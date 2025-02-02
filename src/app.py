import random
import uuid
from datetime import datetime

from flask import Flask, jsonify, render_template, request, session

app = Flask(__name__)
app.secret_key = "your-secret-key-here"

# Database of questions with full descriptions
QUESTIONS = {
    "Philosophy": [
        {
            "description": "Is free will an illusion?",
            "category": "Philosophy",
        },
        {
            "description": "Is time travel possible?",
            "category": "Philosophy",
        },
        {
            "description": "Is reality subjective or objective?",
            "category": "Philosophy",
        },
        {
            "description": "Are we living in a simulation?",
            "category": "Philosophy",
        },
        {
            "description": "Is there a meaning of life?",
            "category": "Philosophy",
        },
        {
            "description": "Can the universe be infinite or must it have a boundary?",
            "category": "Philosophy",
        },
        {
            "description": "Is there life after death?",
            "category": "Philosophy",
        },
        {
            "description": "Is capitalism the best available system to maximize human prosperity?",
            "category": "Philosophy",
        },
    ],
    "Ethics": [
        {
            "description": "Is it ever justifiable to break the law for the greater good?",
            "category": "Ethics",
        },
        {
            "description": 'If no one gets hurt, is anything truly "wrong"?',
            "category": "Ethics",
        },
    ],
    "Business & Risk": [
        {
            "description": "Should a company invest in risky innovation or focus on stable revenue streams?",
            "category": "Business & Risk",
        },
        {
            "description": "Is it better to diversify investments or concentrate on areas of expertise?",
            "category": "Business & Risk",
        },
        {
            "description": "Should companies prioritize short-term profits or long-term sustainability?",
            "category": "Business & Risk",
        },
        {
            "description": "Is it worth taking on debt to expand a successful business?",
            "category": "Business & Risk",
        },
    ],
    "Thought Experiments": [
        {
            "description": "You're given a button that grants you $1 million, but it causes an unknown person to die. Do you press it?",
            "category": "Thought Experiments",
        },
        {
            "description": "If you could erase one invention from history, what would it be?",
            "category": "Thought Experiments",
        },
    ],
    "Politics": [
        {
            "description": "Should governments implement universal basic income?",
            "category": "Politics",
        },
        {
            "description": "Should all votes in a democracy count equally?",
            "category": "Politics",
        },
    ],
    "Biases & Fallacies": [
        {
            "description": "A new cancer drug shows a 90% survival rate in trials, but some experts doubt its effectiveness. Should it be approved?",
            "category": "Biases & Fallacies",
        },
        {
            "description": "A study finds that people who drink coffee live longer. Should the World Health Organization therefore publish a recommendation to drink coffee?",
            "category": "Biases & Fallacies",
        },
    ],
    "AI & Future": [
        {
            "description": "Could a machine ever experience emotions like humans?",
            "category": "AI & Future",
        },
        {
            "description": "Should the progress of AI be regulated?",
            "category": "AI & Future",
        },
        {
            "description": "Should intelligent AIs ever have rights?",
            "category": "AI & Future",
        },
        {
            "description": "Could intelligent AIs be creative?",
            "category": "AI & Future",
        },
        {
            "description": "Should self-driving cars prioritize passengers or pedestrians in an unavoidable crash?",
            "category": "Ethics",
        },
    ],
    "Fun & Casual": [
        {
            "description": "Apples or oranges?",
            "category": "Fun & Casual",
        },
        {
            "description": "Who would win in a fight, a Grizzly bear or a gorilla?",
            "category": "Fun & Casual",
        },
        {
            "description": "Is a hotdog a sandwich?",
            "category": "Fun & Casual",
        },
    ],
}


def get_random_question(categories=None):
    """Get a random question from selected categories."""
    if not categories:
        categories = list(QUESTIONS.keys())

    # Get all questions from selected categories
    available_questions = []
    for category in categories:
        if category in QUESTIONS:
            available_questions.extend(QUESTIONS[category])

    if not available_questions:
        return None

    return random.choice(available_questions)


def evaluate_answer(answer):
    """
    Evaluate user's answer. In production, this would call an actual LLM API.
    For now, it provides placeholder scoring and feedback.
    """
    # Placeholder scoring logic
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
    if "user_id" not in session:
        session["user_id"] = str(uuid.uuid4())
        session["points"] = 0
        session["answers"] = []
    return render_template("index.html")


@app.route("/get_question", methods=["POST"])
def get_question():
    data = request.json
    categories = data.get("categories", list(QUESTIONS.keys()))
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

    # Evaluate answer
    evaluation = evaluate_answer(answer)

    # Update user points
    points_earned = int(evaluation["total_score"] * 10)
    session["points"] = session.get("points", 0) + points_earned

    # Store answer history
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


if __name__ == "__main__":
    app.run(debug=True)
