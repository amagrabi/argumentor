"""Signed, unguessable share tokens for individual answers.

No database column and no migration: the token carries the answer id plus an
HMAC of it under SECRET_KEY, so only the server can mint a valid one. A caller
cannot enumerate other people's answers by guessing.

Consequences of being stateless, both acceptable for v1:
  - There is no per-answer revoke. Rotating SECRET_KEY invalidates every link
    at once (and also every session, so it is not a casual operation).
  - The server cannot tell whether a link was ever actually shared.
"""

import hmac
from hashlib import sha256

from config import get_settings

SETTINGS = get_settings()

# 16 hex chars = 64 bits. Forging one without SECRET_KEY is infeasible, and the
# answer id is a UUID so the pair is not enumerable either.
_SIG_LENGTH = 16


def _signature(answer_id: str) -> str:
    return hmac.new(
        SETTINGS.SECRET_KEY.encode(),
        f"share:{answer_id}".encode(),
        sha256,
    ).hexdigest()[:_SIG_LENGTH]


def make_share_token(answer_id: str) -> str:
    return f"{answer_id}.{_signature(answer_id)}"


def verify_share_token(token: str) -> str | None:
    """Return the answer id if the token is authentic, otherwise None."""
    if not token or "." not in token:
        return None
    answer_id, _, signature = token.rpartition(".")
    if not answer_id or not signature:
        return None
    # compare_digest to avoid leaking the signature through timing.
    if not hmac.compare_digest(signature, _signature(answer_id)):
        return None
    return answer_id
