import os
import random
import uuid
from datetime import datetime

import yaml
from flask import Flask, jsonify, render_template, request, session

app = Flask(__name__)
app.secret_key = "your-secret-key-here"

LEVEL_DEFINITIONS = [
    (0, "Novice Thinker"),
    (50, "Curious Mind"),
    (150, "Inquisitive Brain"),
    (300, "Critical Debater"),
    (600, "Rational Maestro"),
    (1000, "ArguMentor Grandmaster"),
]


def load_questions():
    base_dir = os.path.dirname(__file__)
    data_path = os.path.join(base_dir, "data", "questions.yaml")
    with open(data_path, "r") as f:
        questions_by_category = yaml.safe_load(f)
    # Assign a unique id and the category to each question.
    for category, questions in questions_by_category.items():
        new_questions = []
        for i, q in enumerate(questions):
            new_questions.append(
                {
                    "id": f"{category}-{i}",
                    "description": q,
                    "category": category,
                }
            )
        questions_by_category[category] = new_questions
    return questions_by_category


QUESTIONS = load_questions()


def get_random_question(categories=None):
    """Get a random question from selected categories, avoiding repeats until all have been seen."""
    if not categories:
        categories = list(QUESTIONS.keys())
    candidate_questions = []
    for category in categories:
        if category in QUESTIONS:
            candidate_questions.extend(QUESTIONS[category])
    seen_ids = session.get("seen_question_ids", [])
    # Filter out questions that have already been shown.
    unseen_questions = [q for q in candidate_questions if q["id"] not in seen_ids]
    # If all questions in these categories were already shown, reset the seen list for them.
    if not unseen_questions:
        seen_ids = [
            qid
            for qid in seen_ids
            if not any(qid.startswith(f"{cat}-") for cat in categories)
        ]
        session["seen_question_ids"] = seen_ids
        unseen_questions = candidate_questions
    chosen_question = random.choice(unseen_questions)
    # Mark the chosen question as seen.
    session.setdefault("seen_question_ids", []).append(chosen_question["id"])
    return chosen_question


def get_level(xp):
    current_level = LEVEL_DEFINITIONS[0][1]
    for threshold, name in LEVEL_DEFINITIONS:
        if xp >= threshold:
            current_level = name
        else:
            break
    return current_level


def get_level_info(xp):
    level_definitions = LEVEL_DEFINITIONS
    current_level = level_definitions[0]
    level_number = 1
    for i, (threshold, label) in enumerate(level_definitions):
        if xp >= threshold:
            current_level = (threshold, label)
            level_number = i + 1
        else:
            break
    current_threshold = current_level[0]
    next_threshold = (
        level_definitions[level_number][0]
        if level_number < len(level_definitions)
        else None
    )
    xp_into_level = xp - current_threshold
    xp_needed = next_threshold - current_threshold if next_threshold is not None else 0
    progress_percent = (
        (xp_into_level / xp_needed) * 100 if next_threshold and xp_needed > 0 else 100
    )
    display_name = f"Level {level_number} ({current_level[1]})"
    if level_number < len(level_definitions):
        next_level_display = (
            f"Level {level_number + 1} ({level_definitions[level_number][1]})"
        )
    else:
        next_level_display = "Max Level"
    return {
        "level_number": level_number,
        "level_label": current_level[1],
        "display_name": display_name,
        "current_threshold": current_threshold,
        "next_threshold": next_threshold,
        "xp_into_level": xp_into_level,
        "xp_needed": xp_needed,
        "progress_percent": progress_percent,
        "next_level": next_level_display,
    }


def evaluate_answer(answer):
    """
    Evaluate user's answer. In production, this would call an actual LLM API.
    For now, it provides placeholder scoring and feedback.
    """
    scores = {
        "Logical Structure": random.randint(1, 10),
        "Clarity": random.randint(1, 10),
        "Depth": random.randint(1, 10),
        "Objectivity": random.randint(1, 10),
        "Creativity": random.randint(1, 10),
    }
    total_score = sum(scores.values()) / len(scores)
    feedback = {
        "Logical Structure": "Your argument structure shows good coherence. Consider strengthening the connection between premises and conclusion.",
        "Clarity": "Your points are clearly expressed. Try to be even more concise in future responses.",
        "Depth": "Good analysis of key factors. Consider exploring additional philosophical implications.",
        "Objectivity": "Well-balanced perspective. Watch for potential emotional appeals.",
        "Creativity": "Interesting approach to the problem. Consider exploring even more unconventional angles.",
    }
    return {"scores": scores, "total_score": total_score, "feedback": feedback}


@app.route("/")
def home():
    if "user_id" not in session:
        session["user_id"] = str(uuid.uuid4())
        session["points"] = 0
        session["xp"] = 0  # Initialize XP
        session["answers"] = []
        session["seen_question_ids"] = []
    xp = session.get("xp", 0)
    level_info = get_level_info(xp)
    return render_template("index.html", xp=xp, level_info=level_info)


@app.route("/get_question", methods=["GET"])
def get_question():
    # If no questions have been shown yet in this session, return the fixed starting question.
    if not session.get("seen_question_ids"):
        fixed_question = {
            "id": "Philosophy-0",
            "description": "Does free will exist if all decisions are ultimately influenced by biological/physical factors?",
            "category": "Philosophy",
        }
        session.setdefault("seen_question_ids", []).append(fixed_question["id"])
        return jsonify(fixed_question)

    categories_param = request.args.get("categories", "")
    categories = categories_param.split(",") if categories_param else None
    question = get_random_question(categories)
    if question is None:
        return jsonify({"error": "No questions available"}), 404
    return jsonify(question)


@app.route("/submit_answer", methods=["POST"])
def submit_answer():
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 400

    data = request.json
    answer = data.get("answer", "").strip()

    if not answer:
        return jsonify({"error": "Answer cannot be empty"}), 400

    if len(answer) > 200:
        return jsonify({"error": "Answer exceeds maximum length"}), 400

    evaluation = evaluate_answer(answer)
    # Use the sum of the individual rating scores for XP
    xp_gained = sum(evaluation["scores"].values())

    old_xp = session.get("xp", 0)
    new_xp = old_xp + xp_gained
    session["xp"] = new_xp

    old_level = get_level(old_xp)
    new_level = get_level(new_xp)
    leveled_up = old_level != new_level

    # Since XP and points are the same in your setup:
    session["points"] = new_xp

    session["answers"].append(
        {
            "timestamp": datetime.now().isoformat(),
            "answer": answer,
            "evaluation": evaluation,
            "points_earned": xp_gained,
        }
    )

    level_info = get_level_info(new_xp)

    return jsonify(
        {
            "evaluation": evaluation,
            "points_earned": xp_gained,
            "total_points": session["points"],
            "xp_gained": xp_gained,
            "current_xp": new_xp,
            "current_level": level_info["display_name"],
            "leveled_up": leveled_up,
            "level_info": level_info,
        }
    )


@app.route("/get_all_questions", methods=["GET"])
def get_all_questions():
    all_questions = []
    for questions in QUESTIONS.values():
        all_questions.extend(questions)
    return jsonify(all_questions)


@app.route("/select_question", methods=["POST"])
def select_question():
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 400

    data = request.json
    question_id = data.get("question_id", "").strip()
    if not question_id:
        return jsonify({"error": "Question ID is required"}), 400

    selected_question = None
    for questions in QUESTIONS.values():
        for q in questions:
            if q["id"] == question_id:
                selected_question = q
                break
        if selected_question:
            break

    if not selected_question:
        return jsonify({"error": "Question not found"}), 404

    session.setdefault("seen_question_ids", []).append(selected_question["id"])
    return jsonify(selected_question)


@app.route("/profile")
def profile():
    xp = session.get("xp", 0)
    level_info = get_level_info(xp)
    return render_template(
        "profile.html",
        points=session.get("points", 0),
        xp=xp,
        level_info=level_info,
    )


@app.route("/get_new_question", methods=["GET"])
def get_new_question():
    categories_param = request.args.get("categories", "")
    categories = categories_param.split(",") if categories_param else None
    question = get_random_question(categories)
    if question is None:
        return jsonify({"error": "No questions available"}), 404
    return jsonify(question)


@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


if __name__ == "__main__":
    app.run(debug=True)
