import logging
import uuid

from flask import Blueprint, jsonify, request, session
from flask_login import login_required, login_user, logout_user
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from sqlalchemy import update
from werkzeug.security import check_password_hash, generate_password_hash

from config import get_settings
from extensions import login_manager
from models import Answer, User, db
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
        username = data.get("username")
        password = data.get("password")

        # Check for existing anonymous user
        anonymous_user = None
        if "user_id" in session:
            anonymous_user = User.query.filter_by(uuid=session["user_id"]).first()

        if User.query.filter_by(username=username).first():
            logger.warning(f"Signup attempt with existing username: {username}")
            return jsonify({"error": "Username already exists"}), 400

        # Create and flush new user first to generate UUID
        user = User(
            uuid=str(uuid.uuid4()),
            username=username,
            password_hash=generate_password_hash(password),
            xp=anonymous_user.xp if anonymous_user else session.get("xp", 0),
        )
        db.session.add(user)
        db.session.flush()

        if anonymous_user:
            # Merge all answers from the anonymous user into the google account.
            db.session.execute(
                update(Answer)
                .where(Answer.user_uuid == anonymous_user.uuid)
                .values(user_uuid=user.uuid)
            )
            db.session.delete(anonymous_user)

        db.session.commit()
        login_user(user)

        # Ensure session is updated before responding
        session["user_id"] = user.uuid
        session.modified = True

        # Calculate level info
        level_info = get_level_info(user.xp)
        logger.info(f"New user signed up: {username}, id: {user.uuid}")

        return jsonify(
            {
                "message": "Account created successfully",
                "user": {
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
    username = data.get("username")
    user = User.query.filter_by(username=username).first()

    if user and check_password_hash(user.password_hash, data.get("password")):
        if "user_id" in session:
            anonymous_user = User.query.filter_by(uuid=session["user_id"]).first()
            if anonymous_user:
                db.session.execute(
                    update(Answer)
                    .where(Answer.user_uuid == anonymous_user.uuid)
                    .values(user_uuid=user.uuid)
                )
                user.xp += anonymous_user.xp
                db.session.delete(anonymous_user)
                db.session.commit()

        login_user(user)
        session["user_id"] = user.uuid
        session.modified = True  # Ensure session is marked as modified

        # Calculate the level info here
        level_info = get_level_info(user.xp)
        logger.info(f"User logged in: {username}, id: {user.uuid}")

        return jsonify(
            {
                "message": "Logged in successfully",
                "user": {
                    "username": user.username,
                    "uuid": user.uuid,
                    "xp": user.xp,
                    "level_info": level_info,  # Include the additional level information
                },
            }
        )
    logger.warning(f"Failed login attempt for username: {username}")
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
    try:
        id_info = id_token.verify_oauth2_token(
            token, google_requests.Request(), SETTINGS.GOOGLE_CLIENT_ID
        )

        # Look for an existing google user based on the Google ID.
        user = User.query.filter_by(google_id=id_info["sub"]).first()

        # Check if there's a user in the session (anonymous user)
        anonymous_user = None
        if "user_id" in session:
            session_user = User.query.filter_by(uuid=session["user_id"]).first()
            # If the session user exists and is different from the found google user,
            # treat that as the anonymous account to merge.
            if session_user and (not user or session_user.uuid != user.uuid):
                anonymous_user = session_user

        if not user:
            google_email = id_info["email"]
            user = User(
                uuid=str(uuid.uuid4()),
                google_id=id_info["sub"],
                username=google_email,
                email=google_email,
                profile_pic=id_info.get("picture"),
                xp=anonymous_user.xp if anonymous_user else 0,
            )
            db.session.add(user)
        else:
            # For an existing google user, merge XP from the anonymous account if present.
            if anonymous_user:
                user.xp += anonymous_user.xp

        if anonymous_user:
            # Merge all answers from the anonymous user into the google account.
            db.session.execute(
                update(Answer)
                .where(Answer.user_uuid == anonymous_user.uuid)
                .values(user_uuid=user.uuid)
            )
            db.session.delete(anonymous_user)

        # Always update profile picture if a new one is provided.
        new_pic = id_info.get("picture")
        if new_pic and user.profile_pic != new_pic:
            user.profile_pic = new_pic

        db.session.commit()
        login_user(user)
        # Ensure the session is updated to use the google account's UUID.
        session["user_id"] = user.uuid
        return jsonify({"message": "Google login successful"})
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
        return jsonify({"error": str(e)}), 500
