import json
import logging
import secrets
import sys
import traceback
from datetime import UTC, datetime, timedelta
from pathlib import Path

from flask import Blueprint, current_app, jsonify, render_template, request, session
from flask_login import login_user
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash

from config import get_settings
from models import User, db

password_reset_bp = Blueprint("password_reset", __name__)
SETTINGS = get_settings()
mail = Mail()

# Configure logging to output to stdout
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)

logger = logging.getLogger(__name__)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)


def generate_reset_token():
    return secrets.token_urlsafe(32)


@password_reset_bp.route("/request-reset", methods=["POST"])
def request_reset():
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 400

    email = request.json.get("email")
    if not email:
        return jsonify({"error": "Email is required"}), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        # Return success even if user not found to prevent email enumeration
        return jsonify(
            {
                "message": "If an account exists with this email, you will receive reset instructions."
            }
        ), 200

    # Generate and save reset token
    token = generate_reset_token()
    user.reset_token = token
    user.reset_token_expiry = datetime.now(UTC) + timedelta(hours=1)
    db.session.commit()

    # Get user's preferred language or default to English
    language = user.preferred_language or "en"

    # Load translations
    try:
        translations_path = (
            Path(current_app.root_path) / "static" / "translations" / f"{language}.json"
        )
        with open(translations_path, "r", encoding="utf-8") as f:
            translations = json.load(f)

        email_subject = (
            translations.get("resetPassword", {})
            .get("email", {})
            .get("subject", "Password Reset Request")
        )
        email_message_template = (
            translations.get("resetPassword", {})
            .get("email", {})
            .get(
                "message",
                "To reset your password, visit the following link:\n\n{resetUrl}\n\nThis link will expire in 1 hour.\n\nIf you did not request this reset, please ignore this email.",
            )
        )
    except Exception as e:
        logger.error(f"Error loading translations: {e}")
        email_subject = "Password Reset Request"
        email_message_template = "To reset your password, visit the following link:\n\n{resetUrl}\n\nThis link will expire in 1 hour.\n\nIf you did not request this reset, please ignore this email."

    # Send reset email
    reset_url = f"{request.host_url}reset-password?token={token}"
    msg = Message(
        email_subject,
        sender=SETTINGS.MAIL_DEFAULT_SENDER,
        recipients=[email],
    )
    msg.body = email_message_template.format(resetUrl=reset_url)
    mail.send(msg)

    return jsonify(
        {
            "message": "If an account exists with this email, you will receive reset instructions."
        }
    ), 200


@password_reset_bp.route("/reset-password", methods=["POST"])
def reset_password():
    try:
        print("Password reset request received", file=sys.stderr)
        logger.debug(
            "Password reset request received with data: %s", request.get_json()
        )

        if not request.is_json:
            return jsonify({"error": "Content-Type must be application/json"}), 400

        data = request.get_json()
        token = data.get("token")
        new_password = data.get("password")

        print(
            f"Reset attempt with token: {token[:10] if token else 'None'}",
            file=sys.stderr,
        )

        if not token or not new_password:
            return jsonify({"error": "Token and new password are required"}), 400

        try:
            with db.session.begin_nested():
                user = User.query.filter_by(reset_token=token).first()

                if not user:
                    print(
                        f"Invalid reset token attempted: {token[:10] if token else 'None'}",
                        file=sys.stderr,
                    )
                    return jsonify({"error": "Invalid reset token"}), 400

                print(f"Found user with ID: {user.uuid}", file=sys.stderr)

                if not user.reset_token_expiry:
                    print(
                        f"Reset token has no expiry for user: {user.uuid}",
                        file=sys.stderr,
                    )
                    return jsonify({"error": "Reset token has expired"}), 400

                current_time = datetime.now(UTC)
                token_expiry = (
                    user.reset_token_expiry.replace(tzinfo=UTC)
                    if user.reset_token_expiry.tzinfo is None
                    else user.reset_token_expiry
                )

                print(
                    f"Token expiry: {token_expiry}, Current time: {current_time}",
                    file=sys.stderr,
                )

                if token_expiry < current_time:
                    return jsonify({"error": "Reset token has expired"}), 400

                # Update password and clear reset token
                user.password_hash = generate_password_hash(new_password)
                user.reset_token = None
                user.reset_token_expiry = None

            try:
                db.session.commit()

                # Log in the user
                login_user(user)
                session["user_id"] = user.uuid
                session.modified = True

                print(
                    f"Password successfully reset and user logged in: {user.uuid}",
                    file=sys.stderr,
                )
                return jsonify(
                    {
                        "message": "Password successfully reset",
                        "user": {
                            "uuid": user.uuid,
                            "username": user.username,
                            "email": user.email,
                            "preferred_language": user.preferred_language,
                        },
                    }
                ), 200
            except Exception as db_error:
                db.session.rollback()
                print(f"Database error during commit: {str(db_error)}", file=sys.stderr)
                print(f"Traceback: {traceback.format_exc()}", file=sys.stderr)
                return jsonify({"error": "Failed to update password"}), 500

        except Exception as db_error:
            db.session.rollback()
            print(
                f"Database error during transaction: {str(db_error)}", file=sys.stderr
            )
            print(f"Traceback: {traceback.format_exc()}", file=sys.stderr)
            return jsonify({"error": "Database error occurred"}), 500

    except Exception as e:
        print(f"Unexpected error during password reset: {str(e)}", file=sys.stderr)
        print(f"Full traceback: {traceback.format_exc()}", file=sys.stderr)
        return jsonify({"error": "An error occurred while resetting password"}), 500
    finally:
        db.session.remove()


@password_reset_bp.route("/reset-password", methods=["GET"])
def reset_password_page():
    token = request.args.get("token")
    if not token:
        # Get language from request or default to English
        language = request.args.get("lang") or "en"

        # Load translations
        try:
            translations_path = (
                Path(current_app.root_path)
                / "static"
                / "translations"
                / f"{language}.json"
            )
            with open(translations_path, "r", encoding="utf-8") as f:
                translations = json.load(f)

            error_message = (
                translations.get("resetPassword", {})
                .get("errors", {})
                .get("invalidToken", "Invalid reset link")
            )
        except Exception as e:
            logger.error(f"Error loading translations: {e}")
            error_message = "Invalid reset link"

        return error_message, 400

    user = User.query.filter_by(reset_token=token).first()
    if (
        not user
        or not user.reset_token_expiry
        or user.reset_token_expiry.replace(tzinfo=UTC) < datetime.now(UTC)
    ):
        # Get language from user or default to English
        language = user.preferred_language if user else "en"

        # Load translations
        try:
            translations_path = (
                Path(current_app.root_path)
                / "static"
                / "translations"
                / f"{language}.json"
            )
            with open(translations_path, "r", encoding="utf-8") as f:
                translations = json.load(f)

            error_message = (
                translations.get("resetPassword", {})
                .get("errors", {})
                .get("invalidToken", "Invalid or expired reset token")
            )
        except Exception as e:
            logger.error(f"Error loading translations: {e}")
            error_message = "Invalid or expired reset token"

        return error_message, 400

    # Pass the user's preferred language to the template
    preferred_language = user.preferred_language if user else "en"
    return render_template(
        "reset_password.html", token=token, preferred_language=preferred_language
    )
