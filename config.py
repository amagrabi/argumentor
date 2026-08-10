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

    # Connection pool sizing. These are per gunicorn worker, so the ceiling is
    # DB_POOL_SIZE + DB_MAX_OVERFLOW, times workers, times running instances.
    # Cloud Run runs several instances, so keep these small enough that a
    # scale-out cannot exhaust the database's connection limit.
    DB_POOL_SIZE: int = Field(default=2)
    DB_MAX_OVERFLOW: int = Field(default=3)

    GCLOUD_PROJECT_NAME: str = Field(default="fallback")
    # Only used as the Vertex AI location for the genai clients. Gemini 3.x is
    # served exclusively from the "global" endpoint — it 404s in us-central1.
    GCLOUD_PROJECT_REGION: str = Field(default="global")
    GOOGLE_APPLICATION_CREDENTIALS: str = Field(default="fallback")
    GCS_BUCKET: str = Field(default="fallback")  # for voice recordings

    # For Google logins
    GOOGLE_CLIENT_ID: str = Field(default="fallback")
    # Unused: sign-in uses Google Identity Services and verifies the returned ID
    # token against GOOGLE_CLIENT_ID, which needs no secret. Only an
    # authorization-code exchange would, and we do not perform one.
    GOOGLE_CLIENT_SECRET: str = Field(default="fallback")

    # OpenAI API configuration
    OPENAI_API_KEY: str = Field(default="fallback")
    WHISPER_MODEL: str = Field(default="whisper-1")  # Current Whisper model version
    WHISPER_RESPONSE_FORMAT: str = Field(default="text")  # text, vtt, srt, verbose_json

    # Stripe settings for subscriptions
    STRIPE_SECRET_KEY: str = Field(default="sk_test_your_test_key")
    STRIPE_PUBLIC_KEY: str = Field(default="pk_test_your_test_key")
    STRIPE_WEBHOOK_SECRET: str = Field(default="whsec_your_webhook_secret")
    STRIPE_PLUS_PRICE_ID: str = Field(default="price_plus_id")
    STRIPE_PRO_PRICE_ID: str = Field(default="price_pro_id")

    MAIL_SERVER: str = Field(default="smtp.gmail.com")
    MAIL_PORT: int = Field(default=587)
    MAIL_USE_TLS: bool = Field(default=True)
    MAIL_USERNAME: str = Field(default="your-email@gmail.com")
    MAIL_PASSWORD: str = Field(default="your-app-password")
    MAIL_DEFAULT_SENDER: str = Field(default="your-email@gmail.com")

    # If false, cheaper dummy responses will be returned
    USE_LLM_EVALUATOR: bool = Field(default=True)

    # Measured against the production prompt (both languages) in Aug 2026:
    # gemini-2.5-flash took 17-22s and $6.90-10.00 per 1k evaluations, because it
    # spends 1200-2400 hidden thinking tokens per call. This model is ~3.5x faster
    # and ~2.6x cheaper with comparable feedback length. gemini-3.6-flash was both
    # slower and dearer than this with no visible quality gain.
    MODEL: str = Field(default="gemini-3.5-flash-lite")  # LLM

    # Maximum characters allowed for each field
    MAX_CLAIM: int = Field(default=200)
    MAX_ARGUMENT: int = Field(default=2000)
    MAX_COUNTERARGUMENT: int = Field(default=800)
    MAX_VOICE_ANSWER: int = Field(default=3000)
    MAX_CHALLENGE_RESPONSE: int = Field(default=3000)

    # Below this threshold, no XP is awarded
    RELEVANCE_THRESHOLD_FOR_XP: int = Field(default=3)
    # Above this threshold, answers are considered too similar
    SIMILARITY_THRESHOLD: float = Field(default=0.8)

    SUBMISSION_RATE_LIMITS: str = Field(default="10 per minute, 100 per day")
    # Transcription is the most expensive endpoint (Whisper + GCS + an LLM call),
    # so it gets a tighter burst limit than text submissions.
    VOICE_RATE_LIMITS: str = Field(default="5 per minute, 30 per hour")

    # Anonymous is a taster, not a usable tier: every anonymous evaluation is an
    # unauthenticated LLM call. Free is deliberately generous enough to build a
    # habit — this is a practice product, and users only convert once they have
    # felt themselves improve. At current model cost a free user is ~8 cents/month.
    TIER_MONTHLY_EVAL_LIMITS: ClassVar[Dict[str, int]] = {
        "anonymous": 3,
        "free": 30,
        "plus": 150,
        "pro": 500,
    }
    # Voice costs more than text (transcription + storage + the same LLM call), so
    # it is the paid differentiator rather than being offered at parity.
    TIER_MONTHLY_VOICE_LIMITS: ClassVar[Dict[str, int]] = {
        "anonymous": 1,
        "free": 5,
        "plus": 50,
        "pro": 250,
    }

    # Burst protection: roughly a fifth of the monthly allowance, so a compromised
    # or scripted account cannot spend a whole month's budget in one sitting.
    # These are enforced — previously they were set above the monthly limits,
    # which silently disabled them.
    TIER_DAILY_EVAL_LIMITS: ClassVar[Dict[str, int]] = {
        "anonymous": 3,
        "free": 8,
        "plus": 30,
        "pro": 100,
    }
    TIER_DAILY_VOICE_LIMITS: ClassVar[Dict[str, int]] = {
        "anonymous": 1,
        "free": 3,
        "plus": 12,
        "pro": 50,
    }

    # The visit table is append-only and nothing reads it, so it is kept only as
    # a rough first-party traffic record and trimmed nightly by /prune-visits.
    # Ninety days is enough to compare this month against last quarter; at a
    # 500 MB Supabase cap, keeping it forever is not an option.
    VISIT_RETENTION_DAYS: int = Field(default=90)

    SUPPORTED_LANGUAGES: ClassVar[List[str]] = ["en", "de"]
    DEFAULT_LANGUAGE: str = "en"
    LANGUAGE_CODES: ClassVar[Dict[str, str]] = {"en": "en-US", "de": "de-DE"}

    DEFAULT_QUESTION: str = "experiences"  # id of first question new users see

    # Memory management thresholds for individual workers (in MB)
    # Basic dyno on Heroku has 512MB and we currently use two workers (baseline memory usage per worker around 190mb)
    MEMORY_WARN_THRESHOLD: int = Field(default=220)  # Log warning and trigger GC
    MEMORY_RESTART_THRESHOLD: int = Field(default=250)  # Trigger worker restart

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
