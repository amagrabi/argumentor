import gc
import logging
import os
import platform
import resource
import signal
import threading
import time
import traceback
from datetime import timedelta

from flask import Flask, jsonify, request, send_from_directory, session
from flask_limiter.errors import RateLimitExceeded
from flask_login import current_user
from flask_migrate import Migrate
from flask_talisman import Talisman
from werkzeug.exceptions import NotFound

from commands import register_commands
from config import get_settings
from extensions import db, limiter, login_manager
from middleware import (
    block_wp_scanners,
    ensure_user_id,
    log_visit,
    monitor_memory_usage,
)
from routes.answers import answers_bp
from routes.auth import auth_bp
from routes.pages import pages_bp
from routes.password_reset import mail, password_reset_bp
from routes.preferences import preferences_bp
from routes.questions import questions_bp
from routes.transcribe import transcribe_bp

SETTINGS = get_settings()

# Configure logging using the settings value directly
log_level = getattr(logging, SETTINGS.LOG_LEVEL.upper(), logging.DEBUG)
logging.basicConfig(
    level=log_level,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    force=True,  # Ensure our configuration takes precedence
)

# Get the root logger and set its level
root_logger = logging.getLogger()
root_logger.setLevel(log_level)

# Create a logger for this module
logger = logging.getLogger(__name__)
logger.debug("Logging configured with level: %s", SETTINGS.LOG_LEVEL)


def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


def create_app():
    instance_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "instance"
    )
    os.makedirs(instance_path, exist_ok=True)

    app = Flask(__name__, instance_path=instance_path, static_folder="static")
    app.config.from_mapping(get_settings())
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=30)
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max file size

    app.url_map.strict_slashes = False

    # Add SQLAlchemy engine options tuned for production
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_size": 5,  # Reduced from 10 to save memory
        "max_overflow": 10,  # Reduced from 20 to save memory
        "pool_timeout": 30,  # Increased wait time (in seconds) for a free connection
        "pool_recycle": 180,  # Recycle connections older than 3 minutes (helps avoid stale connections)
        "pool_pre_ping": True,  # Check connection health before using it
    }

    # Ensure the connection is cleaned up properly when returned to the pool
    app.config["SQLALCHEMY_POOL_RESET_ON_RETURN"] = "rollback"

    # Initialize extensions
    db.init_app(app)
    Migrate(app, db)
    login_manager.init_app(app)
    limiter.init_app(app)
    mail.init_app(app)

    # Start memory monitor thread in production
    if not SETTINGS.DEV:

        def memory_monitor_thread():
            """Background thread that monitors memory usage and restarts worker if needed"""
            logger.info("Starting memory monitor thread")
            while True:
                try:
                    # Check every 60 seconds
                    time.sleep(60)

                    # Force garbage collection
                    gc.collect()

                    # Get memory usage
                    memory_divisor = (
                        1024 if platform.system() != "Darwin" else 1024 * 1024
                    )
                    mem_usage = (
                        resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
                        / memory_divisor
                    )

                    # Log memory usage periodically
                    logger.info(f"Current memory usage: {mem_usage:.2f}MB")

                    # If memory exceeds threshold, trigger restart
                    if mem_usage > SETTINGS.MEMORY_RESTART_THRESHOLD:
                        logger.warning(
                            f"Memory monitor detected high usage: {mem_usage:.2f}MB, restarting worker"
                        )
                        # Give a moment for any in-progress requests
                        time.sleep(2)
                        # Send SIGTERM to self - Gunicorn will handle worker replacement
                        os.kill(os.getpid(), signal.SIGTERM)
                        break
                except Exception as e:
                    logger.error(f"Error in memory monitor thread: {e}")
                    # Continue running even if there's an error

        # Start the thread
        monitor_thread = threading.Thread(target=memory_monitor_thread, daemon=True)
        monitor_thread.start()

    # Register WordPress scanner blocking middleware
    app.before_request(block_wp_scanners)

    # Register a custom error handler for rate limit errors
    @app.errorhandler(RateLimitExceeded)
    def ratelimit_handler(e):
        # e.description comes from the error_message parameter in the rate limit decorator
        return jsonify(error=e.description), e.code

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(pages_bp)
    app.register_blueprint(answers_bp)
    app.register_blueprint(questions_bp)
    app.register_blueprint(preferences_bp)
    app.register_blueprint(password_reset_bp)
    app.register_blueprint(transcribe_bp)

    # Register CLI commands
    register_commands(app)

    # Add request handlers
    app.before_request(ensure_user_id)
    app.before_request(log_visit)

    # Register memory monitoring middleware (always active)
    app.before_request(monitor_memory_usage())
    app.after_request(add_cors_headers)

    @app.context_processor
    def inject_client_id():
        return dict(GOOGLE_CLIENT_ID=app.config.get("GOOGLE_CLIENT_ID"))

    # Ensure the URL scheme is set to HTTPS for URL generation
    app.config["PREFERRED_URL_SCHEME"] = "https"

    # Define custom content security policy (CSP)
    csp = {
        "default-src": ["'self'"],
        "script-src": [
            "'self'",
            "https://cdn.tailwindcss.com",
            "https://cdn.jsdelivr.net",
            "https://accounts.google.com",
            "https://www.googletagmanager.com",
            "'unsafe-inline'",
            "https://fedcm.googleapis.com",
            "https://unpkg.com",
            "https://js.stripe.com",
        ],
        "style-src": [
            "'self'",
            "https://cdn.tailwindcss.com",
            "https://accounts.google.com",
            "'unsafe-inline'",
        ],
        "img-src": ["'self'", "data:", "https://img.icons8.com"],
        "frame-src": [
            "https://accounts.google.com",
            "https://fedcm.googleapis.com",
            "https://identity.google.com",
            "https://js.stripe.com",
            "https://hooks.stripe.com",
        ],
        "connect-src": [
            "'self'",
            "https://accounts.google.com",
            "https://fedcm.googleapis.com",
            "https://identity.google.com",
            "https://api.stripe.com",
        ],
    }

    # Initialize Talisman with custom configurations
    Talisman(
        app,
        content_security_policy=csp,
        permissions_policy={},  # Empty dict to avoid setting any permissions policy
        force_https=False,  # Since we're running locally
    )

    @app.route("/static/translations/<path:filename>")
    def serve_translations(filename):
        return send_from_directory("static/translations", filename)

    @app.before_request
    def handle_language_parameter():
        lang = request.args.get("lang")
        if lang:
            # If language is not supported, use default
            lang = (
                lang
                if lang in SETTINGS.SUPPORTED_LANGUAGES
                else SETTINGS.DEFAULT_LANGUAGE
            )
            session["language"] = lang
            if current_user.is_authenticated:
                current_user.preferred_language = lang
                db.session.commit()

    @app.route("/robots.txt")
    def serve_robots_txt():
        return send_from_directory(app.static_folder, "robots.txt")

    @app.route("/sitemap.xml")
    def serve_sitemap():
        return send_from_directory(app.static_folder, "sitemap.xml")

    @app.route("/security.txt")
    def serve_security_txt():
        return send_from_directory(app.static_folder, "security.txt")

    @app.route("/.well-known/security.txt")
    def serve_wellknown_security_txt():
        return send_from_directory(
            os.path.join(app.static_folder, ".well-known"), "security.txt"
        )

    @app.route("/health")
    def health_check():
        # Force garbage collection before reporting memory
        gc.collect()

        # Get memory usage
        memory_divisor = 1024 if platform.system() != "Darwin" else 1024 * 1024
        mem_usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / memory_divisor

        # Return health status with memory info
        return jsonify(
            {
                "status": "ok",
                "memory_mb": round(mem_usage, 2),
                "memory_pct": round(
                    (mem_usage / 512) * 100, 2
                ),  # Percentage of 512MB limit
                "warn_threshold_mb": SETTINGS.MEMORY_WARN_THRESHOLD,
                "restart_threshold_mb": SETTINGS.MEMORY_RESTART_THRESHOLD,
            }
        )

    @app.errorhandler(Exception)
    def handle_exception(e):
        # Skip detailed logging for common routing exceptions that should be handled by specific handlers
        if isinstance(e, NotFound):
            return handle_not_found(e)

        # Log the error
        logger.error(f"Unhandled exception: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")

        # Clean up the database session
        db.session.remove()

        # Return a JSON response for API endpoints
        if request.path.startswith("/reset_password"):
            return jsonify(error=str(e)), 500

        return jsonify(error="An unexpected error occurred"), 500

    @app.errorhandler(404)
    def handle_not_found(e):
        # The WordPress scanning detection is now handled by the middleware
        # This handler will only be called for legitimate 404s

        # Log at a lower level
        logger.info(f"404 Not Found: {request.path}")

        # Return a JSON response for API endpoints
        return jsonify(error="The requested URL was not found"), 404

    @app.teardown_appcontext
    def shutdown_session(exception=None):
        if exception:
            logger.error(f"Exception during request: {str(exception)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
        db.session.remove()

    return app


app = create_app()


if __name__ == "__main__":
    debug = True if SETTINGS.DEV else False
    app.run(debug=debug, host="localhost", port=8000)
