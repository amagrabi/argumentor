from flask import Blueprint, jsonify, request, session

from errors import json_error
from services.question_service import (
    find_question_by_id,
    get_all_questions,
    get_fixed_question,
    get_random_question,
)

questions_bp = Blueprint("questions", __name__)


@questions_bp.route("/get_question", methods=["GET"])
def handle_get_question():
    if not session.get("seen_question_ids"):
        fixed_question = get_fixed_question()
        session.setdefault("seen_question_ids", []).append(fixed_question["id"])
        return jsonify(fixed_question)

    categories = (
        request.args.get("categories", "").split(",")
        if request.args.get("categories")
        else None
    )
    question = get_random_question(categories)
    return question or json_error("No questions available", 404)


@questions_bp.route("/get_all_questions", methods=["GET"])
def handle_get_all_questions():
    return jsonify(get_all_questions())


@questions_bp.route("/select_question", methods=["POST"])
def handle_select_question():
    if not request.is_json:
        return json_error("Content-Type must be application/json", 400)

    question_id = request.json.get("question_id", "").strip()
    if not question_id:
        return json_error("Question ID is required", 400)

    question = find_question_by_id(question_id)
    if not question:
        return json_error("Question not found", 404)

    session.setdefault("seen_question_ids", []).append(question["id"])
    return jsonify(question)
