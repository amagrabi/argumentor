import inspect
from datetime import UTC, datetime, time

from config import get_settings

SETTINGS = get_settings()


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
    return SETTINGS.TIER_EVAL_LIMITS.get(tier, SETTINGS.TIER_EVAL_LIMITS["anonymous"])
