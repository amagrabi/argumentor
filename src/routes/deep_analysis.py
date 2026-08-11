"""Deep analysis: a second, deeper pass over an already-evaluated argument.

A paid capability for the same reason export and custom questions are. Quota
cannot convert this product's engaged users — the most active free user ever
averaged 3 answers a month against a 30/month allowance and never met a wall —
so the paid tiers need capabilities rather than bigger numbers.

What it does that the scored pass does not: reconstruct the inference, name the
premises the argument needs but never argues for, steelman the objections it
never met, and say concretely how to rebuild it. Different prompt, different
schema, no scores, and a Pro-tier model with thinking. See
services/deep_analysis.py and DEEP_ANALYSIS_MODEL in config.py.

Never automatic — it costs ~16x a normal evaluation, so it only ever runs on an
explicit button press against an answer the caller already owns.
"""

import logging
from datetime import UTC, datetime

from flask import Blueprint, jsonify, request, session

from config import get_settings
from extensions import db
from models import Answer
from services.deep_analysis import run_deep_analysis
from services.user_service import load_session_user
from utils import get_monthly_deep_analysis_count, get_monthly_deep_analysis_limit

logger = logging.getLogger(__name__)
deep_analysis_bp = Blueprint("deep_analysis", __name__)

SETTINGS = get_settings()


@deep_analysis_bp.route("/deep_analysis", methods=["POST"])
def create_deep_analysis():
    user_uuid = session.get("user_id")
    if not user_uuid:
        return jsonify({"error": "User not identified."}), 400

    answer_id = (request.get_json(silent=True) or {}).get("answer_id")
    if not answer_id:
        return jsonify({"error": "answer_id is required."}), 400

    # An anonymous visitor has no users row at all, so this is None for exactly
    # the callers who are not entitled to the feature anyway.
    user = load_session_user()
    if not user or user.tier not in ("plus", "pro"):
        return jsonify(
            {
                "error": "Deep analysis is available on Plus and Pro.",
                "status": "upgrade_required",
            }
        ), 402

    answer = Answer.query.filter_by(id=answer_id).first()
    if not answer:
        return jsonify({"error": "Answer not found."}), 404
    # 404 rather than 403, matching submit_challenge_response: this must not
    # confirm that someone else's answer id exists.
    if answer.user_uuid != user_uuid:
        logger.warning("Deep analysis denied: %s does not own %s", user_uuid, answer_id)
        return jsonify({"error": "Answer not found."}), 404

    # Already run: return the stored result rather than paying for it twice.
    # Checked before the quota so revisiting an analysis never costs an allowance.
    if answer.deep_analysis:
        return jsonify({"analysis": answer.deep_analysis, "cached": True})

    monthly_count = get_monthly_deep_analysis_count(user_uuid)
    monthly_limit = get_monthly_deep_analysis_limit(user.tier)
    if monthly_count >= monthly_limit:
        return jsonify(
            {
                "error": (
                    f"Monthly deep analysis limit reached ({monthly_limit})."
                    if session.get("language", SETTINGS.DEFAULT_LANGUAGE) == "en"
                    else f"Monatliches Limit für Tiefenanalysen erreicht ({monthly_limit})."
                ),
                "status": "limit_reached",
            }
        ), 429

    language = session.get("language", SETTINGS.DEFAULT_LANGUAGE)
    try:
        analysis = run_deep_analysis(answer, language)
    except Exception as e:
        # Nothing is counted against the allowance for a failed call. The user
        # gets a plain failure and can press the button again.
        logger.error("Deep analysis failed for answer %s: %s", answer_id, e)
        db.session.rollback()
        return jsonify({"error": "Deep analysis failed. Please try again."}), 502

    answer.deep_analysis = analysis
    answer.deep_analysis_created_at = datetime.now(UTC)
    user.monthly_deep_analysis_count = (user.monthly_deep_analysis_count or 0) + 1
    user.last_monthly_deep_analysis_reset = (
        user.last_monthly_deep_analysis_reset or datetime.now(UTC)
    )
    db.session.commit()

    logger.info(
        "Deep analysis %s/%s for user %s on answer %s",
        user.monthly_deep_analysis_count,
        monthly_limit,
        user_uuid,
        answer_id,
    )

    return jsonify(
        {
            "analysis": analysis,
            "cached": False,
            "remaining": max(monthly_limit - user.monthly_deep_analysis_count, 0),
        }
    )
