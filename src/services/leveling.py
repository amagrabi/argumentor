LEVEL_DEFINITIONS = [
    (0, 1, "Curious Mind"),
    (50, 2, "Socratic Apprentice"),
    (150, 3, "Cognitive Cartographer"),
    (300, 4, "Argument Architect"),
    (500, 5, "Epistemic Engineer"),
    (750, 6, "Debate Ninja"),
    (1000, 7, "Thought Tactician"),
    (1500, 8, "Dialectical Strategist"),
    (2000, 9, "Rational Maestro"),
    (3000, 10, "Grandmaster of Reason"),
    (5000, 11, "Legendary Logician"),
]


def get_level_image_path(level_number):
    """Get the path to the level image for the given level number."""
    return f"/static/img/levels/level_{level_number}.webp"


def get_level(xp):
    current_level = LEVEL_DEFINITIONS[0][2]
    for threshold, _, name in LEVEL_DEFINITIONS:
        if xp >= threshold:
            current_level = name
        else:
            break
    return current_level


def get_level_info(xp):
    level_definitions = LEVEL_DEFINITIONS
    current_level = level_definitions[0]
    level_number = 1
    for i, (threshold, level_num, label) in enumerate(level_definitions):
        if xp >= threshold:
            current_level = (threshold, level_num, label)
            level_number = level_num
        else:
            break
    current_threshold = current_level[0]
    next_level_index = (
        level_number if level_number < len(level_definitions) else level_number - 1
    )
    next_threshold = (
        level_definitions[next_level_index][0]
        if level_number < len(level_definitions)
        else None
    )
    xp_into_level = xp - current_threshold
    xp_needed = next_threshold - current_threshold if next_threshold is not None else 0
    progress_percent = (
        (xp_into_level / xp_needed) * 100 if next_threshold and xp_needed > 0 else 100
    )
    display_name = f"Level {level_number} ({current_level[2]})"
    if level_number < len(level_definitions):
        next_level_display = f"Level {level_definitions[next_level_index][1]} ({level_definitions[next_level_index][2]})"
    else:
        next_level_display = "Max Level"
    return {
        "level_number": level_number,
        "level_label": current_level[2],
        "display_name": display_name,
        "current_threshold": current_threshold,
        "next_threshold": next_threshold,
        "xp_into_level": xp_into_level,
        "xp_needed": xp_needed,
        "progress_percent": progress_percent,
        "next_level": next_level_display,
        "level_image": get_level_image_path(level_number),
    }
