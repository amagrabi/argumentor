import gc
import logging
import resource
import sys
import uuid
from datetime import UTC, datetime
from functools import lru_cache

from flask import Response, after_this_request, request, session
from flask_login import current_user

from config import get_settings
from extensions import db
from models import User, Visit

logger = logging.getLogger(__name__)
SETTINGS = get_settings()

# WordPress scanning patterns
WP_PATTERNS = [
    "wp-",
    "wordpress",
    "xmlrpc.php",
    "wlwmanifest.xml",
    "/blog/",
    "/web/",
    "/site/",
    "/cms/",
    "/wp1/",
    "/wp2/",
    "/test/",
    "/media/",
    "/shop/",
    "/news/",
    "/2018/",
    "/2019/",
    "/sito/",
    # Additional common WordPress scanning patterns
    "wp-content",
    "wp-includes",
    "wp-admin",
    "wp-login",
    "wp-config",
    "wp-cron",
    "wp-json",
    "wp-load",
    "wp-mail",
    "wp-signup",
    ".php",  # Most WordPress exploits target PHP files
]


# Cache for blocked IPs to avoid repeated database lookups
@lru_cache(maxsize=1000)
def is_ip_blocked(ip: str) -> bool:
    """Check if an IP is currently blocked based on recent scanning attempts."""
    return False  # Will be updated by the rate limiter


def block_wp_scanners():
    """
    Enhanced middleware to detect and block WordPress scanning attempts.
    This runs before other middleware to reduce server load.
    """
    path = request.path.lower()
    ip = request.remote_addr

    # Quick return for static files and allowed paths
    if path.startswith(("/static/", "/health", "/favicon.ico")):
        return None

    # Check if the request matches known WordPress scanning patterns
    if any(pattern in path for pattern in WP_PATTERNS):
        # Check if IP is already blocked
        if is_ip_blocked(ip):
            return Response("", status=403)

        try:
            # Create a rate limit key specific to WordPress scanning
            key = f"wp_scan:{ip}"

            # Use stricter rate limiting for scanning attempts
            # Allow only 5 requests per minute, then block for an hour
            from extensions import limiter as limiter_instance

            if not limiter_instance.limiter.hit(key, 5, 60):
                # If rate limit exceeded, mark IP as blocked
                is_ip_blocked.cache_clear()  # Clear cache to update blocked status

                # Log the blocking event
                logger.warning(
                    f"Blocked WordPress scanning attempt from IP: {ip}, path: {path}"
                )

                # Return 403 Forbidden instead of 404
                # This tells the scanner the site is actively blocking them
                return Response("", status=403)

        except Exception as e:
            logger.error(f"Error in WordPress scanning protection: {e}")
            # Continue with normal request processing if rate limiting fails
            pass

        # Return a minimal 404 response without further processing
        return Response("", status=404)

    # Continue normal request processing if not a WordPress scanning attempt
    return None


def ensure_user_id():
    # Skip user identification for static files to improve performance
    if request.path.startswith("/static/"):
        return

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
    # Skip logging for static files to improve performance
    if request.path.startswith("/static/"):
        return

    if request.endpoint and request.endpoint != "static":
        today_str = datetime.now(UTC).strftime("%Y-%m-%d")
        if session.get("last_visit_date") != today_str:
            session["last_visit_date"] = today_str
            user_agent = request.headers.get("User-Agent", "")
            # Truncate user_agent if it's too long to prevent database errors
            if user_agent and len(user_agent) > 500:
                user_agent = user_agent[:500]

            new_visit = Visit(
                ip_address=request.remote_addr,
                user_agent=user_agent,
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

        # Convert MB thresholds to KB for comparison with memory_usage_kb
        warn_threshold_kb = SETTINGS.MEMORY_WARN_THRESHOLD * 1024
        restart_threshold_kb = SETTINGS.MEMORY_RESTART_THRESHOLD * 1024

        # Log if memory usage is high and trigger garbage collection
        if mem_before > warn_threshold_kb:
            logger.warning(
                f"High memory usage detected: {mem_before:.2f}KB - triggering garbage collection"
            )
            # Force garbage collection to free up memory
            gc.collect()

            # Check if memory is still critical after garbage collection
            mem_after_gc = memory_usage_kb()

            # If memory usage is too high even after GC, gracefully restart worker
            if mem_after_gc > restart_threshold_kb:
                import os
                import signal
                from threading import Timer

                def delayed_exit():
                    logger.warning(
                        f"Worker exceeded memory threshold ({mem_after_gc / 1024:.2f}MB), shutting down gracefully"
                    )
                    # Send SIGTERM to self - Gunicorn will handle worker replacement
                    os.kill(os.getpid(), signal.SIGTERM)

                # Schedule exit after response is sent
                Timer(1.0, delayed_exit).start()
                logger.warning(
                    f"Scheduled worker shutdown due to high memory usage: {mem_after_gc / 1024:.2f}MB"
                )

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
