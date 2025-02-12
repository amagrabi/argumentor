import os
import uuid

import yaml
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
from extensions import db
from models import Feedback, User
from services.leveling import get_level_info

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
        # Existing anonymous user handling
        if "user_id" not in session:
            session["user_id"] = str(uuid.uuid4())
        user = User.query.filter_by(uuid=session["user_id"]).first()
        if not user:
            user = User(uuid=session["user_id"], xp=0)
            db.session.add(user)
            db.session.commit()

    xp = user.xp
    level_info = get_level_info(xp)
    xp = user.xp
    level_info = get_level_info(xp)

    return render_template("index.html", xp=xp, level_info=level_info)


@pages_bp.route("/how_it_works")
def how_it_works():
    criteria_path = os.path.join(
        current_app.root_path, "data", "evaluation_criteria.yaml"
    )
    with open(criteria_path, "r") as f:
        criteria = yaml.safe_load(f)
    settings = get_settings()
    return render_template(
        "how_it_works.html",
        criteria=criteria,
        relevance_threshold=settings.RELEVANCE_THRESHOLD_FOR_XP,
    )


@pages_bp.route("/reasoning_guide")
def reasoning_guide():
    data_path = os.path.join(current_app.root_path, "data", "biases_fallacies.yaml")
    with open(data_path, "r") as f:
        data = yaml.safe_load(f)
    biases = data.get("cognitive_biases", [])
    fallacies = data.get("logical_fallacies", [])
    return render_template("reasoning_guide.html", biases=biases, fallacies=fallacies)


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
    # Convert answers to dictionaries for JSON serialization
    answers_dict = [answer.to_dict() for answer in user.answers]
    # Sync session XP with database
    session["xp"] = user.xp
    return render_template(
        "profile.html",
        xp=user.xp,
        level_info=level_info,
        user=user,
        answers_json=answers_dict,
    )


@pages_bp.route("/submit_feedback", methods=["POST"])
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
