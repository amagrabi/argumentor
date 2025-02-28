import json

from flask import Blueprint, jsonify, request, session
from flask_login import current_user

from extensions import db
from src.constants.categories import DEFAULT_CATEGORIES
from models import UserAchievement

preferences_bp = Blueprint("preferences", __name__)


@preferences_bp.route("/update_categories", methods=["POST"])
def update_categories():
    data = request.get_json() or {}
    categories = data.get("categories", [])
    # Save the categories in the session so that unlogged users persist their selection.
    session["selected_categories"] = categories

    if current_user.is_authenticated:
        try:
            # Save the serialized list (or you could use another format) in the user's record.
            current_user.category_preferences = json.dumps(categories)
            db.session.commit()
        except Exception:
            return jsonify({"error": "Failed to update preferences"}), 500

    return jsonify({"message": "Preferences updated", "categories": categories})


@preferences_bp.route("/get_categories", methods=["GET"])
def get_categories():
    categories = []
    if current_user.is_authenticated and current_user.category_preferences:
        try:
            categories = json.loads(current_user.category_preferences)
        except json.JSONDecodeError:
            pass
    else:
        categories = session.get("selected_categories", DEFAULT_CATEGORIES)

    return jsonify({"categories": categories})


@preferences_bp.route("/get_user_achievements", methods=["GET"])
def get_user_achievements():
    """Return the user's earned achievements."""
    try:
        if current_user.is_authenticated:
            # Query user's achievements from database
            user_achievements = UserAchievement.query.filter_by(
                user_id=current_user.id
            ).all()

            # Extract achievement IDs
            earned_achievement_ids = [ua.achievement_id for ua in user_achievements]
        else:
            # For non-authenticated users, use session-stored achievements
            earned_achievement_ids = session.get("earned_achievements", [])

        return jsonify({"earned_achievements": earned_achievement_ids})
    except Exception as e:
        return jsonify({"error": str(e), "earned_achievements": []}), 500
