"""Test fixtures.

Importing the app is not free: `extensions.py` resolves Google credentials and
`services/llm.py` builds a Vertex AI client, both at module import time. Neither
works without a service account, so they are stubbed before `app` is imported at
all — and the environment has to be set before that too, because `get_settings()`
is `lru_cache`d and runs on the first import of `config`.
"""

import os
import tempfile
from unittest import mock

import pytest
from flask.testing import FlaskClient

_DB_PATH = os.path.join(tempfile.mkdtemp(prefix="argumentor-tests-"), "test.db")

os.environ.update(
    {
        "DEV": "true",
        "LOG_LEVEL": "WARNING",
        "SECRET_KEY": "test-secret-key",
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{_DB_PATH}",
        "USE_LLM_EVALUATOR": "false",
    }
)

mock.patch(
    "google.auth.default", return_value=(mock.MagicMock(), "test-project")
).start()
mock.patch("google.genai.Client", return_value=mock.MagicMock()).start()

from app import create_app  # noqa: E402
from extensions import db  # noqa: E402


class HttpsClient(FlaskClient):
    """A client that talks https, so session cookies actually stick.

    Talisman sets `SESSION_COOKIE_SECURE`, and the werkzeug cookie jar honours
    it: over the test client's default `http://localhost` the session cookie is
    set and then dropped, so every request looks like a first visit. Requesting
    https instead keeps the fixture faithful to production rather than switching
    the flag off.
    """

    def open(self, *args, **kwargs):
        kwargs.setdefault("base_url", "https://localhost")
        return super().open(*args, **kwargs)

    def session_transaction(self, *args, **kwargs):
        kwargs.setdefault("base_url", "https://localhost")
        return super().session_transaction(*args, **kwargs)


@pytest.fixture
def app():
    application = create_app()
    application.config["TESTING"] = True
    application.test_client_class = HttpsClient

    with application.app_context():
        db.create_all()
        try:
            yield application
        finally:
            db.session.remove()
            db.drop_all()


@pytest.fixture
def client(app):
    """A client that keeps its cookies, i.e. behaves like a browser."""
    return app.test_client()
