import json
from pathlib import Path
from random import choice

from flask import current_app, session
from flask_login import current_user

from config import get_settings
from models import Answer
from src.constants.categories import DEFAULT_CATEGORIES

SETTINGS = get_settings()
_questions_cache = None


def load_questions():
    global _questions_cache
    language = session.get("language", "en")

    # Ensure we're using a supported language
    if language not in SETTINGS.SUPPORTED_LANGUAGES:
        session["language"] = SETTINGS.DEFAULT_LANGUAGE

    # Always reload questions when language changes
    translations_path = (
        Path(current_app.root_path) / "static" / "translations" / f"{language}.json"
    )

    with open(translations_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        questions_data = data.get("questions", {})

        # Transform the data into the format expected by the application
        _questions_cache = {
            category: [
                {
                    "id": question_id,
                    "description": question_text,
                    "category": category,
                }
                for question_id, question_text in questions_data.get(
                    category, {}
                ).items()
            ]
            for category in DEFAULT_CATEGORIES
        }

    return _questions_cache


def get_questions():
    if not current_app:
        with current_app.app_context():
            return load_questions()
    return load_questions()


def get_fixed_question():
    """Get the experiences vs possessions question from Personal Growth category"""
    questions = get_questions()
    personal_growth_questions = questions.get("Personal Growth & Relationships", [])
    for question in personal_growth_questions:
        if question["id"] == SETTINGS.DEFAULT_QUESTION:
            return question
    return None


def get_random_question(categories=None):
    filtered = []
    all_questions = get_questions()
    seen_question_ids = session.get("seen_question_ids", [])

    # Get list of answered question IDs for the current user
    answered_question_ids = []
    if current_user and current_user.is_authenticated:
        # Query the database for questions this user has already answered
        answers = Answer.query.filter_by(user_uuid=current_user.uuid).all()
        answered_question_ids = [
            answer.question_id for answer in answers if answer.question_id
        ]
    elif "user_id" in session:
        # For non-authenticated users with a session user_id
        answers = Answer.query.filter_by(user_uuid=session["user_id"]).all()
        answered_question_ids = [
            answer.question_id for answer in answers if answer.question_id
        ]

    # First try: filter out both seen and answered questions
    for category, questions in all_questions.items():
        if not categories or category in categories:
            filtered.extend(
                [
                    q
                    for q in questions
                    if q["id"] not in seen_question_ids
                    and q["id"] not in answered_question_ids
                ]
            )

    # If no questions left, try showing seen but not answered questions
    if not filtered:
        for category, questions in all_questions.items():
            if not categories or category in categories:
                filtered.extend(
                    [q for q in questions if q["id"] not in answered_question_ids]
                )

    # If still no questions, show all questions (including answered ones)
    if not filtered:
        for category, questions in all_questions.items():
            if not categories or category in categories:
                filtered.extend(questions)

    # Add the chosen question to seen_question_ids
    if filtered:
        chosen = choice(filtered)
        session.setdefault("seen_question_ids", []).append(chosen["id"])
        return chosen

    return None


def get_all_questions():
    return [q for category in get_questions().values() for q in category]


def find_question_by_id(question_id):
    questions = get_questions()
    for questions in questions.values():
        for q in questions:
            if q["id"] == question_id:
                return q
    return None
