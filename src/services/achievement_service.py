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


def check_and_award_achievements(
    user: User, answer_data: dict, session=None
) -> List[Achievement]:
    """Check for and award any newly earned achievements

    Args:
        user: The user to check achievements for
        answer_data: Data about the answer submission
        session: Optional Flask session object for anonymous users

    Returns:
        List of newly awarded achievements
    """
    if not user:
        return []

    newly_awarded = []

    # For tracking achievements for anonymous users
    session_achievements = []
    if session and "earned_achievements" in session:
        session_achievements = session.get("earned_achievements", [])

    # Check each achievement condition
    def award_achievement(achievement_id):
        """Helper to award achievement to user and track in session"""
        # Award to user if authenticated
        if user.is_authenticated:
            if not user.has_achievement(achievement_id):
                user.award_achievement(achievement_id)
                newly_awarded.append(ACHIEVEMENTS_BY_ID[achievement_id])
        # Track in session for anonymous users
        elif session is not None:
            if achievement_id not in session_achievements:
                session_achievements.append(achievement_id)
                newly_awarded.append(ACHIEVEMENTS_BY_ID[achievement_id])

    # First argument achievement
    if not user.is_authenticated or not user.has_achievement("first_argument"):
        award_achievement("first_argument")

    # Voice pioneer
    has_voice_pioneer = user.is_authenticated and user.has_achievement("voice_pioneer")
    if answer_data.get("input_mode") == "voice" and not has_voice_pioneer:
        award_achievement("voice_pioneer")

    # Check for exceptional rating
    total_score = answer_data.get("total_score", 0)
    has_exceptional = user.is_authenticated and user.has_achievement(
        "exceptional_rating"
    )
    if total_score >= 9 and not has_exceptional:
        award_achievement("exceptional_rating")

    # Check for master of all categories
    scores = answer_data.get("evaluation_scores", {})
    has_master = user.is_authenticated and user.has_achievement("master_of_all")
    if all(score >= 9 for score in scores.values()) and not has_master:
        award_achievement("master_of_all")

    # Check for wordsmith (long argument)
    argument = answer_data.get("argument", "")
    has_wordsmith = user.is_authenticated and user.has_achievement("wordsmith")
    if len(argument) > 900 and total_score >= 7.5 and not has_wordsmith:
        award_achievement("wordsmith")

    # Check for concise master
    has_concise = user.is_authenticated and user.has_achievement("concise_master")
    if len(argument) < 200 and total_score >= 7.5 and not has_concise:
        award_achievement("concise_master")

    # Count total answers and award milestones - only for authenticated users
    if user.is_authenticated:
        MIN_SCORE = 4
        answer_count = sum(
            1 for a in user.answers if getattr(a, "total_score", 0) >= MIN_SCORE
        )
        if answer_count >= 10 and not user.has_achievement("ten_answers"):
            award_achievement("ten_answers")

        if answer_count >= 25 and not user.has_achievement("twenty_five_answers"):
            award_achievement("twenty_five_answers")

        if answer_count >= 50 and not user.has_achievement("fifty_answers"):
            award_achievement("fifty_answers")

        if answer_count >= 100 and not user.has_achievement("hundred_answers"):
            award_achievement("hundred_answers")
    else:
        MIN_SCORE = 4

    # Count voice answers - only for authenticated users
    if user.is_authenticated:
        voice_answers = sum(1 for a in user.answers if a.input_mode == "voice")
        if voice_answers >= 10 and not user.has_achievement("voice_master"):
            award_achievement("voice_master")

        # Check for category explorer achievement - only for authenticated users
        answered_categories = {
            get_question_category(a.question_id)
            for a in user.answers
            if a.question_id and get_question_category(a.question_id)
        }
        if len(answered_categories) >= 9 and not user.has_achievement(
            "category_explorer"
        ):  # All 9 categories
            award_achievement("category_explorer")

    # Check for challenge achievements
    if answer_data.get("is_challenge") and total_score >= MIN_SCORE:
        has_challenge = user.is_authenticated and user.has_achievement(
            "first_challenge"
        )
        if not has_challenge:
            award_achievement("first_challenge")

        # Only check these for authenticated users
        if user.is_authenticated:
            challenge_count = sum(
                1
                for a in user.answers
                if a.challenge_response and getattr(a, "total_score", 0) >= MIN_SCORE
            )

            if challenge_count >= 10 and not user.has_achievement("ten_challenges"):
                award_achievement("ten_challenges")

            if challenge_count >= 100 and not user.has_achievement(
                "hundred_challenges"
            ):
                award_achievement("hundred_challenges")

    # Update the session with achievements for non-authenticated users
    if session is not None and not user.is_authenticated and session_achievements:
        session["earned_achievements"] = session_achievements

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
