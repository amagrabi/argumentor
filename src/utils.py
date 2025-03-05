import inspect
from datetime import UTC, datetime, time

from flask_sqlalchemy import SQLAlchemy

from config import get_settings
from models import User

SETTINGS = get_settings()
db = SQLAlchemy()


def auto_dedent(obj, strip_newlines=False):
    """
    Recursively dedent and clean all string values in a nested structure.
    If strip_newlines is True, removes all extra whitespace (including newlines)
    by splitting the string and rejoining with a single space.
    """
    if isinstance(obj, str):
        cleaned = inspect.cleandoc(obj)
        if strip_newlines:
            return " ".join(cleaned.split())
        return cleaned
    elif isinstance(obj, list):
        return [auto_dedent(item, strip_newlines) for item in obj]
    elif isinstance(obj, dict):
        return {key: auto_dedent(val, strip_newlines) for key, val in obj.items()}
    return obj


def get_daily_evaluation_count(user_uuid):
    """
    Returns the total number of evaluation attempts made by the user today.
    Each initial answer submission counts as 1.
    If the answer has a non-null challenge_response, that counts as an additional evaluation attempt.
    """
    from models import Answer  # Import here to avoid circular imports

    today_start = datetime.combine(datetime.now(UTC).date(), time.min)
    answers = Answer.query.filter(
        Answer.user_uuid == user_uuid, Answer.created_at >= today_start
    ).all()
    count = 0
    for ans in answers:
        count += 1
        if ans.challenge_response:
            count += 1
    return count


def get_eval_limit(tier):
    """Returns the evaluation limit for a given user tier."""
    return SETTINGS.TIER_DAILY_EVAL_LIMITS.get(
        tier, SETTINGS.TIER_DAILY_EVAL_LIMITS["anonymous"]
    )


def get_daily_voice_count(user_uuid):
    """Returns the total number of voice transcription attempts made by the user today."""
    user = User.query.filter_by(uuid=user_uuid).first()
    if not user or not user.last_voice_transcription:
        return 0

    today_start = datetime.combine(datetime.now(UTC).date(), time.min)
    today_start = today_start.replace(tzinfo=UTC)

    # Ensure the datetime is timezone-aware before comparison
    last_transcription = user.last_voice_transcription
    if last_transcription.tzinfo is None:
        last_transcription = last_transcription.replace(tzinfo=UTC)

    if last_transcription < today_start:
        user.daily_voice_count = 0
        db.session.commit()
        return 0

    return user.daily_voice_count


def get_voice_limit(tier):
    """Returns the voice recording limit for a given user tier."""
    return SETTINGS.TIER_DAILY_VOICE_LIMITS.get(
        tier, SETTINGS.TIER_DAILY_VOICE_LIMITS["anonymous"]
    )


def get_monthly_eval_limit(tier):
    """Returns the monthly evaluation limit for a given user tier."""
    return SETTINGS.TIER_MONTHLY_EVAL_LIMITS.get(
        tier, SETTINGS.TIER_MONTHLY_EVAL_LIMITS["anonymous"]
    )


def get_monthly_voice_limit(tier):
    """Returns the monthly voice recording limit for a given user tier."""
    return SETTINGS.TIER_MONTHLY_VOICE_LIMITS.get(
        tier, SETTINGS.TIER_MONTHLY_VOICE_LIMITS["anonymous"]
    )


def get_monthly_evaluation_count(user_uuid):
    """
    Returns the total number of evaluation attempts made by the user in the current month.
    Also resets the counter if we're in a new month.
    """
    from models import User  # Import here to avoid circular imports

    user = User.query.filter_by(uuid=user_uuid).first()
    if not user:
        return 0

    # Get the first day of the current month
    now = datetime.now(UTC)
    first_day_of_month = datetime(now.year, now.month, 1, tzinfo=UTC)

    # If we've never reset or it's a new month, reset the counter
    if not user.last_monthly_eval_reset:
        user.monthly_eval_count = 0
        user.last_monthly_eval_reset = now
        db.session.commit()
        return 0

    # Ensure the datetime is timezone-aware before comparison
    last_reset = user.last_monthly_eval_reset
    if last_reset.tzinfo is None:
        last_reset = last_reset.replace(tzinfo=UTC)

    if last_reset < first_day_of_month:
        user.monthly_eval_count = 0
        user.last_monthly_eval_reset = now
        db.session.commit()
        return 0

    return user.monthly_eval_count


def get_monthly_voice_count(user_uuid):
    """
    Returns the total number of voice transcription attempts made by the user in the current month.
    Also resets the counter if we're in a new month.
    """
    user = User.query.filter_by(uuid=user_uuid).first()
    if not user:
        return 0

    # Get the first day of the current month
    now = datetime.now(UTC)
    first_day_of_month = datetime(now.year, now.month, 1, tzinfo=UTC)

    # If we've never reset or it's a new month, reset the counter
    if not user.last_monthly_voice_reset:
        user.monthly_voice_count = 0
        user.last_monthly_voice_reset = now
        db.session.commit()
        return 0

    # Ensure the datetime is timezone-aware before comparison
    last_reset = user.last_monthly_voice_reset
    if last_reset.tzinfo is None:
        last_reset = last_reset.replace(tzinfo=UTC)

    if last_reset < first_day_of_month:
        user.monthly_voice_count = 0
        user.last_monthly_voice_reset = now
        db.session.commit()
        return 0

    return user.monthly_voice_count
