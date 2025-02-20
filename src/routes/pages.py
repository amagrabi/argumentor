import json
import os
import uuid

from flask import (
    Blueprint,
    current_app,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import current_user

from config import get_settings
from extensions import db, limiter
from models import Answer, Feedback, User
from services.leveling import get_level_info
from services.question_service import load_questions
from utils import (
    get_daily_evaluation_count,
    get_daily_voice_count,
    get_eval_limit,
    get_voice_limit,
)

pages_bp = Blueprint("pages", __name__)

SETTINGS = get_settings()


def calculate_valid_xp(answer):
    """Template filter to calculate actual XP earned considering relevance threshold"""
    total_xp = 0
    if (
        answer.evaluation_scores.get("Relevance", 0)
        >= SETTINGS.RELEVANCE_THRESHOLD_FOR_XP
    ):
        total_xp += answer.xp_earned

    if (
        answer.challenge_response
        and answer.challenge_evaluation_scores.get("Relevance", 0)
        >= SETTINGS.RELEVANCE_THRESHOLD_FOR_XP
    ):
        total_xp += answer.challenge_xp_earned

    return total_xp


# Register the template filter
@pages_bp.app_template_filter("calculate_valid_xp")
def calculate_valid_xp_filter(answer):
    return calculate_valid_xp(answer)


@pages_bp.route("/")
def home():
    # Use the authenticated user's ID if logged in
    if current_user.is_authenticated:
        user = current_user
        session["user_id"] = current_user.uuid  # Sync session with logged-in user
    else:
        # The middleware (ensure_user_id) will have already created an anonymous user if needed
        user = User.query.filter_by(uuid=session["user_id"]).first()
        if not user:
            # If user not found, create a new anonymous user
            new_id = str(uuid.uuid4())
            session["user_id"] = new_id
            default_username = f"anonymous_{new_id[:8]}"
            user = User(uuid=new_id, username=default_username)
            db.session.add(user)
            db.session.commit()

    xp = user.xp
    level_info = get_level_info(xp)

    return render_template("index.html", xp=xp, level_info=level_info)


@pages_bp.route("/how_it_works")
def how_it_works():
    # First check for the query parameter; if not present, use the session language (default to "en")
    lang = request.args.get("lang") or session.get("language", "en")
    trans_file = os.path.join(
        current_app.root_path, "static", "translations", f"{lang}.json"
    )
    with open(trans_file, "r", encoding="utf-8") as f:
        translations = json.load(f)

    # Get the evaluation criteria from the translation file
    criteria = translations.get("evaluationCriteria", {})

    # Create a mapping for dimension translations
    dimension_mapping = {
        "Relevance": translations["evaluation"]["scores"]["relevance"],
        "Logical Structure": translations["evaluation"]["scores"]["logic"],
        "Clarity": translations["evaluation"]["scores"]["clarity"],
        "Depth": translations["evaluation"]["scores"]["depth"],
        "Objectivity": translations["evaluation"]["scores"]["objectivity"],
        "Creativity": translations["evaluation"]["scores"]["creativity"],
    }

    return render_template(
        "how_it_works.html",
        criteria=criteria,
        dimension_mapping=dimension_mapping,
        translations=translations,
    )


@pages_bp.route("/how_to_improve")
def how_to_improve():
    # Get language from query parameter or session (default to "en")
    lang = request.args.get("lang") or session.get("language", "en")
    trans_file = os.path.join(
        current_app.root_path, "static", "translations", f"{lang}.json"
    )

    with open(trans_file, "r", encoding="utf-8") as f:
        translations = json.load(f)

    # Get the page content from translations
    page_content = translations.get("howToImprovePage", {})

    return render_template(
        "how_to_improve.html", page_content=page_content, translations=translations
    )


@pages_bp.route("/support")
def support():
    return render_template("support.html")


@pages_bp.route("/profile")
def profile():
    if "user_id" not in session:
        return redirect(url_for("pages.home"))

    user = User.query.filter_by(uuid=session["user_id"]).first()
    if not user:
        return redirect(url_for("pages.home"))

    level_info = get_level_info(user.xp)
    daily_eval_count = get_daily_evaluation_count(user.uuid)
    eval_limit = get_eval_limit(user.tier)
    daily_voice_count = get_daily_voice_count(user.uuid)
    voice_limit = get_voice_limit(user.tier)

    # Query answers sorted by created_at descending and then by id descending to break ties
    answers = (
        Answer.query.filter_by(user_uuid=user.uuid)
        .order_by(Answer.created_at.desc(), Answer.id.desc())
        .all()
    )
    answers_dict = [answer.to_dict() for answer in answers]

    # Sync session XP with database.
    session["xp"] = user.xp

    return render_template(
        "profile.html",
        xp=user.xp,
        level_info=level_info,
        user=user,
        answers_json=answers_dict,
        daily_eval_count=daily_eval_count,
        eval_limit=eval_limit,
        daily_voice_count=daily_voice_count,
        voice_limit=voice_limit,
    )


@pages_bp.route("/submit_feedback", methods=["POST"])
@limiter.limit(
    SETTINGS.SUBMISSION_RATE_LIMITS,
    error_message="Too many submissions. Please wait before trying again.",
)
def submit_feedback():
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 400

    data = request.json
    message = data.get("message", "").strip()
    category = data.get("category", "").strip()

    if not message or not category:
        return jsonify({"error": "Message and category are required"}), 400

    feedback = Feedback(
        user_uuid=session.get("user_id"), message=message, category=category
    )

    db.session.add(feedback)
    db.session.commit()

    return jsonify({"success": True})


@pages_bp.route("/set_language", methods=["POST"])
def set_language():
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 400

    data = request.get_json()
    language = data.get("language")

    if language in ["en", "de"]:
        session["language"] = language
        load_questions()
        # If logged in, persist language preference in the user's account.
        if current_user.is_authenticated:
            current_user.preferred_language = language
            db.session.commit()
        return jsonify({"status": "success"})

    return jsonify({"status": "error", "message": "Invalid language"}), 400


@pages_bp.route("/privacy")
def privacy():
    return render_template("privacy.html")


@pages_bp.route("/terms")
def terms():
    return render_template("terms.html")


@pages_bp.route("/contact")
def contact():
    return render_template("contact.html")
