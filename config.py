from functools import lru_cache

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    DEV: bool = False

    SECRET_KEY: str = Field(default="fallback")  # Flask

    SQLALCHEMY_DATABASE_URI: str = Field(default="sqlite:///argumentor.db")
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = Field(default=False)

    GCLOUD_PROJECT_NAME: str = Field(default="fallback")
    GCLOUD_PROJECT_REGION: str = Field(default="us-central1")
    GOOGLE_APPLICATION_CREDENTIALS: str = Field(default="fallback")

    GOOGLE_CLIENT_ID: str = Field(default="fallback")
    GOOGLE_CLIENT_SECRET: str = Field(default="fallback")

    USE_LLM_EVALUATOR: bool = Field(default=True)

    MODEL: str = Field(default="gemini-2.0-flash-001")

    MAX_CLAIM: int = Field(default=200)
    MAX_ARGUMENT: int = Field(default=1000)
    MAX_COUNTERARGUMENT: int = Field(default=500)

    RELEVANCE_THRESHOLD_FOR_XP: int = Field(default=3)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache()
def get_settings():
    return Settings()
