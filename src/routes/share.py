"""Unlisted share pages for a single evaluated answer.

Unlisted, not public: the pages carry noindex/nofollow and are reachable only
by the signed link. That was a deliberate v1 choice -- the growth benefit comes
from people passing links around, and it needs no consent flow because nothing
is published or indexed.
"""

import logging

from flask import Blueprint, abort, jsonify, render_template, request, session

from models import Answer
from services.share_service import make_share_token, verify_share_token

logger = logging.getLogger(__name__)
share_bp = Blueprint("share", __name__)


@share_bp.route("/create_share_link", methods=["POST"])
def create_share_link():
    """Mint a share link for one of the caller's own answers."""
    user_uuid = session.get("user_id")
    if not user_uuid:
        return jsonify({"error": "User not identified."}), 400

    answer_id = (request.get_json(silent=True) or {}).get("answer_id")
    if not answer_id:
        return jsonify({"error": "answer_id is required."}), 400

    answer = Answer.query.filter_by(id=answer_id).first()
    if not answer:
        return jsonify({"error": "Answer not found."}), 404
    # Only the author may create a link, otherwise knowing an answer id would be
    # enough to publish someone else's writing.
    if answer.user_uuid != user_uuid:
        logger.warning("Share link denied: %s does not own %s", user_uuid, answer_id)
        return jsonify({"error": "Not your answer."}), 403

    token = make_share_token(answer_id)
    return jsonify(
        {
            "token": token,
            "url": f"https://www.argumentorai.com/share/{token}",
        }
    )


@share_bp.route("/share/<token>", methods=["GET"])
def view_shared_answer(token):
    answer_id = verify_share_token(token)
    if not answer_id:
        abort(404)

    answer = Answer.query.filter_by(id=answer_id).first()
    if not answer:
        abort(404)

    scores = answer.evaluation_scores or {}
    feedback = answer.evaluation_feedback or {}
    return render_template(
        "share.html",
        answer=answer,
        scores=scores,
        overall_feedback=feedback.get("Overall") or feedback.get("overall"),
        dimensions=[
            (name, scores.get(name), feedback.get(name))
            for name in (
                "Relevance",
                "Logical Structure",
                "Clarity",
                "Depth",
                "Objectivity",
                "Creativity",
            )
            if scores.get(name) is not None
        ],
    )
