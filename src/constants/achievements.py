from dataclasses import dataclass


@dataclass
class Achievement:
    id: str
    name: str
    description: str
    icon: str = "trophy"


ACHIEVEMENTS = [
    Achievement(
        id="first_argument",
        name="First Steps",
        description="Submit your first argument",
    ),
    Achievement(
        id="voice_pioneer",
        name="Voice Pioneer",
        description="Submit your first voice answer",
    ),
    Achievement(
        id="category_explorer",
        name="Category Explorer",
        description="Answer questions from all categories",
    ),
    Achievement(
        id="exceptional_rating",
        name="Excellence Achieved",
        description="Receive an exceptional rating (9+ score)",
    ),
    Achievement(
        id="master_of_all",
        name="Master of All",
        description="Receive a 9+ rating in all evaluation categories",
    ),
    Achievement(
        id="first_challenge",
        name="Challenge Accepted",
        description="Complete your first challenge response",
    ),
    Achievement(
        id="ten_challenges",
        name="Challenge Enthusiast",
        description="Complete 10 challenge responses",
    ),
    Achievement(
        id="hundred_challenges",
        name="Challenge Master",
        description="Complete 100 challenge responses",
    ),
    Achievement(
        id="wordsmith",
        name="Wordsmith",
        description="Submit a long argument",
    ),
    Achievement(
        id="concise_master",
        name="Concise Master",
        description="Submit a concise argument",
    ),
    Achievement(
        id="ten_answers",
        name="Getting Started",
        description="Submit 10 arguments",
    ),
    Achievement(
        id="twenty_five_answers",
        name="Regular Debater",
        description="Submit 25 arguments",
    ),
    Achievement(
        id="fifty_answers",
        name="Dedicated Contributor",
        description="Submit 50 arguments",
    ),
    Achievement(
        id="hundred_answers",
        name="Centurion",
        description="Submit 100 arguments",
    ),
    Achievement(
        id="voice_master",
        name="Voice Master",
        description="Submit 10 voice arguments",
    ),
    Achievement(
        id="great_rating",
        name="Great Rating",
        description="Receive a great rating (7+ score)",
    ),
    Achievement(
        id="all_seven_categories",
        name="Balanced Greatness",
        description="Receive a 7+ rating in all evaluation categories",
    ),
]

# Create a lookup dictionary for achievements by ID
ACHIEVEMENTS_BY_ID = {achievement.id: achievement for achievement in ACHIEVEMENTS}
