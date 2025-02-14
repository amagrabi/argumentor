import uuid
from datetime import UTC, datetime

from flask import request, session

from extensions import db
from models import User, Visit


def ensure_user_id():
    if "user_id" not in session:
        new_id = str(uuid.uuid4())
        session["user_id"] = new_id
        # Optionally, create an empty user record for anonymous visitors.
        new_user = User(uuid=new_id)
        db.session.add(new_user)
        db.session.commit()


def log_visit():
    if request.endpoint and request.endpoint != "static":
        today_str = datetime.now(UTC).strftime("%Y-%m-%d")
        if session.get("last_visit_date") != today_str:
            session["last_visit_date"] = today_str
            new_visit = Visit(
                ip_address=request.remote_addr,
                user_agent=request.headers.get("User-Agent"),
                user_uuid=session.get("user_id"),
            )
            db.session.add(new_visit)
            db.session.commit()
