from flask import Flask
from google.oauth2 import service_account

from commands import register_commands
from config import get_settings
from extensions import db
from middleware import ensure_user_id, log_visit
from routes.answers import answers_bp
from routes.pages import pages_bp
from routes.questions import questions_bp

SETTINGS = get_settings()
CREDENTIALS = service_account.Credentials.from_service_account_file(
    SETTINGS.GOOGLE_APPLICATION_CREDENTIALS,
    scopes=["https://www.googleapis.com/auth/cloud-platform"],
)


def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


def create_app():
    app = Flask(__name__)
    app.config.from_mapping(get_settings())

    # Initialize extensions
    db.init_app(app)

    # Create tables if they don't exist
    with app.app_context():
        db.create_all()

    # Register blueprints
    app.register_blueprint(pages_bp)
    app.register_blueprint(answers_bp)
    app.register_blueprint(questions_bp)

    # Register CLI commands
    register_commands(app)

    # Add request handlers
    app.before_request(ensure_user_id)
    app.before_request(log_visit)
    app.after_request(add_cors_headers)

    return app


app = create_app()


if __name__ == "__main__":
    debug = True if SETTINGS.DEV else False
    app.run(debug=debug)
