from dataclasses import dataclass
from typing import ClassVar


@dataclass
class Level:
    """A level in the game's progression system."""

    id: int
    name: str
    xp_threshold: int

    # Class variable to store all levels
    all_levels: ClassVar[list["Level"]] = []

    def __post_init__(self):
        # Add this level to the all_levels list upon creation
        Level.all_levels.append(self)

    @property
    def display_name(self) -> str:
        """Get the formatted display name for this level."""
        return f"Level {self.id} ({self.name})"

    @property
    def image_path(self) -> str:
        """Get the path to this level's image asset."""
        return f"/static/img/levels/level_{self.id}.webp"


# Define all levels - these will automatically be added to Level.all_levels
LEVELS = [
    Level(
        id=1,
        name="Curious Mind",
        xp_threshold=0,
    ),
    Level(
        id=2,
        name="Socratic Apprentice",
        xp_threshold=50,
    ),
    Level(
        id=3,
        name="Cognitive Cartographer",
        xp_threshold=150,
    ),
    Level(
        id=4,
        name="Argument Architect",
        xp_threshold=300,
    ),
    Level(
        id=5,
        name="Epistemic Engineer",
        xp_threshold=500,
    ),
    Level(
        id=6,
        name="Debate Ninja",
        xp_threshold=750,
    ),
    Level(
        id=7,
        name="Thought Tactician",
        xp_threshold=1000,
    ),
    Level(
        id=8,
        name="Dialectical Strategist",
        xp_threshold=1500,
    ),
    Level(
        id=9,
        name="Rational Maestro",
        xp_threshold=2000,
    ),
    Level(
        id=10,
        name="Grandmaster of Reason",
        xp_threshold=3000,
    ),
    Level(
        id=11,
        name="Legendary Logician",
        xp_threshold=5000,
    ),
]
