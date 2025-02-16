import secrets
from datetime import UTC, datetime, timedelta

from flask import Blueprint, jsonify, render_template, request
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash

from config import get_settings
from models import User, db

password_reset_bp = Blueprint("password_reset", __name__)
SETTINGS = get_settings()
mail = Mail()


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

    # Send reset email
    reset_url = f"{request.host_url}reset-password?token={token}"
    msg = Message(
        "Password Reset Request",
        sender=SETTINGS.MAIL_DEFAULT_SENDER,
        recipients=[email],
    )
    msg.body = f"""To reset your password, visit the following link:

{reset_url}

This link will expire in 1 hour.

If you did not request this reset, please ignore this email.
"""
    mail.send(msg)

    return jsonify(
        {
            "message": "If an account exists with this email, you will receive reset instructions."
        }
    ), 200


@password_reset_bp.route("/reset-password", methods=["POST"])
def reset_password():
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 400

    token = request.json.get("token")
    new_password = request.json.get("password")

    if not token or not new_password:
        return jsonify({"error": "Token and new password are required"}), 400

    user = User.query.filter_by(reset_token=token).first()
    if (
        not user
        or not user.reset_token_expiry
        or user.reset_token_expiry.replace(tzinfo=UTC) < datetime.now(UTC)
    ):
        return jsonify({"error": "Invalid or expired reset token"}), 400

    # Update password and clear reset token
    user.password_hash = generate_password_hash(new_password)
    user.reset_token = None
    user.reset_token_expiry = None
    db.session.commit()

    return jsonify({"message": "Password successfully reset"}), 200


@password_reset_bp.route("/reset-password", methods=["GET"])
def reset_password_page():
    token = request.args.get("token")
    if not token:
        return "Invalid reset link", 400

    user = User.query.filter_by(reset_token=token).first()
    if (
        not user
        or not user.reset_token_expiry
        or user.reset_token_expiry.replace(tzinfo=UTC) < datetime.now(UTC)
    ):
        return "Invalid or expired reset token", 400

    return render_template("reset_password.html", token=token)
