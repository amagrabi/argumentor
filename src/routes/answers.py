import logging
from datetime import UTC, datetime, time
from difflib import SequenceMatcher

from flask import Blueprint, jsonify, request, session

from config import get_settings
from extensions import db, limiter
from models import Answer, User
from services.leveling import get_level, get_level_info
from services.question_service import get_questions

logger = logging.getLogger(__name__)

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
    data = request.get_json() or {}
    user_uuid = session.get("user_id")
    logger.debug(
        f"Received answer submission from user: {user_uuid}, data keys: {list(data.keys())}"
    )

    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 400

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

    # Determine XP and overall rating for the main answer
    scores = evaluation["scores"]
    all_keys = [
        "Relevance",
        "Logical Structure",
        "Clarity",
        "Depth",
        "Objectivity",
        "Creativity",
    ]
    avg_all = sum(scores[key] for key in all_keys) / len(all_keys)
    xp_earned = (
        round(avg_all * 10) if avg_all >= SETTINGS.RELEVANCE_THRESHOLD_FOR_XP else 0
    )
    logger.debug(f"Raw main average: {avg_all}, XP earned: {xp_earned}")

    xp_message = ""
    if scores["Relevance"] < SETTINGS.RELEVANCE_THRESHOLD_FOR_XP:
        xp_message = (
            "Your response did not meet the minimum relevance required to earn XP."
        )

    user = User.query.filter_by(uuid=user_uuid).first()
    old_xp = user.xp if user else 0

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
        user = User(uuid=user_uuid, xp=old_xp)
        db.session.add(user)
    else:
        user.xp = old_xp

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
            "Overall": avg_all,
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

    # Recalculate the user's total XP from all of their answers.
    user = User.query.filter_by(uuid=user_uuid).first()
    total_xp = recalc_user_xp(user)
    user.xp = total_xp
    session["xp"] = total_xp
    db.session.commit()

    old_level = get_level(old_xp)
    new_level = get_level(total_xp)
    leveled_up = old_level != new_level
    level_info = get_level_info(total_xp)

    logger.info(
        f"Answer processed for user: {user_uuid} for question: {data.get('question_id')}"
    )

    return jsonify(
        {
            "evaluation": evaluation,
            "xp_gained": xp_earned,
            "current_xp": total_xp,
            "leveled_up": leveled_up,
            "current_level": level_info["display_name"],
            "level_info": level_info,
            "answer_id": new_answer.id,
            "xp_message": xp_message,
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

    daily_count = get_daily_evaluation_count(user_uuid)
    if daily_count >= SETTINGS.EVAL_DAILY_LIMIT:
        return jsonify(
            {"error": f"Daily evaluation limit reached ({SETTINGS.EVAL_DAILY_LIMIT})."}
        ), 429

    evaluator = create_evaluator()
    evaluation = evaluator.evaluate_challenge(answer, challenge_response)

    scores = evaluation["scores"]
    all_keys = [
        "Relevance",
        "Logical Structure",
        "Clarity",
        "Depth",
        "Objectivity",
        "Creativity",
    ]
    avg_all = sum(scores[key] for key in all_keys) / len(all_keys)
    # Only award XP if the overall average meets the threshold.
    xp_gained = (
        round(avg_all * 10) if avg_all >= SETTINGS.RELEVANCE_THRESHOLD_FOR_XP else 0
    )
    logger.info(f"Challenge average: {avg_all}, XP gained: {xp_gained}")

    # Update the answer with the new challenge response and XP.
    answer.challenge_response = challenge_response
    answer.challenge_evaluation_scores = {**evaluation["scores"], "Overall": avg_all}
    answer.challenge_evaluation_feedback = {
        **evaluation["feedback"],
        "Overall": evaluation["overall_feedback"],
    }
    answer.challenge_xp_earned = xp_gained

    db.session.commit()

    user = User.query.filter_by(uuid=user_uuid).first()
    new_total = recalc_user_xp(user)
    user.xp = new_total
    session["xp"] = new_total
    db.session.commit()

    leveled_up = get_level(recalc_user_xp(user) - xp_gained) != get_level(new_total)
    level_info = get_level_info(new_total)

    return jsonify(
        {
            "evaluation": evaluation,
            "challenge_xp_earned": xp_gained,
            "current_xp": new_total,
            "current_level": level_info["display_name"],
            "leveled_up": leveled_up,
            "level_info": level_info,
            "xp_message": "Your challenge response did not meet the minimum relevance required to earn XP."
            if scores["Relevance"] < SETTINGS.RELEVANCE_THRESHOLD_FOR_XP
            else "",
        }
    )


def recalc_user_xp(user):
    answers = Answer.query.filter_by(user_uuid=user.uuid).all()
    total_xp = 0

    for answer in answers:
        # Check main answer relevance
        if (
            answer.evaluation_scores.get("Relevance", 0)
            >= SETTINGS.RELEVANCE_THRESHOLD_FOR_XP
        ):
            total_xp += answer.xp_earned

        # Check challenge response relevance if it exists
        if (
            answer.challenge_response
            and answer.challenge_evaluation_scores.get("Relevance", 0)
            >= SETTINGS.RELEVANCE_THRESHOLD_FOR_XP
        ):
            total_xp += answer.challenge_xp_earned

    return total_xp
