import gc
import logging
import resource
import sys
from datetime import UTC, datetime

from flask import Response, after_this_request, request, session
from flask_login import current_user

from config import get_settings
from extensions import db
from models import Visit
from services.user_service import session_is_new, session_user_uuid

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
]


def block_wp_scanners():
    """
    Middleware to detect and block WordPress scanning attempts.
    This runs before other middleware to reduce server load.
    """
    path = request.path.lower()

    # Check if the request matches known WordPress scanning patterns
    if any(pattern in path for pattern in WP_PATTERNS):
        # Apply stricter rate limiting for WordPress scanning IPs
        # This helps prevent abuse by the same IP address
        try:
            # Get the client's IP address
            ip = request.remote_addr

            # Create a rate limit key specific to WordPress scanning
            key = f"wp_scan:{ip}"

            # Check if this IP has exceeded the rate limit (10 requests per minute)
            # Access the limiter instance through the Flask extension
            from extensions import limiter as limiter_instance

            if not limiter_instance.limiter.hit(key, 10, 60):
                # If rate limit exceeded, return 429 Too Many Requests
                return Response("Rate limit exceeded", status=429)
        except (AttributeError, ImportError):
            # If limiter is not available or configured correctly, just continue
            pass

        # Return a minimal 404 response without further processing
        return Response("", status=404)

    # Continue normal request processing if not a WordPress scanning attempt
    return None


def ensure_user_id():
    # Skip user identification for static files to improve performance
    if request.path.startswith("/static/"):
        return

    # Identity only, no database write. This used to INSERT a users row for every
    # visitor arriving without a session cookie, which meant one row per request
    # for every bot, crawler and vulnerability scanner. The row is now created
    # lazily by persist_session_user() at the first action that needs one.
    session_user_uuid()


def log_visit():
    # Skip logging for static files to improve performance
    if request.path.startswith("/static/"):
        return

    # A client that returned no session cookie is almost certainly not a browser:
    # a real one sends the cookie back on its next request, which is within the
    # same page view. Logging the cookie-less ones is what filled this table.
    if session_is_new():
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
                # user_uuid is a foreign key, and an anonymous visitor usually
                # has no users row to point at, so only authenticated visits are
                # linked. Nothing joins visit to users today, so the anonymous
                # rows carry exactly the information they always did.
                user_uuid=current_user.uuid if current_user.is_authenticated else None,
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
