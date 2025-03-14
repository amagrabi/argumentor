import gc
import logging
import resource
import sys
import uuid
from datetime import UTC, datetime

from flask import after_this_request, request, session
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


def monitor_memory_usage():
    """
    Middleware to monitor memory usage and log when it exceeds thresholds.
    This helps identify memory leaks or high memory usage patterns.
    """

    def memory_usage_kb():
        """Return memory usage in kilobytes"""
        try:
            # For Unix systems
            rusage_denom = 1024.0
            if sys.platform == "darwin":
                # ... macOS ...
                rusage_denom = rusage_denom
            else:
                # ... Linux ...
                rusage_denom = rusage_denom

            # Get memory usage from resource module
            usage = resource.getrusage(resource.RUSAGE_SELF)
            return usage.ru_maxrss / rusage_denom
        except Exception as e:
            logger.error(f"Error getting memory usage: {e}")
            return 0

    def middleware():
        # Check memory before request
        mem_before = memory_usage_kb()

        # Log if memory usage is high and trigger garbage collection
        if mem_before > 400 * 1024:  # 400MB (Heroku free tier has 512MB limit)
            logger.warning(
                f"High memory usage detected: {mem_before:.2f}KB - triggering garbage collection"
            )
            # Force garbage collection to free up memory
            gc.collect()

        @after_this_request
        def after_request(response):
            # Check memory after request
            mem_after = memory_usage_kb()
            mem_diff = mem_after - mem_before

            # Log significant memory increases
            if mem_diff > 50 * 1024:  # 50MB increase in a single request
                logger.warning(
                    f"Large memory increase: {mem_diff:.2f}KB in request {request.path}"
                )
                # Force garbage collection after large memory increases
                gc.collect()

            return response

        return None

    return middleware
