"""The Vertex call behind deep analysis.

Kept out of `services/evaluator.py` because it shares nothing with it but the
client: no scores, a different schema, a different model, and a thinking budget.
Folding it into `LLMEvaluator` would have meant threading a second schema and a
second model through every method for no reuse.

The model is deliberately not `SETTINGS.MODEL`. See DEEP_ANALYSIS_MODEL in
config.py for the measured latency and cost that justify a limited action rather
than an across-the-board upgrade.
"""

import json
import logging

from google.genai import types

from config import get_settings
from services.llm import (
    CLIENT,
    DEEP_ANALYSIS_INSTRUCTION_DE,
    DEEP_ANALYSIS_INSTRUCTION_EN,
    DEEP_ANALYSIS_SCHEMA,
)
from utils import auto_dedent

SETTINGS = get_settings()
logger = logging.getLogger(__name__)


def build_deep_analysis_prompt(
    question_text: str,
    claim: str,
    argument: str,
    counterargument: str,
    language: str = "en",
) -> str:
    """Restate the argument for the critic, labelling every part by its author.

    Same labelling convention as the scored pass: the model has to know which
    text is the system's and which is the user's, or it starts critiquing the
    question.
    """
    if language == "de":
        return auto_dedent(f"""
            Frage (dem Benutzer gestellt): {question_text}
            These zur Beantwortung der Frage (vom Benutzer): {claim}
            Argument zur Unterstützung der These (vom Benutzer): {argument}
            Widerlegung von Gegenargumenten (vom Benutzer; optional): {counterargument}
        """)
    return auto_dedent(f"""
        Question (given to user): {question_text}
        Claim to answer the question (written by user): {claim}
        Argument to support the claim (written by user): {argument}
        Refute counterarguments (written by user; optional): {counterargument}
    """)


def run_deep_analysis(answer, language: str = "en") -> dict:
    """Run the deep pass over a stored Answer and return the parsed result.

    Raises on an API or parse failure; the caller decides what the user sees and
    is responsible for not charging quota for a failed call.
    """
    instruction = (
        DEEP_ANALYSIS_INSTRUCTION_DE
        if language == "de"
        else DEEP_ANALYSIS_INSTRUCTION_EN
    )
    prompt = build_deep_analysis_prompt(
        answer.question_text or "",
        answer.claim or "",
        answer.argument or "",
        answer.counterargument or "",
        language=language,
    )

    logger.debug("Deep analysis - language: %s, answer: %s", language, answer.id)
    logger.debug("Deep analysis - prompt: %s", prompt)

    response = CLIENT.models.generate_content(
        model=SETTINGS.DEEP_ANALYSIS_MODEL,
        contents=[
            types.Content(role="user", parts=[types.Part.from_text(text=prompt)])
        ],
        config=types.GenerateContentConfig(
            temperature=0,
            # max_output_tokens has to cover thinking as well as the response.
            # At 8192 (the scored pass's value) gemini-2.5-pro spent the whole
            # budget on thoughts and returned MAX_TOKENS with an empty body.
            max_output_tokens=16384,
            thinking_config=types.ThinkingConfig(
                thinking_budget=SETTINGS.DEEP_ANALYSIS_THINKING_BUDGET
            ),
            response_modalities=["TEXT"],
            safety_settings=[
                types.SafetySetting(
                    category="HARM_CATEGORY_HATE_SPEECH", threshold="OFF"
                ),
                types.SafetySetting(
                    category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="OFF"
                ),
                types.SafetySetting(
                    category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="OFF"
                ),
                types.SafetySetting(
                    category="HARM_CATEGORY_HARASSMENT", threshold="OFF"
                ),
            ],
            response_mime_type="application/json",
            response_schema=DEEP_ANALYSIS_SCHEMA,
            system_instruction=[types.Part.from_text(text=instruction)],
        ),
    )

    try:
        return json.loads(response.text)
    except (json.JSONDecodeError, TypeError) as e:
        logger.error("Failed to parse deep analysis response: %s", e)
        logger.debug("Raw deep analysis response: %s", response.text)
        raise
