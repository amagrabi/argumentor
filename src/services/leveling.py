LEVEL_DEFINITIONS = [
    (0, "Curious Mind"),
    (50, "Socratic Apprentice"),
    (150, "Cognitive Cartographer"),
    (300, "Argument Architect"),
    (500, "Epistemic Engineer"),
    (750, "Debate Ninja"),
    (1000, "Thought Tactician"),
    (1500, "Dialectical Strategist"),
    (2000, "Rational Maestro"),
    (3000, "Grandmaster of Reason"),
    (5000, "Legendary Logician"),
]


def get_level(xp):
    current_level = LEVEL_DEFINITIONS[0][1]
    for threshold, name in LEVEL_DEFINITIONS:
        if xp >= threshold:
            current_level = name
        else:
            break
    return current_level


def get_level_info(xp):
    level_definitions = LEVEL_DEFINITIONS
    current_level = level_definitions[0]
    level_number = 1
    for i, (threshold, label) in enumerate(level_definitions):
        if xp >= threshold:
            current_level = (threshold, label)
            level_number = i + 1
        else:
            break
    current_threshold = current_level[0]
    next_threshold = (
        level_definitions[level_number][0]
        if level_number < len(level_definitions)
        else None
    )
    xp_into_level = xp - current_threshold
    xp_needed = next_threshold - current_threshold if next_threshold is not None else 0
    progress_percent = (
        (xp_into_level / xp_needed) * 100 if next_threshold and xp_needed > 0 else 100
    )
    display_name = f"Level {level_number} ({current_level[1]})"
    if level_number < len(level_definitions):
        next_level_display = (
            f"Level {level_number + 1} ({level_definitions[level_number][1]})"
        )
    else:
        next_level_display = "Max Level"
    return {
        "level_number": level_number,
        "level_label": current_level[1],
        "display_name": display_name,
        "current_threshold": current_threshold,
        "next_threshold": next_threshold,
        "xp_into_level": xp_into_level,
        "xp_needed": xp_needed,
        "progress_percent": progress_percent,
        "next_level": next_level_display,
    }
