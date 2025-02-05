from difflib import SequenceMatcher

from flask import Blueprint, jsonify, request, session

from config import get_settings
from extensions import db
from models import Answer, User
from services.leveling import get_level, get_level_info
from services.question_service import get_questions

answers_bp = Blueprint("answers", __name__)


SETTINGS = get_settings()


def create_evaluator():
    if SETTINGS.USE_LLM_EVALUATOR:
        from services.evaluator import LLMEvaluator
        from services.llm import CLIENT, RESPONSE_SCHEMA, SYSTEM_INSTRUCTION

        return LLMEvaluator(CLIENT, SYSTEM_INSTRUCTION, RESPONSE_SCHEMA)
    else:
        from services.evaluator import DummyEvaluator

        return DummyEvaluator()


def evaluate_answer(question_text, claim, argument, counterargument):
    """
    Evaluate the answer using the configured evaluator
    """
    evaluator = create_evaluator()
    return evaluator.evaluate(question_text, claim, argument, counterargument)


@answers_bp.route("/submit_answer", methods=["POST"])
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
        len(claim) > 200
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
    existing_answers = Answer.query.filter_by(
        user_uuid=user_uuid, question_id=data.get("question_id")
    ).all()

    SIMILARITY_THRESHOLD = 0.8  # 80% similarity

    for existing in existing_answers:
        # Compare both claim and argument
        claim_similarity = SequenceMatcher(None, claim, existing.claim).ratio()
        argument_similarity = SequenceMatcher(None, argument, existing.argument).ratio()

        if (
            claim_similarity > SIMILARITY_THRESHOLD
            and argument_similarity > SIMILARITY_THRESHOLD
        ):
            return jsonify(
                {
                    "error": """
                        You already submitted a very similar answer to this question.
                        Change your argument to receive a new evaluation.
                    """
                }
            ), 400
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
        # First check if it's the fixed question
        if (
            question_id
            == "does-free-will-exist-if-all-decisions-are-ultimately-influenced-by-biologicalphysical-factors"
        ):
            question_text = "Does free will exist if all decisions are ultimately influenced by biological/physical factors?"
        else:
            # search through loaded QUESTIONS
            for questions in get_questions().values():
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
        evaluation_scores={
            **evaluation["scores"],
            "Overall": evaluation["total_score"],
        },
        evaluation_feedback={
            **evaluation["feedback"],  # Changed from data["evaluation"]
            "Overall": evaluation["overall_feedback"],
        },
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
