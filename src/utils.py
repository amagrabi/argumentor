import inspect


def auto_dedent(obj, strip_newlines=False):
    """
    Recursively dedent and clean all string values in a nested structure.
    If strip_newlines is True, removes all extra whitespace (including newlines)
    by splitting the string and rejoining with a single space.
    """
    if isinstance(obj, str):
        cleaned = inspect.cleandoc(obj)
        if strip_newlines:
            return " ".join(cleaned.split())
        return cleaned
    elif isinstance(obj, list):
        return [auto_dedent(item, strip_newlines) for item in obj]
    elif isinstance(obj, dict):
        return {key: auto_dedent(val, strip_newlines) for key, val in obj.items()}
    return obj
