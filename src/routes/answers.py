from datetime import UTC, datetime, time
from difflib import SequenceMatcher

from flask import Blueprint, jsonify, request, session

from config import get_settings
from extensions import db, limiter
from models import Answer, User
from services.leveling import get_level, get_level_info
from services.question_service import get_questions

answers_bp = Blueprint("answers", __name__)


SETTINGS = get_settings()


# Helper to count today's evaluation attempts.
def get_daily_evaluation_count(user_uuid):
    """
    Returns the total number of evaluation attempts made by the user today.
    Each initial answer submission counts as 1.
    If the answer has a non-null challenge_response, that counts as an additional evaluation attempt.
    """
    today_start = datetime.combine(datetime.now(UTC).date(), time.min)
    answers = Answer.query.filter(
        Answer.user_uuid == user_uuid, Answer.created_at >= today_start
    ).all()
    count = 0
    for ans in answers:
        count += 1
        if ans.challenge_response:
            count += 1
    return count


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
@limiter.limit(
    SETTINGS.SUBMISSION_RATE_LIMITS,
    error_message="Too many submissions. Please wait before trying again.",
)
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
        len(claim) > SETTINGS.MAX_CLAIM
        or len(argument) > SETTINGS.MAX_ARGUMENT
        or (counterargument and len(counterargument) > SETTINGS.MAX_COUNTERARGUMENT)
    ):
        return jsonify({"error": "Character limit exceeded"}), 400

    # If question_text wasn't provided, try to look it up using question_id.
    question_id = data.get("question_id")
    if not question_text and question_id:
        if (
            question_id
            == "does-free-will-exist-if-all-decisions-are-ultimately-influenced-by-biologicalphysical-factors"
        ):
            question_text = "Does free will exist if all decisions are ultimately influenced by biological/physical factors?"
        else:
            for questions in get_questions().values():
                for q in questions:
                    if q["id"] == question_id:
                        question_text = q["description"]
                        break
                if question_text:
                    break

    user_uuid = session.get("user_id")
    if not user_uuid:
        return jsonify({"error": "User not identified."}), 400

    # Check today's evaluation count (initial submission counts as one)
    daily_count = get_daily_evaluation_count(user_uuid)
    if daily_count >= SETTINGS.EVAL_DAILY_LIMIT:
        return (
            jsonify(
                {
                    "error": f"Daily evaluation limit reached ({SETTINGS.EVAL_DAILY_LIMIT})."
                }
            ),
            429,
        )

    evaluator = create_evaluator()
    evaluation = evaluator.evaluate(question_text, claim, argument, counterargument)

    # Determine XP and overall rating (excluding the Relevance score)
    scores = evaluation["scores"]
    other_keys = ["Logical Structure", "Clarity", "Depth", "Objectivity", "Creativity"]
    avg_other = sum(scores[key] for key in other_keys) / len(other_keys)
    xp_earned = (
        int(avg_other * 10)
        if scores["Relevance"] >= SETTINGS.RELEVANCE_THRESHOLD_FOR_XP
        else 0
    )

    user = User.query.filter_by(uuid=user_uuid).first()
    old_xp = user.xp if user else 0
    new_xp = old_xp + xp_earned
    session["xp"] = new_xp

    existing_answers = Answer.query.filter_by(
        user_uuid=user_uuid, question_id=data.get("question_id")
    ).all()

    for existing in existing_answers:
        # Compare both claim and argument
        claim_similarity = SequenceMatcher(None, claim, existing.claim).ratio()
        argument_similarity = SequenceMatcher(None, argument, existing.argument).ratio()

        if (
            claim_similarity > SETTINGS.SIMILARITY_THRESHOLD
            and argument_similarity > SETTINGS.SIMILARITY_THRESHOLD
        ):
            return jsonify(
                {
                    "error": """
                        You already submitted a very similar answer to this question.
                        Change your argument to receive a new evaluation.
                    """
                }
            ), 400
    if not user:
        user = User(uuid=user_uuid, xp=new_xp)
        db.session.add(user)
    else:
        user.xp = new_xp

    # Get question_text from the request by looking up question_id if necessary.
    question_id = data.get("question_id")
    question_text = ""
    if question_id:
        if (
            question_id
            == "does-free-will-exist-if-all-decisions-are-ultimately-influenced-by-biologicalphysical-factors"
        ):
            question_text = "Does free will exist if all decisions are ultimately influenced by biological/physical factors?"
        else:
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
            "Overall": avg_other,
        },
        evaluation_feedback={
            **evaluation["feedback"],
            "Overall": evaluation["overall_feedback"],
        },
        xp_earned=xp_earned,
        challenge=evaluation.get("challenge"),
        challenge_evaluation_scores={},
        challenge_evaluation_feedback={},
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
            "xp_earned": xp_earned,
            "total_xp": new_xp,
            "xp_gained": xp_earned,
            "current_xp": new_xp,
            "current_level": level_info["display_name"],
            "leveled_up": leveled_up,
            "level_info": level_info,
            "answer_id": new_answer.id,
        }
    )


@answers_bp.route("/submit_challenge_response", methods=["POST"])
@limiter.limit(
    SETTINGS.SUBMISSION_RATE_LIMITS,
    error_message="Too many submissions. Please wait before trying again.",
)
def submit_challenge_response():
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 400

    data = request.json
    challenge_response = data.get("challenge_response", "").strip()
    answer_id = data.get("answer_id")

    if not challenge_response:
        return jsonify({"error": "Challenge response is required"}), 400
    if len(challenge_response) > SETTINGS.MAX_ARGUMENT:
        return jsonify({"error": "Character limit exceeded"}), 400

    answer = Answer.query.filter_by(id=answer_id).first()
    if not answer:
        return jsonify({"error": "Answer not found"}), 404
    if not answer.challenge:
        return jsonify({"error": "No challenge available for this answer"}), 400
    if answer.challenge_response:
        return jsonify(
            {"error": "You have already submitted a response to this challenge."}
        ), 400

    user_uuid = session.get("user_id")
    if not user_uuid:
        return jsonify({"error": "User not identified."}), 400

    # Check the daily evaluation count (challenge responses count as a separate evaluation attempt)
    daily_count = get_daily_evaluation_count(user_uuid)
    if daily_count >= SETTINGS.EVAL_DAILY_LIMIT:
        return (
            jsonify(
                {
                    "error": f"Daily evaluation limit reached ({SETTINGS.EVAL_DAILY_LIMIT})."
                }
            ),
            429,
        )

    evaluator = create_evaluator()
    evaluation = evaluator.evaluate_challenge(answer, challenge_response)

    scores = evaluation["scores"]
    other_keys = ["Logical Structure", "Clarity", "Depth", "Objectivity", "Creativity"]
    avg_other = sum(scores[key] for key in other_keys) / len(other_keys)
    overall_challenge_rating = avg_other
    xp_gained = (
        int(avg_other * 10)
        if scores["Relevance"] >= SETTINGS.RELEVANCE_THRESHOLD_FOR_XP
        else 0
    )

    answer.challenge_response = challenge_response
    answer.challenge_evaluation_scores = {
        **evaluation["scores"],
        "Overall": overall_challenge_rating,
    }
    answer.challenge_evaluation_feedback = {
        **evaluation["feedback"],
        "Overall": evaluation["overall_feedback"],
    }
    answer.challenge_xp_earned = xp_gained

    user = User.query.filter_by(uuid=user_uuid).first()
    old_xp = user.xp if user else 0
    new_xp = old_xp + xp_gained
    session["xp"] = new_xp

    if user:
        user.xp = new_xp
    else:
        user = User(uuid=user_uuid, xp=new_xp)
        db.session.add(user)

    db.session.commit()

    old_level = get_level(old_xp)
    new_level = get_level(new_xp)
    leveled_up = old_level != new_level
    level_info = get_level_info(new_xp)

    return jsonify(
        {
            "evaluation": evaluation,
            "challenge_xp_earned": xp_gained,
            "total_xp": new_xp,
            "current_level": level_info["display_name"],
            "leveled_up": leveled_up,
            "level_info": level_info,
        }
    )
