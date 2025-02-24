from typing import List

from models import User
from services.question_service import get_questions
from src.constants.achievements import ACHIEVEMENTS, ACHIEVEMENTS_BY_ID, Achievement


def get_question_category(question_id):
    """Get the category for a given question ID."""
    if not question_id:
        return None

    questions = get_questions()
    for category, category_questions in questions.items():
        for question in category_questions:
            if question["id"] == question_id:
                return category
    return None


def check_and_award_achievements(user: User, answer_data: dict) -> List[Achievement]:
    """Check for and award any newly earned achievements"""
    if not user:
        return []

    newly_awarded = []

    # Check each achievement condition
    if not user.has_achievement("first_argument"):
        user.award_achievement("first_argument")
        newly_awarded.append(ACHIEVEMENTS_BY_ID["first_argument"])

    if answer_data.get("input_mode") == "voice" and not user.has_achievement(
        "voice_pioneer"
    ):
        user.award_achievement("voice_pioneer")
        newly_awarded.append(ACHIEVEMENTS_BY_ID["voice_pioneer"])

    # Check for exceptional rating
    total_score = answer_data.get("total_score", 0)
    if total_score >= 9 and not user.has_achievement("exceptional_rating"):
        user.award_achievement("exceptional_rating")
        newly_awarded.append(ACHIEVEMENTS_BY_ID["exceptional_rating"])

    # Check for master of all categories
    scores = answer_data.get("evaluation_scores", {})
    if all(score >= 9 for score in scores.values()) and not user.has_achievement(
        "master_of_all"
    ):
        user.award_achievement("master_of_all")
        newly_awarded.append(ACHIEVEMENTS_BY_ID["master_of_all"])

    # Check for wordsmith (long argument)
    argument = answer_data.get("argument", "")
    if (
        len(argument) > 900
        and total_score >= 7.5
        and not user.has_achievement("wordsmith")
    ):
        user.award_achievement("wordsmith")
        newly_awarded.append(ACHIEVEMENTS_BY_ID["wordsmith"])

    # Check for concise master
    if (
        len(argument) < 200
        and total_score >= 7.5
        and not user.has_achievement("concise_master")
    ):
        user.award_achievement("concise_master")
        newly_awarded.append(ACHIEVEMENTS_BY_ID["concise_master"])

    # Count total answers and award milestones
    MIN_SCORE = 4
    answer_count = sum(
        1 for a in user.answers if getattr(a, "total_score", 0) >= MIN_SCORE
    )
    if answer_count >= 10 and not user.has_achievement("ten_answers"):
        user.award_achievement("ten_answers")
        newly_awarded.append(ACHIEVEMENTS_BY_ID["ten_answers"])

    if answer_count >= 25 and not user.has_achievement("twenty_five_answers"):
        user.award_achievement("twenty_five_answers")
        newly_awarded.append(ACHIEVEMENTS_BY_ID["twenty_five_answers"])

    if answer_count >= 50 and not user.has_achievement("fifty_answers"):
        user.award_achievement("fifty_answers")
        newly_awarded.append(ACHIEVEMENTS_BY_ID["fifty_answers"])

    if answer_count >= 100 and not user.has_achievement("hundred_answers"):
        user.award_achievement("hundred_answers")
        newly_awarded.append(ACHIEVEMENTS_BY_ID["hundred_answers"])

    # Count voice answers
    voice_answers = sum(1 for a in user.answers if a.input_mode == "voice")
    if voice_answers >= 10 and not user.has_achievement("voice_master"):
        user.award_achievement("voice_master")
        newly_awarded.append(ACHIEVEMENTS_BY_ID["voice_master"])

    # Check for category explorer achievement
    answered_categories = {
        get_question_category(a.question_id)
        for a in user.answers
        if a.question_id and get_question_category(a.question_id)
    }
    if len(answered_categories) >= 9 and not user.has_achievement(
        "category_explorer"
    ):  # All 9 categories
        user.award_achievement("category_explorer")
        newly_awarded.append(ACHIEVEMENTS_BY_ID["category_explorer"])

    # Check for challenge achievements
    if answer_data.get("is_challenge") and total_score >= MIN_SCORE:
        if not user.has_achievement("first_challenge"):
            user.award_achievement("first_challenge")
            newly_awarded.append(ACHIEVEMENTS_BY_ID["first_challenge"])

        challenge_count = sum(
            1
            for a in user.answers
            if a.challenge_response and getattr(a, "total_score", 0) >= MIN_SCORE
        )

        if challenge_count >= 10 and not user.has_achievement("ten_challenges"):
            user.award_achievement("ten_challenges")
            newly_awarded.append(ACHIEVEMENTS_BY_ID["ten_challenges"])

        if challenge_count >= 100 and not user.has_achievement("hundred_challenges"):
            user.award_achievement("hundred_challenges")
            newly_awarded.append(ACHIEVEMENTS_BY_ID["hundred_challenges"])

    return newly_awarded


def get_all_achievements() -> List[Achievement]:
    """Get list of all possible achievements"""
    return ACHIEVEMENTS


def get_user_achievements(user: User) -> List[Achievement]:
    """Get list of achievements earned by user"""
    if not user:
        return []
    return [
        ACHIEVEMENTS_BY_ID[a.achievement_id]
        for a in user.achievements
        if a.achievement_id in ACHIEVEMENTS_BY_ID
    ]
