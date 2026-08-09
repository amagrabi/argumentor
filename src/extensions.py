import json
import os

import google.auth
import openai
from flask import request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from google.oauth2 import service_account

from config import get_settings

SETTINGS = get_settings()

# Initialize Flask extensions
db = SQLAlchemy()

def client_identifier():
    """Best-effort client IP for rate limiting.

    Cloudflare sets CF-Connecting-IP to the true visitor address, which is more
    reliable than walking X-Forwarded-For. Falls back to the ProxyFix-corrected
    remote address for local development and for requests that somehow bypass
    Cloudflare.

    This is a backstop, not the primary defence: the *.run.app URL stays publicly
    reachable, so a caller going direct can forge CF-Connecting-IP. The
    authoritative per-IP gate is the Cloudflare rate-limiting rule, which sees the
    real client and runs before Cloud Run is ever invoked.
    """
    return request.headers.get("CF-Connecting-IP") or get_remote_address()


# Storage is deliberately in-memory. Shared storage would mean paying for Redis,
# and buckets here are only a per-instance backstop — Cloudflare owns real rate
# limiting. Consequence: these limits are per gunicorn worker and reset when an
# instance is recycled, so do not rely on the long windows.
limiter = Limiter(key_func=client_identifier)
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
