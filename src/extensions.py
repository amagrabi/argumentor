import json
import os

import google.auth
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


SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]


# Initialize Google credentials
def get_google_credentials():
    if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON"):
        credentials_info = json.loads(os.environ["GOOGLE_APPLICATION_CREDENTIALS_JSON"])
        return service_account.Credentials.from_service_account_info(
            credentials_info, scopes=SCOPES
        )
    key_file = SETTINGS.GOOGLE_APPLICATION_CREDENTIALS
    if key_file and key_file != "fallback" and os.path.exists(key_file):
        return service_account.Credentials.from_service_account_file(
            key_file, scopes=SCOPES
        )
    # On Cloud Run (and any GCP runtime) the attached service account is picked
    # up via Application Default Credentials, so no key file is needed.
    credentials, _ = google.auth.default(scopes=SCOPES)
    return credentials


google_credentials = get_google_credentials()
