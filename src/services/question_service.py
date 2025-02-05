import re
from pathlib import Path
from random import choice

import yaml
from flask import current_app, session

_questions = None  # Cache for loaded questions


def load_questions():
    global _questions
    if _questions is None:
        questions_path = Path(current_app.root_path) / "data" / "questions.yaml"
        with open(questions_path, "r") as f:
            raw_data = yaml.safe_load(f)

            def slugify(s: str) -> str:
                return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")

            _questions = {
                category: [
                    {
                        "id": slugify(text),
                        "description": text,
                        "category": category,
                    }
                    for text in questions  # Remove enumerate since we don't need index
                ]
                for category, questions in raw_data.items()
            }
    return _questions


def get_questions():
    if not current_app:
        with current_app.app_context():
            return load_questions()
    return load_questions()


def get_fixed_question():
    return {
        "id": "philosophy-0",
        "description": "Does free will exist if all decisions are ultimately influenced by biological/physical factors?",
        "category": "Philosophy",
    }


def get_random_question(categories=None):
    filtered = []
    all_questions = get_questions()
    for category, questions in all_questions.items():
        if not categories or category in categories:
            filtered.extend(
                [
                    q
                    for q in questions
                    if q["id"] not in session.get("seen_question_ids", [])
                ]
            )
    return choice(filtered) if filtered else None


def get_all_questions():
    return [q for category in get_questions().values() for q in category]


def find_question_by_id(question_id):
    questions = get_questions()
    for questions in questions.values():
        for q in questions:
            if q["id"] == question_id:
                return q
    return None
