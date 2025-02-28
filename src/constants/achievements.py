from dataclasses import dataclass


@dataclass
class Achievement:
    id: str
    name_key: str  # Translation key for the name
    description_key: str  # Translation key for the description
    icon: str = "trophy"

    @property
    def name(self) -> str:
        """For backward compatibility, returns the translation key for name"""
        return f"profile.achievementData.{self.id}.name"

    @property
    def description(self) -> str:
        """For backward compatibility, returns the translation key for description"""
        return f"profile.achievementData.{self.id}.description"


ACHIEVEMENTS = [
    Achievement(
        id="first_argument",
        name_key="profile.achievementData.first_argument.name",
        description_key="profile.achievementData.first_argument.description",
    ),
    Achievement(
        id="voice_pioneer",
        name_key="profile.achievementData.voice_pioneer.name",
        description_key="profile.achievementData.voice_pioneer.description",
    ),
    Achievement(
        id="first_challenge",
        name_key="profile.achievementData.first_challenge.name",
        description_key="profile.achievementData.first_challenge.description",
    ),
    Achievement(
        id="great_rating",
        name_key="profile.achievementData.great_rating.name",
        description_key="profile.achievementData.great_rating.description",
    ),
    Achievement(
        id="exceptional_rating",
        name_key="profile.achievementData.exceptional_rating.name",
        description_key="profile.achievementData.exceptional_rating.description",
    ),
    Achievement(
        id="category_explorer",
        name_key="profile.achievementData.category_explorer.name",
        description_key="profile.achievementData.category_explorer.description",
    ),
    Achievement(
        id="concise_master",
        name_key="profile.achievementData.concise_master.name",
        description_key="profile.achievementData.concise_master.description",
    ),
    Achievement(
        id="wordsmith",
        name_key="profile.achievementData.wordsmith.name",
        description_key="profile.achievementData.wordsmith.description",
    ),
    Achievement(
        id="ten_answers",
        name_key="profile.achievementData.ten_answers.name",
        description_key="profile.achievementData.ten_answers.description",
    ),
    Achievement(
        id="voice_master",
        name_key="profile.achievementData.voice_master.name",
        description_key="profile.achievementData.voice_master.description",
    ),
    Achievement(
        id="ten_challenges",
        name_key="profile.achievementData.ten_challenges.name",
        description_key="profile.achievementData.ten_challenges.description",
    ),
    Achievement(
        id="daily_streak",
        name_key="profile.achievementData.daily_streak.name",
        description_key="profile.achievementData.daily_streak.description",
    ),
    Achievement(
        id="all_seven_categories",
        name_key="profile.achievementData.all_seven_categories.name",
        description_key="profile.achievementData.all_seven_categories.description",
    ),
    Achievement(
        id="master_of_all",
        name_key="profile.achievementData.master_of_all.name",
        description_key="profile.achievementData.master_of_all.description",
    ),
    Achievement(
        id="domain_expert",
        name_key="profile.achievementData.domain_expert.name",
        description_key="profile.achievementData.domain_expert.description",
    ),
    Achievement(
        id="twenty_five_answers",
        name_key="profile.achievementData.twenty_five_answers.name",
        description_key="profile.achievementData.twenty_five_answers.description",
    ),
    Achievement(
        id="fifty_answers",
        name_key="profile.achievementData.fifty_answers.name",
        description_key="profile.achievementData.fifty_answers.description",
    ),
    Achievement(
        id="hundred_answers",
        name_key="profile.achievementData.hundred_answers.name",
        description_key="profile.achievementData.hundred_answers.description",
    ),
    Achievement(
        id="hundred_challenges",
        name_key="profile.achievementData.hundred_challenges.name",
        description_key="profile.achievementData.hundred_challenges.description",
    ),
]

# Create a lookup dictionary for achievements by ID
ACHIEVEMENTS_BY_ID = {achievement.id: achievement for achievement in ACHIEVEMENTS}
