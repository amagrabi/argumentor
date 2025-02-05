import random


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
