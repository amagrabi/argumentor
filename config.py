from functools import lru_cache
from typing import ClassVar, Dict, List

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    DEV: bool = False
    LOG_LEVEL: str = Field(default="DEBUG")

    SECRET_KEY: str = Field(default="fallback")  # Flask

    SQLALCHEMY_DATABASE_URI: str = Field(
        default="postgresql+psycopg2://postgres:password@localhost:5432/argumentor"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = Field(default=False)

    GCLOUD_PROJECT_NAME: str = Field(default="fallback")
    GCLOUD_PROJECT_REGION: str = Field(default="us-central1")
    GOOGLE_APPLICATION_CREDENTIALS: str = Field(default="fallback")
    GCS_BUCKET: str = Field(default="fallback")  # for voice recordings

    # For Google logins
    GOOGLE_CLIENT_ID: str = Field(default="fallback")
    GOOGLE_CLIENT_SECRET: str = Field(default="fallback")

    MAIL_SERVER: str = Field(default="smtp.gmail.com")
    MAIL_PORT: int = Field(default=587)
    MAIL_USE_TLS: bool = Field(default=True)
    MAIL_USERNAME: str = Field(default="your-email@gmail.com")
    MAIL_PASSWORD: str = Field(default="your-app-password")
    MAIL_DEFAULT_SENDER: str = Field(default="your-email@gmail.com")

    # If false, cheaper dummy responses will be returned
    USE_LLM_EVALUATOR: bool = Field(default=True)

    MODEL: str = Field(default="gemini-2.0-flash-001")  # LLM

    # Voice transcription
    VOICE_MODEL: str = Field(
        default="telephony"
    )  # Alternative: default, telephony, latest_long
    VOICE_ENHANCED: bool = Field(default=True)
    VOICE_PUNCTUATION: bool = Field(default=True)

    # Maximum characters allowed for each field
    MAX_CLAIM: int = Field(default=200)
    MAX_ARGUMENT: int = Field(default=1000)
    MAX_COUNTERARGUMENT: int = Field(default=500)

    # Below this threshold, no XP is awarded
    RELEVANCE_THRESHOLD_FOR_XP: int = Field(default=3)
    # Above this threshold, answers are considered too similar
    SIMILARITY_THRESHOLD: float = Field(default=0.8)

    SUBMISSION_RATE_LIMITS: str = Field(default="10 per minute, 100 per day")

    TIER_EVAL_LIMITS: ClassVar[Dict[str, int]] = {
        "anonymous": 10,
        "free": 20,
        "plus": 100,
    }
    TIER_VOICE_LIMITS: ClassVar[Dict[str, int]] = {
        "anonymous": 10,
        "free": 20,
        "plus": 100,
    }

    SUPPORTED_LANGUAGES: ClassVar[List[str]] = ["en", "de"]
    DEFAULT_LANGUAGE: str = "en"
    LANGUAGE_CODES: ClassVar[Dict[str, str]] = {"en": "en-US", "de": "de-DE"}

    DEFAULT_QUESTION: str = "experiences"  # id of first question new users see

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache()
def get_settings():
    settings = Settings()
    # Heroku provides DATABASE_URL starting with "postgres://". Replace it if needed.
    if settings.SQLALCHEMY_DATABASE_URI.startswith("postgres://"):
        settings.SQLALCHEMY_DATABASE_URI = settings.SQLALCHEMY_DATABASE_URI.replace(
            "postgres://", "postgresql://", 1
        )
    return settings
