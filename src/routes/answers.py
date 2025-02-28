import logging
from datetime import UTC, datetime
from difflib import SequenceMatcher

from flask import Blueprint, jsonify, request, session

from config import get_settings
from extensions import db, limiter
from models import Answer, User
from services.achievement_service import check_and_award_achievements
from services.evaluator import DummyEvaluator
from services.level_service import get_level_for_xp, get_level_info, get_level_name
from services.question_service import get_questions
from utils import get_daily_evaluation_count, get_eval_limit

logger = logging.getLogger(__name__)

answers_bp = Blueprint("answers", __name__)


SETTINGS = get_settings()


def create_evaluator():
    if SETTINGS.USE_LLM_EVALUATOR:
        from services.evaluator import LLMEvaluator
        from services.llm import (
            CLIENT,
            RESPONSE_SCHEMA,
            SYSTEM_INSTRUCTION_DE,
            SYSTEM_INSTRUCTION_EN,
        )

        system_instructions = {"en": SYSTEM_INSTRUCTION_EN, "de": SYSTEM_INSTRUCTION_DE}

        return LLMEvaluator(CLIENT, system_instructions, RESPONSE_SCHEMA)
    else:
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
    error_message="tooManySubmissions",
)
def submit_answer():
    try:
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
        user = User.query.filter_by(uuid=user_uuid).first()
        eval_limit = get_eval_limit(user.tier)

        if daily_count >= eval_limit:
            error_message = f"Daily evaluation limit reached ({eval_limit}). "
            if user.tier == "anonymous":
                error_message += (
                    'Log in for higher limits <a href="#" class="underline" '
                    'onclick="showAuthModal(); return false;">here</a>.'
                )
            else:
                error_message += (
                    'If you need a higher limit, let me know in the <a href="#" class="underline" '
                    'onclick="showFeedbackModal(); return false;">feedback</a>.'
                )
            return jsonify({"error": error_message}), 429

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
            round(avg_all * 10)
            if scores["Relevance"] >= SETTINGS.RELEVANCE_THRESHOLD_FOR_XP
            else 0
        )
        logger.debug(f"Raw main average: {avg_all}, XP earned: {xp_earned}")

        # Add relevance_too_low flag to response
        relevance_too_low = scores["Relevance"] < SETTINGS.RELEVANCE_THRESHOLD_FOR_XP

        old_xp = user.xp if user else 0

        existing_answers = (
            Answer.query.filter_by(user_uuid=user.uuid)
            .order_by(Answer.created_at.desc(), Answer.id.desc())
            .all()
        )

        for existing in existing_answers:
            existing_counter = (existing.counterargument or "").strip()
            new_counter = counterargument  # Already trimmed when parsing input

            claim_similarity = SequenceMatcher(None, claim, existing.claim).ratio()
            argument_similarity = SequenceMatcher(
                None, argument, existing.argument
            ).ratio()

            if (
                claim_similarity > SETTINGS.SIMILARITY_THRESHOLD
                and argument_similarity > SETTINGS.SIMILARITY_THRESHOLD
            ):
                # Only consider the counterargument if both submissions have one.
                if bool(new_counter) == bool(existing_counter):
                    if new_counter:
                        counter_similarity = SequenceMatcher(
                            None, new_counter, existing_counter
                        ).ratio()
                        if counter_similarity > SETTINGS.SIMILARITY_THRESHOLD:
                            return jsonify({"error": "similarAnswer"}), 409
                    else:
                        # Neither submission has a counterargument.
                        return jsonify({"error": "similarAnswer"}), 409
                # If one has a counterargument and the other doesn't, we treat them as different.
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

        # Get mode from request payload
        input_mode = data.get("input_mode", "text")

        # Use consistent property name without quotes to avoid issues
        scores_dict = {**evaluation["scores"]}
        scores_dict["Overall"] = avg_all

        feedback_dict = {**evaluation["feedback"]}
        feedback_dict["Overall"] = evaluation["overall_feedback"]

        new_answer = Answer(
            user_uuid=user_uuid,
            question_id=question_id,
            question_text=question_text,
            claim=claim,
            argument=argument,
            counterargument=counterargument if counterargument else None,
            evaluation_scores=scores_dict,
            evaluation_feedback=feedback_dict,
            xp_earned=xp_earned,
            challenge=evaluation.get("challenge"),
            challenge_evaluation_scores={},
            challenge_evaluation_feedback={},
            input_mode=input_mode,
            created_at=datetime.now(UTC),
        )
        db.session.add(new_answer)
        db.session.commit()

        # Recalculate the user's total XP from all of their answers.
        user = User.query.filter_by(uuid=user_uuid).first()
        total_xp = recalc_user_xp(user)
        user.xp = total_xp
        session["xp"] = total_xp
        db.session.commit()

        # Check and award any new achievements
        answer_data = {
            "input_mode": input_mode,
            "total_score": avg_all,
            "evaluation_scores": evaluation["scores"],
        }
        newly_awarded = check_and_award_achievements(user, answer_data, session)

        old_level = get_level_name(old_xp)
        new_level = get_level_name(total_xp)
        leveled_up = old_level != new_level
        level_info = get_level_info(total_xp)

        # Add previous level image if user leveled up
        if leveled_up:
            previous_level = get_level_for_xp(old_xp)
            level_info["previous_level_image"] = previous_level.image_path

        logger.info(
            f"Answer processed for user: {user_uuid} for question: {data.get('question_id')}"
        )

        response_data = {
            "evaluation": {
                **evaluation,
                "total_score": avg_all,  # Ensure total_score is included at the root level
            },
            "xp_gained": xp_earned,
            "total_xp": total_xp,
            "leveled_up": leveled_up,
            "level_info": level_info,
            "relevance_too_low": relevance_too_low,
            "answer_id": new_answer.id,
            "current_level": level_info["display_name"],
        }

        # Add any newly awarded achievements to the response
        if newly_awarded:
            response_data["achievements"] = [
                {
                    "id": achievement.id,
                    "name": achievement.name,
                    "description": achievement.description,
                    "name_key": achievement.name_key,
                    "description_key": achievement.description_key,
                }
                for achievement in newly_awarded
            ]

        return jsonify(response_data)
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.session.remove()


@answers_bp.route("/submit_challenge_response", methods=["POST"])
@limiter.limit(
    SETTINGS.SUBMISSION_RATE_LIMITS,
    error_message="Too many submissions. Please wait before trying again.",
)
def submit_challenge_response():
    try:
        if not request.is_json:
            return jsonify({"error": "Content-Type must be application/json"}), 400

        data = request.json
        challenge_response = data.get("challenge_response", "").strip()
        answer_id = data.get("answer_id")
        input_mode = data.get(
            "input_mode", "text"
        )  # Get input mode from request or default to text

        logger.debug(f"Challenge response received for answer_id: {answer_id}")

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

        # Check today's evaluation count (initial submission counts as one)
        daily_count = get_daily_evaluation_count(user_uuid)
        user = User.query.filter_by(uuid=user_uuid).first()
        eval_limit = get_eval_limit(user.tier)

        if daily_count >= eval_limit:
            error_message = f"Daily evaluation limit reached ({eval_limit}). "
            if user.tier == "anonymous":
                error_message += (
                    'Log in for higher limits <a href="#" class="underline" '
                    'onclick="showAuthModal(); return false;">here</a>.'
                )
            else:
                error_message += (
                    'If you need a higher limit, let me know in the <a href="#" class="underline" '
                    'onclick="showFeedbackModal(); return false;">feedback</a>.'
                )
            return jsonify({"error": error_message}), 429

        try:
            evaluator = create_evaluator()
            evaluation = evaluator.evaluate_challenge(answer, challenge_response)
        except Exception as eval_error:
            logger.error(f"Error during challenge evaluation: {str(eval_error)}")
            return jsonify({"error": f"Evaluation error: {str(eval_error)}"}), 500

        scores = evaluation["scores"]
        all_keys = [
            "Relevance",
            "Logical Structure",
            "Clarity",
            "Depth",
            "Objectivity",
            "Creativity",
        ]
        try:
            logger.debug(f"Calculating average score from keys: {all_keys}")
            avg_all = sum(scores[key] for key in all_keys) / len(all_keys)
            logger.debug(f"Average score calculated: {avg_all}")
        except Exception as avg_error:
            logger.error(f"Error calculating average score: {str(avg_error)}")
            return jsonify({"error": f"Score calculation error: {str(avg_error)}"}), 500

        # Only award XP if the overall average meets the threshold.
        xp_gained = (
            round(avg_all * 10)
            if scores["Relevance"] >= SETTINGS.RELEVANCE_THRESHOLD_FOR_XP
            else 0
        )
        logger.info(f"Challenge average: {avg_all}, XP gained: {xp_gained}")

        # Update the answer with the new challenge response and XP.
        try:
            logger.debug("Updating answer with challenge response and scores")
            answer.challenge_response = challenge_response

            # Use consistent property name without quotes to avoid issues
            scores_dict = {**evaluation["scores"]}
            scores_dict["Overall"] = avg_all

            feedback_dict = {**evaluation["feedback"]}
            feedback_dict["Overall"] = evaluation["overall_feedback"]

            answer.challenge_evaluation_scores = scores_dict
            answer.challenge_evaluation_feedback = feedback_dict
            answer.challenge_xp_earned = xp_gained

            db.session.commit()
            logger.debug("Answer successfully updated in database")
        except Exception as db_error:
            logger.error(f"Database error: {str(db_error)}")
            return jsonify({"error": f"Database error: {str(db_error)}"}), 500

        try:
            user = User.query.filter_by(uuid=user_uuid).first()
            new_total = recalc_user_xp(user)
            user.xp = new_total
            session["xp"] = new_total
            db.session.commit()
            logger.debug(f"User XP updated: {new_total}")
        except Exception as xp_error:
            logger.error(f"Error updating user XP: {str(xp_error)}")
            return jsonify({"error": f"XP update error: {str(xp_error)}"}), 500

        # Check and award any new achievements
        try:
            logger.debug("Checking for achievements")
            challenge_answer_data = {
                "input_mode": input_mode,  # Use the input mode we defined above
                "total_score": avg_all,  # Use the avg_all we calculated directly instead of trying to access it through scores
                "evaluation_scores": evaluation["scores"],
                "is_challenge": True,
                "argument": challenge_response,  # Include the challenge response text
            }
            newly_awarded = check_and_award_achievements(
                user, challenge_answer_data, session
            )
            logger.debug(f"Newly awarded achievements: {newly_awarded}")
        except Exception as achievement_error:
            logger.error(f"Error checking achievements: {str(achievement_error)}")
            return jsonify(
                {"error": f"Achievement error: {str(achievement_error)}"}
            ), 500

        try:
            leveled_up = get_level_name(
                recalc_user_xp(user) - xp_gained
            ) != get_level_name(new_total)
            level_info = get_level_info(new_total)

            # Add previous level image if user leveled up
            if leveled_up:
                previous_level = get_level_for_xp(recalc_user_xp(user) - xp_gained)
                level_info["previous_level_image"] = previous_level.image_path

            logger.debug(f"Leveled up: {leveled_up}")
        except Exception as level_error:
            logger.error(f"Error checking level info: {str(level_error)}")
            return jsonify({"error": f"Level info error: {str(level_error)}"}), 500

        try:
            logger.debug("Building response data")
            # Make sure evaluation has consistent structure
            eval_copy = dict(evaluation)
            if "total_score" not in eval_copy:
                eval_copy["total_score"] = avg_all

            response_data = {
                "evaluation": eval_copy,
                "challenge_xp_earned": xp_gained,
                "current_xp": new_total,
                "current_level": level_info["display_name"],
                "leveled_up": leveled_up,
                "level_info": level_info,
                "relevance_too_low": scores["Relevance"]
                < SETTINGS.RELEVANCE_THRESHOLD_FOR_XP,
            }

            # Add any newly awarded achievements to the response
            if newly_awarded:
                response_data["achievements"] = [
                    {
                        "id": achievement.id,
                        "name": achievement.name,
                        "description": achievement.description,
                        "name_key": achievement.name_key,
                        "description_key": achievement.description_key,
                    }
                    for achievement in newly_awarded
                ]

            logger.debug("Response prepared successfully, returning to client")
            return jsonify(response_data)
        except Exception as response_error:
            logger.error(f"Error preparing response: {str(response_error)}")
            return jsonify(
                {"error": f"Response preparation error: {str(response_error)}"}
            ), 500

    except Exception as e:
        logger.error(f"Uncaught exception in challenge response: {str(e)}")
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.session.remove()


def recalc_user_xp(user):
    answers = (
        Answer.query.filter_by(user_uuid=user.uuid)
        .order_by(Answer.created_at.desc(), Answer.id.desc())
        .all()
    )
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
