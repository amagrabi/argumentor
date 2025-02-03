import os
import random
import uuid
from datetime import datetime

import yaml
from flask import Flask, jsonify, render_template, request, session

app = Flask(__name__)
app.secret_key = "your-secret-key-here"


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


def evaluate_answer(answer):
    """
    Evaluate user's answer. In production, this would call an actual LLM API.
    For now, it provides placeholder scoring and feedback.
    """
    scores = {
        "Logical Structure": random.randint(6, 9),
        "Clarity": random.randint(6, 9),
        "Depth": random.randint(6, 9),
        "Objectivity": random.randint(6, 9),
        "Creativity": random.randint(6, 9),
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
    # Initialize the session if it's a new visit.
    if "user_id" not in session:
        session["user_id"] = str(uuid.uuid4())
        session["points"] = 0
        session["answers"] = []
        session["seen_question_ids"] = []
    return render_template("index.html")


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
    points_earned = int(evaluation["total_score"] * 10)
    session["points"] = session.get("points", 0) + points_earned

    session["answers"].append(
        {
            "timestamp": datetime.now().isoformat(),
            "answer": answer,
            "evaluation": evaluation,
            "points_earned": points_earned,
        }
    )

    return jsonify(
        {
            "evaluation": evaluation,
            "points_earned": points_earned,
            "total_points": session["points"],
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


if __name__ == "__main__":
    app.run(debug=True)
