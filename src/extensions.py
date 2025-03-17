import json
import os

import openai
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from google.oauth2 import service_account

from config import get_settings

SETTINGS = get_settings()

# Initialize Flask extensions
db = SQLAlchemy()
limiter = Limiter(key_func=get_remote_address)
login_manager = LoginManager()
login_manager.login_view = "auth.login"

# Initialize OpenAI client
openai_client = openai.OpenAI(api_key=SETTINGS.OPENAI_API_KEY)


# Initialize Google credentials
def get_google_credentials():
    if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON"):
        credentials_info = json.loads(os.environ["GOOGLE_APPLICATION_CREDENTIALS_JSON"])
        return service_account.Credentials.from_service_account_info(
            credentials_info, scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
    return service_account.Credentials.from_service_account_file(
        SETTINGS.GOOGLE_APPLICATION_CREDENTIALS,
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )


google_credentials = get_google_credentials()
