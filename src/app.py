import os

from flask import Flask
from google.oauth2 import service_account

from commands import register_commands
from config import get_settings
from extensions import db, login_manager
from middleware import ensure_user_id, log_visit
from routes.answers import answers_bp
from routes.auth import auth_bp
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
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


def create_app():
    instance_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "instance"
    )
    os.makedirs(instance_path, exist_ok=True)

    app = Flask(__name__, instance_path=instance_path)
    app.config.from_mapping(get_settings())
    app.config["SQLALCHEMY_DATABASE_URI"] = (
        f"sqlite:///{os.path.join(instance_path, 'argumentor.db')}"
    )

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)

    # Create tables if they don't exist
    with app.app_context():
        db.create_all()

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(pages_bp)
    app.register_blueprint(answers_bp)
    app.register_blueprint(questions_bp)

    # Register CLI commands
    register_commands(app)

    # Add request handlers
    app.before_request(ensure_user_id)
    app.before_request(log_visit)
    app.after_request(add_cors_headers)

    @app.context_processor
    def inject_client_id():
        return dict(GOOGLE_CLIENT_ID=app.config.get("GOOGLE_CLIENT_ID"))

    return app


app = create_app()


if __name__ == "__main__":
    debug = True if SETTINGS.DEV else False
    app.run(debug=debug, host="localhost", port=8000)
