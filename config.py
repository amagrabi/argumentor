from functools import lru_cache

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    SECRET_KEY: str = Field(default="fallback")  # Flask

    SQLALCHEMY_DATABASE_URI: str = Field(default="sqlite:///argumentor.db")
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = Field(default=False)

    GCLOUD_PROJECT_NAME: str = Field(default="fallback")
    GCLOUD_PROJECT_REGION: str = Field(default="us-central1")
    GOOGLE_APPLICATION_CREDENTIALS: str = Field(default="fallback")

    USE_LLM_EVALUATOR: bool = Field(default=True)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache()
def get_settings():
    return Settings()
