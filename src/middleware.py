import logging
import uuid
from datetime import UTC, datetime

from flask import request, session
from flask_login import current_user

from extensions import db
from models import User, Visit

logger = logging.getLogger(__name__)


def ensure_user_id():
    # If the user is already authenticated through Flask-Login, make sure session user_id matches
    if current_user.is_authenticated:
        if "user_id" not in session or session["user_id"] != current_user.uuid:
            session["user_id"] = current_user.uuid
            session.modified = True
            logger.debug(
                f"Updated session user_id to match authenticated user: {current_user.uuid}"
            )
        return

    # For non-authenticated users, create an anonymous user if needed
    if "user_id" not in session:
        new_id = str(uuid.uuid4())
        session["user_id"] = new_id
        # Generate a default username using a prefix and a short version of the UUID.
        default_username = f"anonymous_{new_id[:8]}"
        new_user = User(uuid=new_id, username=default_username)
        db.session.add(new_user)
        db.session.commit()
        # Make the session permanent to ensure it persists
        session.permanent = True
        logger.debug(
            f"Anonymous user created with id: {new_id} and username: {default_username}"
        )
    else:
        logger.debug(f"Existing user found with id: {session.get('user_id')}")


def log_visit():
    if request.endpoint and request.endpoint != "static":
        today_str = datetime.now(UTC).strftime("%Y-%m-%d")
        if session.get("last_visit_date") != today_str:
            session["last_visit_date"] = today_str
            new_visit = Visit(
                ip_address=request.remote_addr,
                user_agent=request.headers.get("User-Agent"),
                user_uuid=session.get("user_id") if session.get("user_id") else None,
            )
            db.session.add(new_visit)
            db.session.commit()
            logger.info(
                f"Logged visit for user: {session.get('user_id')} on {today_str}"
            )
