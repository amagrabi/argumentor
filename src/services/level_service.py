from typing import Optional, TypedDict

from constants.levels import Level


class LevelProgress(TypedDict):
    """Type definition for level progress information."""

    xp_into_level: int
    xp_needed: int
    progress_percent: float
    next_level: str


class LevelInfo(TypedDict):
    """Type definition for complete level information."""

    level_number: int
    level_label: str
    display_name: str
    current_threshold: int
    next_threshold: Optional[int]
    xp_into_level: int
    xp_needed: int
    progress_percent: float
    next_level: str
    level_image: str


def get_next_level(level: Level) -> Optional[Level]:
    """Get the next level after the given level, or None if at max level."""
    if level.id >= len(Level.all_levels):
        return None
    return Level.all_levels[level.id]  # Since levels are 1-indexed


def calculate_level_progress(level: Level, xp: int) -> LevelProgress:
    """Calculate progress information for a level given an XP amount."""
    next_level = get_next_level(level)

    xp_into_level = xp - level.xp_threshold
    xp_needed = (next_level.xp_threshold - level.xp_threshold) if next_level else 0
    progress_percent = (
        (xp_into_level / xp_needed * 100) if next_level and xp_needed > 0 else 100
    )

    return {
        "xp_into_level": xp_into_level,
        "xp_needed": xp_needed,
        "progress_percent": progress_percent,
        "next_level": next_level.display_name if next_level else "Max Level",
    }


def get_level_for_xp(xp: int) -> Level:
    """Get the current level for a given XP amount."""
    current_level = Level.all_levels[0]
    for level in Level.all_levels:
        if xp >= level.xp_threshold:
            current_level = level
        else:
            break
    return current_level


def get_level_name(xp: int) -> str:
    """Get just the name of the level for the given XP amount."""
    return get_level_for_xp(xp).name


def get_level_info(xp: int) -> LevelInfo:
    """Get complete level information for the given XP amount."""
    level = get_level_for_xp(xp)
    progress = calculate_level_progress(level, xp)
    next_threshold = (
        (progress["xp_needed"] + level.xp_threshold)
        if progress["xp_needed"] > 0
        else None
    )

    return {
        "level_number": level.id,
        "level_label": level.name,
        "display_name": level.display_name,
        "current_threshold": level.xp_threshold,
        "next_threshold": next_threshold,
        "xp_into_level": progress["xp_into_level"],
        "xp_needed": progress["xp_needed"],
        "progress_percent": progress["progress_percent"],
        "next_level": progress["next_level"],
        "level_image": level.image_path,
    }
