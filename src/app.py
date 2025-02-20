import logging
import os
from datetime import timedelta

from flask import Flask, jsonify, request, send_from_directory, session
from flask_limiter.errors import RateLimitExceeded
from flask_login import current_user
from flask_migrate import Migrate
from flask_talisman import Talisman

from commands import register_commands
from config import get_settings
from extensions import db, limiter, login_manager
from middleware import ensure_user_id, log_visit
from routes.answers import answers_bp
from routes.auth import auth_bp
from routes.pages import pages_bp
from routes.password_reset import mail, password_reset_bp
from routes.preferences import preferences_bp
from routes.questions import questions_bp
from routes.transcribe import transcribe_bp

SETTINGS = get_settings()

logging.basicConfig(
    level=SETTINGS.LOG_LEVEL, format="%(asctime)s - %(levelname)s - %(message)s"
)


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
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=2)
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max file size
    # For sqlite
    # app.config["SQLALCHEMY_DATABASE_URI"] = (
    #     f"sqlite:///{os.path.join(instance_path, 'argumentor.db')}"
    # )

    # Initialize extensions
    db.init_app(app)
    Migrate(app, db)
    login_manager.init_app(app)
    limiter.init_app(app)
    mail.init_app(app)

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
        ],
        "connect-src": [
            "'self'",
            "https://accounts.google.com",
            "https://fedcm.googleapis.com",
            "https://identity.google.com",
        ],
    }
    Talisman(app, content_security_policy=csp)

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

    return app


app = create_app()


if __name__ == "__main__":
    debug = True if SETTINGS.DEV else False
    app.run(debug=debug, host="localhost", port=8000)
