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

auth_bp = Blueprint("auth", __name__)
SETTINGS = get_settings()


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
            return jsonify({"error": "Username already exists"}), 400

        # Create and flush new user first to generate UUID
        user = User(
            uuid=str(uuid.uuid4()),
            username=username,
            password_hash=generate_password_hash(password),
            xp=anonymous_user.xp if anonymous_user else session.get("xp", 0),
        )
        db.session.add(user)
        db.session.flush()  # Generate UUID without committing transaction

        if anonymous_user:
            # Directly update answers' user_uuid
            db.session.execute(
                update(Answer)
                .where(Answer.user_uuid == anonymous_user.uuid)
                .values(user_uuid=user.uuid)
            )
            db.session.delete(anonymous_user)

        db.session.commit()
        login_user(user)
        return jsonify({"message": "Account created successfully"})
    except Exception as e:
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
                # Bulk update answers
                db.session.execute(
                    update(Answer)
                    .where(Answer.user_uuid == anonymous_user.uuid)
                    .values(user_uuid=user.uuid)
                )
                # Merge XP and delete
                user.xp += anonymous_user.xp
                db.session.delete(anonymous_user)
                db.session.commit()

        login_user(user)
        return jsonify({"message": "Logged in successfully"})
    return jsonify({"error": "Invalid credentials"}), 401


@auth_bp.route("/logout", methods=["POST"], endpoint="logout_route")
@login_required
def logout():
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
