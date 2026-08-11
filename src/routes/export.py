"""Export a user's own arguments and evaluations as a single HTML file.

A paid capability, for the same reason custom questions are: quota cannot
convert engaged users, so the paid tiers need capabilities rather than bigger
numbers. A portfolio of your own reasoning is the thing a student or debater has
a reason to keep.

Deliberately one self-contained HTML file rather than PDF: no new dependency, no
extra weight in a 1.2 GB image, and it prints to PDF from any browser.
"""

import logging
from datetime import UTC, datetime

from flask import Blueprint, Response, jsonify, render_template, session

from models import Answer
from services.user_service import get_session_user

logger = logging.getLogger(__name__)
export_bp = Blueprint("export", __name__)

DIMENSIONS = (
    "Logical Structure",
    "Clarity",
    "Depth",
    "Objectivity",
    "Creativity",
)


@export_bp.route("/export", methods=["GET"])
def export_answers():
    user_uuid = session.get("user_id")
    if not user_uuid:
        return jsonify({"error": "User not identified."}), 400

    user = get_session_user()
    if not user or user.tier not in ("plus", "pro"):
        return jsonify(
            {
                "error": "Export is available on Plus and Pro.",
                "status": "upgrade_required",
            }
        ), 402

    answers = (
        Answer.query.filter_by(user_uuid=user_uuid)
        .order_by(Answer.created_at.desc())
        .all()
    )

    entries = []
    for a in answers:
        scores = a.evaluation_scores or {}
        feedback = a.evaluation_feedback or {}
        entries.append(
            {
                "answer": a,
                "overall": scores.get("Overall"),
                "overall_feedback": feedback.get("Overall"),
                # Relevance is excluded here for the same reason it is excluded
                # from the UI: it gates XP rather than grading the argument.
                "dimensions": [
                    (n, scores.get(n), feedback.get(n))
                    for n in DIMENSIONS
                    if scores.get(n) is not None
                ],
            }
        )

    html = render_template(
        "export.html",
        user=user,
        entries=entries,
        generated_at=datetime.now(UTC).strftime("%Y-%m-%d"),
    )
    stamp = datetime.now(UTC).strftime("%Y%m%d")
    return Response(
        html,
        mimetype="text/html",
        headers={
            "Content-Disposition": f'attachment; filename="argumentor-{stamp}.html"',
            # An export is per-user; never let a proxy or the browser reuse it.
            "Cache-Control": "no-store, private",
        },
    )
