"""Session-scoped user identity.

Anonymous visitors carry a UUID in their session cookie, but they get no `users`
row until they do something that needs one — submit an answer, record voice,
leave feedback, or start a checkout.

Until Aug 2026 the identity was persisted eagerly, by `ensure_user_id` on the
first non-static request. Since bots and vulnerability scanners never return a
cookie, every single one of their requests minted a fresh identity and inserted a
row: the users table reached 253,915 rows of which 253,841 (99.97%) had no
answers, 86 MB against a 500 MB Supabase cap.

Read paths therefore cannot assume a row exists behind `session["user_id"]`:

- `get_session_user()` when you only need to *read* the user — rendering a page,
  checking a quota. Returns an unsaved placeholder when there is no row.
- `persist_session_user()` when you are about to write something that references
  `users.uuid`. Returns a committed row.
"""

import logging
import uuid

from flask import current_app, request, session
from flask_login import current_user
from sqlalchemy.exc import IntegrityError

from config import get_settings
from extensions import db
from models import User

logger = logging.getLogger(__name__)
SETTINGS = get_settings()


def session_user_uuid():
    """Return this session's user UUID, minting one if the session has none.

    Touches no database. Called from `ensure_user_id` on every non-static
    request, so it has to stay free.
    """
    if current_user.is_authenticated:
        if session.get("user_id") != current_user.uuid:
            session["user_id"] = current_user.uuid
            session.modified = True
        return current_user.uuid

    if "user_id" not in session:
        session["user_id"] = str(uuid.uuid4())
        # Persist the cookie across browser restarts, so a returning visitor
        # keeps their identity (and their spent quota) rather than getting a
        # fresh allowance.
        session.permanent = True
        session.modified = True

    return session["user_id"]


def session_is_new():
    """True when the client sent no session cookie with this request.

    A real browser returns the cookie on its next request, so this stays True
    only for clients that do not keep cookies at all — which is nearly every
    bot. Read off the request rather than tracked in `flask.g`, because `g` is
    bound to the *app* context, and Flask reuses an already-pushed one across
    requests instead of creating a fresh one per request.
    """
    cookie_name = current_app.session_interface.get_cookie_name(current_app)
    return cookie_name not in request.cookies


def load_session_user():
    """Return the persisted User for this session, or None if there is no row."""
    user_uuid = session.get("user_id")
    if not user_uuid:
        return None
    return User.query.filter_by(uuid=user_uuid).first()


def get_session_user():
    """Return a User for this session, persisted if it exists, otherwise a placeholder.

    The placeholder is a real `User` instance that is deliberately never added to
    the SQLAlchemy session. It reads like the fresh anonymous user it represents
    — no answers, no achievements, no XP — without writing anything.

    Never pass the result to code that writes a row referencing `users.uuid`;
    use `persist_session_user()` for that.
    """
    user = load_session_user()
    if user is not None:
        return user
    return _new_anonymous_user(session_user_uuid())


def persist_session_user():
    """Materialise this session's user as a committed row, and return it.

    Idempotent — returns the existing row when there is one. Call it immediately
    before writing anything with a foreign key to `users.uuid`.

    It commits rather than leaving the insert pending, so callers that then make
    a slow external call (Stripe, an LLM) are not holding a write transaction
    open across it. The cost is that a caller which fails afterwards leaves a
    user row with nothing attached; harmless, and rare.
    """
    user_uuid = session_user_uuid()
    user = User.query.filter_by(uuid=user_uuid).first()
    if user is not None:
        return user

    user = _new_anonymous_user(user_uuid)
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        # Two concurrent requests on the same session can both reach this point.
        db.session.rollback()
        user = User.query.filter_by(uuid=user_uuid).first()
        if user is None:
            raise
        return user

    logger.info("Persisted anonymous user %s on first action", user_uuid)
    return user


def _anonymous_username(user_uuid):
    """Build the placeholder username for an anonymous user.

    The full UUID, not the 8-character prefix used before Aug 2026: `username`
    is unique, and 8 hex characters collide often enough to matter at a quarter
    of a million rows (~7 expected collisions), each one a 500 for an unlucky
    visitor. Anonymous usernames are never rendered — the UI shows "Anonymous"
    whenever `current_user.is_authenticated` is false — so the length is free.
    """
    return f"anonymous_{user_uuid}"


def _new_anonymous_user(user_uuid):
    """Build an unsaved anonymous User carrying the values a fresh row would have.

    Column defaults (`tier`, `xp`, the quota counters) are applied by the
    database on INSERT, so an instance that is never persisted has None in every
    one of them. They have to be set explicitly here, because
    `get_session_user()` hands this object to read paths: a None `tier` still
    resolves to the anonymous limits through `dict.get`'s fallback but reports
    the wrong upsell message, and a None `xp` breaks level lookups outright.
    """
    return User(
        uuid=user_uuid,
        username=_anonymous_username(user_uuid),
        tier="anonymous",
        xp=0,
        preferred_language=session.get("language", SETTINGS.DEFAULT_LANGUAGE),
        is_active=True,
        daily_voice_count=0,
        monthly_eval_count=0,
        monthly_voice_count=0,
    )
