import json
import os
import random
import re
import uuid
from datetime import UTC, datetime

import yaml
from flask import Flask, jsonify, render_template, request, session
from google import genai
from google.genai import types
from google.oauth2 import service_account

from config import get_settings
from models import Answer, User, Visit, db

SETTINGS = get_settings()
CREDENTIALS = service_account.Credentials.from_service_account_file(
    SETTINGS.GOOGLE_APPLICATION_CREDENTIALS,
    scopes=["https://www.googleapis.com/auth/cloud-platform"],
)

app = Flask(__name__)
app.config.from_mapping(SETTINGS)

# Initialize the database with the app
db.init_app(app)

# Create tables if they don't exist
with app.app_context():
    db.create_all()

LEVEL_DEFINITIONS = [
    (0, "Curious Mind"),
    (50, "Socratic Apprentice"),
    (150, "Cognitive Cartographer"),
    (300, "Argument Architect"),
    (500, "Epistemic Engineer"),
    (750, "Debate Ninja"),
    (1000, "Thought Tactician"),
    (1500, "Dialectical Strategist"),
    (2000, "Rational Maestro"),
    (3000, "Grandmaster of Reason"),
    (5000, "Legendary Logician"),
]


# Helper function to slugify category names.
def slugify(s: str) -> str:
    # Convert to lowercase, replace any sequence of non-alphanumeric characters with a hyphen,
    # and strip hyphens from the beginning and end.
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


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
                    "id": f"{slugify(category)}-{i}",
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


def evaluate_answer(question_text, claim, argument, counterargument):
    """
    Evaluate the answer using either LLM or dummy evaluator based on settings
    """
    if SETTINGS.USE_LLM_EVALUATOR:
        return evaluate_answer_llm(question_text, claim, argument, counterargument)
    else:
        return evaluate_answer_dummy(claim, argument, counterargument)


def evaluate_answer_dummy(claim, argument, counterargument):
    """
    Dummy evaluation with random scores
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

    if total_score >= 8:
        overall_feedback = (
            "Excellent work! Your argument is well-structured and communicated clearly."
        )
    elif total_score >= 6:
        overall_feedback = (
            "Good effort! There is room for improvement in clarity and depth."
        )
    else:
        overall_feedback = "Your response shows potential but needs significant refinement in its reasoning."

    return {
        "scores": scores,
        "total_score": total_score,
        "feedback": feedback,
        "overall_feedback": overall_feedback,
    }


def evaluate_answer_llm(question_text, claim, argument, counterargument):
    """
    Evaluate the answer using Gemini LLM
    """
    client = genai.Client(
        vertexai=True,
        credentials=CREDENTIALS,
        project=SETTINGS.GCLOUD_PROJECT_NAME,
        location=SETTINGS.GCLOUD_PROJECT_REGION,
    )

    prompt = f"""
        Question: {question_text}
        Claim: {claim}
        Argument: {argument}
        Counterargument Rebuttal (Optional): {counterargument}
    """

    response = client.models.generate_content(
        model="gemini-exp-1206",
        contents=[
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=prompt)],
            ),
        ],
        config=types.GenerateContentConfig(
            temperature=0,  # default: 2
            top_p=0,  # default: 0.95
            top_k=1,
            max_output_tokens=8192,
            response_modalities=["TEXT"],
            safety_settings=[
                types.SafetySetting(
                    category="HARM_CATEGORY_HATE_SPEECH", threshold="OFF"
                ),
                types.SafetySetting(
                    category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="OFF"
                ),
                types.SafetySetting(
                    category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="OFF"
                ),
                types.SafetySetting(
                    category="HARM_CATEGORY_HARASSMENT", threshold="OFF"
                ),
            ],
            response_mime_type="application/json",
            response_schema={
                "type": "OBJECT",
                "properties": {
                    "overall_explanation": {"type": "STRING", "nullable": False},
                    "overall_rating": {
                        "type": "INTEGER",
                        "minimum": 1,
                        "maximum": 10,
                        "nullable": False,
                    },
                    "clarity_explanation": {"type": "STRING", "nullable": False},
                    "clarity_rating": {
                        "type": "INTEGER",
                        "minimum": 1,
                        "maximum": 10,
                        "nullable": False,
                    },
                    "logical_structure_explanation": {
                        "type": "STRING",
                        "nullable": False,
                    },
                    "logical_structure_rating": {
                        "type": "INTEGER",
                        "minimum": 1,
                        "maximum": 10,
                        "nullable": False,
                    },
                    "depth_explanation": {"type": "STRING", "nullable": False},
                    "depth_rating": {
                        "type": "INTEGER",
                        "minimum": 1,
                        "maximum": 10,
                        "nullable": False,
                    },
                    "objectivity_explanation": {"type": "STRING", "nullable": False},
                    "objectivity_rating": {
                        "type": "INTEGER",
                        "minimum": 1,
                        "maximum": 10,
                        "nullable": False,
                    },
                    "creativity_explanation": {"type": "STRING", "nullable": False},
                    "creativity_rating": {
                        "type": "INTEGER",
                        "minimum": 1,
                        "maximum": 10,
                        "nullable": False,
                    },
                },
                "required": [
                    "overall_explanation",
                    "overall_rating",
                    "clarity_explanation",
                    "clarity_rating",
                    "logical_structure_explanation",
                    "logical_structure_rating",
                    "depth_explanation",
                    "depth_rating",
                    "objectivity_explanation",
                    "objectivity_rating",
                    "creativity_explanation",
                    "creativity_rating",
                ],
            },
            system_instruction=[
                types.Part.from_text(
                    text="""You are an argument evaluation system. Arguments always start with a claim and then the reasoning to support the claim.
                    In the end there might be a section for counterargument rebuttal, but that is optional. Evaluate the argument overall as well as in terms
                    of the factors clarity, logical structure, depth, objectivity, creativity. Rate from a scale of 1 to 10
                    and give explanations for each score. Make sure you evaluate arguments rationally.
                    Claims could potentially be unpopular or sound strange/radical, but if an argument is well-constructed,
                    it should get a high rating regardless. Return ALL fields in the required JSON format.
                    Never omit any rating or explanation fields. Use the exact field names from the schema."""
                )
            ],
        ),
    )

    return parse_llm_response(json.loads(response.text))


def parse_llm_response(response):
    """
    Convert LLM response format to our evaluation format
    """
    return {
        "scores": {
            "Logical Structure": response["logical_structure_rating"],
            "Clarity": response["clarity_rating"],
            "Depth": response["depth_rating"],
            "Objectivity": response["objectivity_rating"],
            "Creativity": response["creativity_rating"],
        },
        "total_score": response["overall_rating"],
        "feedback": {
            "Logical Structure": response["logical_structure_explanation"],
            "Clarity": response["clarity_explanation"],
            "Depth": response["depth_explanation"],
            "Objectivity": response["objectivity_explanation"],
            "Creativity": response["creativity_explanation"],
        },
        "overall_feedback": response["overall_explanation"],
    }


@app.route("/")
def home():
    if "user_id" not in session:
        session["user_id"] = str(uuid.uuid4())
    user = User.query.filter_by(uuid=session["user_id"]).first()
    if not user:
        user = User(uuid=session["user_id"], xp=0)
        db.session.add(user)
        db.session.commit()
    xp = user.xp
    level_info = get_level_info(xp)

    # Load and select the bias of the day from the YAML file
    biases_path = os.path.join(app.root_path, "data", "cognitive_biases.yaml")
    with open(biases_path, "r") as f:
        biases_data = yaml.safe_load(f)
    biases = biases_data.get("cognitive_biases", [])
    if biases:
        day_of_year = datetime.now().timetuple().tm_yday
        bias_index = day_of_year % len(biases)
        bias = biases[bias_index]
    else:
        bias = {"name": "N/A", "description": "", "example": ""}

    return render_template("index.html", xp=xp, level_info=level_info, bias=bias)


@app.route("/how_it_works")
def how_it_works():
    criteria_path = os.path.join(app.root_path, "data", "evaluation_criteria.yaml")
    with open(criteria_path, "r") as f:
        criteria = yaml.safe_load(f)
    return render_template("how_it_works.html", criteria=criteria)


@app.route("/get_question", methods=["GET"])
def get_question():
    # If no questions have been shown yet in this session, return the fixed starting question.
    if not session.get("seen_question_ids"):
        fixed_question = {
            "id": "philosophy-0",
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
    question_text = data.get("question_text", "").strip()
    claim = data.get("claim", "").strip()
    argument = data.get("argument", "").strip()
    counterargument = (data.get("counterargument", "") or "").strip()

    if not claim or not argument:
        return jsonify({"error": "Both claim and argument are required"}), 400

    if (
        len(claim) > 150
        or len(argument) > 1000
        or (counterargument and len(counterargument) > 500)
    ):
        return jsonify({"error": "Character limit exceeded"}), 400

    evaluation = evaluate_answer(question_text, claim, argument, counterargument)
    xp_gained = sum(evaluation["scores"].values())

    old_xp = session.get("xp", 0)
    new_xp = old_xp + xp_gained
    session["xp"] = new_xp

    user_uuid = session.get("user_id")
    user = User.query.filter_by(uuid=user_uuid).first()
    if not user:
        user = User(uuid=user_uuid, xp=new_xp)
        db.session.add(user)
    else:
        user.xp = new_xp

    # Get question_id from the request and look up the question text.
    question_id = data.get("question_id")
    question_text = ""
    if question_id:
        # search through loaded QUESTIONS to find the matching question description
        for questions in QUESTIONS.values():
            for q in questions:
                if q["id"] == question_id:
                    question_text = q["description"]
                    break
            if question_text:
                break

    new_answer = Answer(
        user_uuid=user_uuid,
        question_id=question_id,
        question_text=question_text,
        claim=claim,
        argument=argument,
        counterargument=counterargument if counterargument else None,
        evaluation_scores=evaluation["scores"],
        evaluation_feedback=evaluation["feedback"],
        xp_earned=xp_gained,
    )
    db.session.add(new_answer)
    db.session.commit()

    old_level = get_level(old_xp)
    new_level = get_level(new_xp)
    leveled_up = old_level != new_level

    level_info = get_level_info(new_xp)

    return jsonify(
        {
            "evaluation": evaluation,
            "xp_earned": xp_gained,
            "total_xp": new_xp,
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
    user_uuid = session.get("user_id")
    user = User.query.filter_by(uuid=user_uuid).first()
    xp = user.xp if user else 0
    level_info = get_level_info(xp)
    return render_template("profile.html", xp=xp, level_info=level_info, user=user)


@app.route("/get_new_question", methods=["GET"])
def get_new_question():
    categories_param = request.args.get("categories", "")
    categories = categories_param.split(",") if categories_param else None
    question = get_random_question(categories)
    if question is None:
        return jsonify({"error": "No questions available"}), 404
    return jsonify(question)


@app.route("/cognitive_bias_day")
def cognitive_bias_day():
    import os
    from datetime import datetime

    import yaml

    # Load the cognitive biases from the YAML file
    data_path = os.path.join(app.root_path, "data", "cognitive_biases.yaml")
    with open(data_path, "r") as f:
        biases_data = yaml.safe_load(f)
    biases = biases_data.get("cognitive_biases", [])
    if not biases:
        return "No cognitive biases available.", 404
    # Select a bias of the day deterministically based on the current day.
    day_of_year = datetime.now().timetuple().tm_yday
    index = day_of_year % len(biases)
    bias_of_the_day = biases[index]
    return render_template(
        "cognitive_bias_day.html", bias=bias_of_the_day, biases=biases
    )


@app.route("/reasoning_guide")
def reasoning_guide():
    data_path = os.path.join(app.root_path, "data", "cognitive_biases.yaml")
    with open(data_path, "r") as f:
        biases_data = yaml.safe_load(f)
    biases = biases_data.get("cognitive_biases", [])
    return render_template("reasoning_guide.html", biases=biases)


@app.route("/support")
def support():
    return render_template("support.html")


@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


@app.cli.command("recreate_db")
def recreate_db():
    """Drop and recreate the database."""
    from models import db

    with app.app_context():
        db.drop_all()
        db.create_all()
    print("Database recreated!")


@app.before_request
def ensure_user_id():
    if "user_id" not in session:
        session["user_id"] = str(uuid.uuid4())


@app.before_request
def log_visit():
    if request.endpoint and request.endpoint != "static":
        today_str = datetime.now(UTC).strftime("%Y-%m-%d")
        if session.get("last_visit_date") != today_str:
            session["last_visit_date"] = today_str
            ip_address = request.remote_addr
            user_agent = request.headers.get("User-Agent")
            user_uuid = session.get("user_id")
            new_visit = Visit(
                ip_address=ip_address, user_agent=user_agent, user_uuid=user_uuid
            )
            db.session.add(new_visit)
            db.session.commit()


if __name__ == "__main__":
    app.run(debug=True)
