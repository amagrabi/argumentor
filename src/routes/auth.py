import logging
import re
import uuid

from flask import Blueprint, jsonify, request, session
from flask_login import login_required, login_user, logout_user
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from sqlalchemy import or_, update
from werkzeug.security import check_password_hash, generate_password_hash

from config import get_settings
from extensions import login_manager
from models import Answer, User, UserAchievement, db
from services.leveling import get_level_info

logger = logging.getLogger(__name__)
SETTINGS = get_settings()

auth_bp = Blueprint("auth", __name__)


@login_manager.user_loader
def load_user(user_uuid):
    return User.query.get(user_uuid)


@auth_bp.route("/signup", methods=["POST"])
def signup():
    try:
        data = request.json
        email = data.get("email")
        password = data.get("password")
        username = data.get("username")

        if not email or not password or not username:
            return jsonify(
                {"error": "Email, password, and username are required."}
            ), 400

        # Validate email format.
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            return jsonify({"error": "Invalid email format."}), 400

        # Check if the username already exists.
        if User.query.filter_by(username=username).first():
            return jsonify({"error": "Username already exists."}), 400

        # Check for an existing account with this email.
        if User.query.filter_by(email=email).first():
            logger.warning(f"Signup attempt with existing email: {email}")
            return jsonify({"error": "Email already exists"}), 400

        # Merge anonymous user data if present.
        anonymous_user = None
        if "user_id" in session:
            anonymous_user = User.query.filter_by(uuid=session["user_id"]).first()

        # Create the new user with the provided username.
        user = User(
            uuid=str(uuid.uuid4()),
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            xp=anonymous_user.xp if anonymous_user else session.get("xp", 0),
            tier="free",
        )
        db.session.add(user)
        db.session.flush()  # This ensures user.uuid is available

        if anonymous_user:
            # Transfer answers
            db.session.execute(
                update(Answer)
                .where(Answer.user_uuid == anonymous_user.uuid)
                .values(user_uuid=user.uuid)
            )

            # Transfer achievements using direct SQL update
            db.session.execute(
                update(UserAchievement)
                .where(UserAchievement.user_uuid == anonymous_user.uuid)
                .values(user_uuid=user.uuid)
            )

            db.session.delete(anonymous_user)

        db.session.commit()
        login_user(user)
        session["user_id"] = user.uuid
        session.modified = True

        level_info = get_level_info(user.xp)
        logger.info(f"New user signed up: {email}, id: {user.uuid}")

        return jsonify(
            {
                "message": "Account created successfully",
                "user": {
                    "email": user.email,
                    "username": user.username,
                    "uuid": user.uuid,
                    "xp": user.xp,
                    "level_info": level_info,
                },
            }
        )
    except Exception as e:
        logger.error(f"Error during signup: {str(e)}")
        return jsonify({"error": str(e)}), 500


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.json
    login_identity = data.get("login")
    password = data.get("password")
    if not login_identity or not password:
        return jsonify({"error": "Both login and password are required."}), 400

    user = User.query.filter(
        or_(User.email == login_identity, User.username == login_identity)
    ).first()

    if user and check_password_hash(user.password_hash, password):
        try:
            # Start a transaction
            if "user_id" in session:
                anonymous_user = User.query.filter_by(uuid=session["user_id"]).first()
                if anonymous_user:
                    # Get all answers from the anonymous user
                    anonymous_answers = Answer.query.filter_by(
                        user_uuid=anonymous_user.uuid
                    ).all()

                    # Get all question IDs for which the authenticated user already has answers
                    existing_question_ids = set(
                        answer.question_id
                        for answer in Answer.query.filter_by(user_uuid=user.uuid).all()
                        if answer.question_id is not None
                    )

                    # Transfer XP from anonymous user
                    user.xp += anonymous_user.xp

                    # Transfer each answer individually, skipping those for questions the user already answered
                    for answer in anonymous_answers:
                        # Skip if the authenticated user already has an answer for this question
                        if (
                            answer.question_id
                            and answer.question_id in existing_question_ids
                        ):
                            logger.info(
                                f"Skipping transfer of answer {answer.id} for question {answer.question_id} as user {user.uuid} already has an answer for it"
                            )
                            continue

                        # Update the user_uuid for this answer
                        answer.user_uuid = user.uuid

                    # Transfer achievements using direct SQL update
                    db.session.execute(
                        update(UserAchievement)
                        .where(UserAchievement.user_uuid == anonymous_user.uuid)
                        .values(user_uuid=user.uuid)
                    )

                    # Mark the anonymous user for deletion
                    db.session.delete(anonymous_user)

                    # Flush to ensure the updates are processed before the commit
                    db.session.flush()

            if user.tier == "anonymous":
                user.tier = "free"

            # Commit the transaction
            db.session.commit()

            # Log in the user after the transaction is committed
            login_user(user)
            session["user_id"] = user.uuid

            # Update session language with the user's saved preference.
            if hasattr(user, "preferred_language") and user.preferred_language in [
                "en",
                "de",
            ]:
                session["language"] = user.preferred_language
            else:
                session["language"] = "en"
            session.modified = True

            level_info = get_level_info(user.xp)
            logger.info(f"User logged in: {login_identity}, id: {user.uuid}")

            return jsonify(
                {
                    "message": "Logged in successfully",
                    "user": {
                        "email": user.email,
                        "username": user.username,
                        "uuid": user.uuid,
                        "xp": user.xp,
                        "level_info": level_info,
                        "preferred_language": user.preferred_language,
                    },
                }
            )
        except Exception as e:
            # Rollback the transaction in case of any error
            db.session.rollback()
            logger.error(f"Error during login for {login_identity}: {str(e)}")
            return jsonify(
                {"error": "A server error occurred during login. Please try again."}
            ), 500

    logger.warning(f"Failed login attempt for login: {login_identity}")
    return jsonify({"error": "Invalid credentials"}), 401


@auth_bp.route("/logout", methods=["POST"], endpoint="logout_route")
@login_required
def logout():
    logger.info(f"User logged out: {session.get('user_id')}")
    logout_user()
    session.clear()
    return jsonify({"message": "Logged out successfully"})


@auth_bp.route("/google-auth", methods=["POST"])
def google_auth():
    token = request.json.get("token")
    username = request.json.get("username")
    try:
        id_info = id_token.verify_oauth2_token(
            token, google_requests.Request(), SETTINGS.GOOGLE_CLIENT_ID
        )

        # Look for an existing google user by Google ID.
        user = User.query.filter_by(google_id=id_info["sub"]).first()

        # Check for an existing anonymous user in session.
        anonymous_user = None
        if "user_id" in session:
            session_user = User.query.filter_by(uuid=session["user_id"]).first()
            if session_user and (not user or session_user.uuid != user.uuid):
                anonymous_user = session_user

        if not user:
            # Reject signup if username is not provided.
            if not username:
                return jsonify(
                    {"error": "Username is required for Google signups."}
                ), 400
            # Ensure the username isn't already in use.
            if User.query.filter_by(username=username).first():
                return jsonify({"error": "Username already exists."}), 400

            google_email = id_info["email"]
            user = User(
                uuid=str(uuid.uuid4()),
                google_id=id_info["sub"],
                username=username,
                email=google_email,
                profile_pic=id_info.get("picture"),
                xp=anonymous_user.xp if anonymous_user else 0,
                tier="free",
            )
            db.session.add(user)
        else:
            # For an existing google user, merge XP from the anonymous account if present.
            if anonymous_user:
                user.xp += anonymous_user.xp

        if anonymous_user:
            db.session.execute(
                update(Answer)
                .where(Answer.user_uuid == anonymous_user.uuid)
                .values(user_uuid=user.uuid)
            )
            db.session.execute(
                update(UserAchievement)
                .where(UserAchievement.user_uuid == anonymous_user.uuid)
                .values(user_uuid=user.uuid)
            )
            db.session.delete(anonymous_user)

        new_pic = id_info.get("picture")
        if new_pic and user.profile_pic != new_pic:
            user.profile_pic = new_pic

        db.session.commit()
        login_user(user)
        session["user_id"] = user.uuid
        return jsonify(
            {
                "message": "Google login successful",
                "user": {"preferred_language": user.preferred_language},
            }
        )
    except ValueError:
        return jsonify({"error": "Invalid Google token"}), 401


@auth_bp.route("/update_session", methods=["POST"])
def update_session():
    data = request.json
    # Use a strict check for None so that an empty dict {} is allowed.
    if data is None:
        return jsonify({"error": "No data provided"}), 400
    try:
        # If no explicit user data was provided, try to retrieve current user's info.
        user_data = data.get("user", None)
        if not user_data:
            if "user_id" in session:
                user = User.query.filter_by(uuid=session["user_id"]).first()
                if user:
                    # Build a user_data dict with the needed info.
                    user_data = {
                        "uuid": user.uuid,
                        "xp": user.xp,
                        "level_info": get_level_info(user.xp),
                    }
                else:
                    return jsonify({"error": "User not found"}), 400
            else:
                return jsonify({"error": "No user in session"}), 400
        else:
            # Update session with the provided data.
            session["user_id"] = user_data.get("uuid")
            session["xp"] = user_data.get("xp", 0)
            if "level_info" not in user_data:
                user_data["level_info"] = get_level_info(user_data.get("xp", 0))
        return jsonify(user_data)
    except Exception as e:
        logger.error(f"Error updating session: {str(e)}")
        return jsonify({"error": "Failed to update session"}), 500
