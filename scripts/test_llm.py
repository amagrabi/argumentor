import json
import logging

from google.genai import types

from config import get_settings
from services.llm import (
    CLIENT,
    RESPONSE_SCHEMA,
    SYSTEM_INSTRUCTION_CHALLENGE_DE,
    SYSTEM_INSTRUCTION_CHALLENGE_EN,
    SYSTEM_INSTRUCTION_DE,
    SYSTEM_INSTRUCTION_EN,
)
from utils import auto_dedent

SETTINGS = get_settings()
logger = logging.getLogger(__name__)

# Test data
TEST_DATA = {
    "en": {
        "question": "Should AIs, if they gain consciousness, be legally recognized as persons and receive similar rights as humans?",
        "claim": "No. Besides humans, there are many other living beings that also have 'consciousness' but don't have access to human rights.",
        "argument": """
            - Why should AIs be directly placed on the same legal level as humans? There are animals that can recognize themselves in mirrors (elephants for example). Here we can speak of consciousness, yet elephants don't have human rights.
            - As a first step, we could discuss giving animals more extensive rights
            - At the same time, rights always involve vulnerability. Can AIs suffer?
        """,
        "counterargument": "",
        "challenge_response": "AIs might experience a different form of suffering that we don't yet understand. Just as animals experience pain and distress differently from humans, AIs could have their own form of vulnerability.",
    },
    "de": {
        "question": "Sollten KIs, falls sie Bewusstsein erlangen, rechtlich als Personen anerkannt werden und ähnliche Rechte wie Menschen erhalten?",
        "claim": "Nein. Neben Menschen gibt es noch sehr viele weitere Lebewesen, die auch 'Bewusstsein' haben und nicht gleichzeitig auch Zugriff auf Menschenrechte haben.",
        "argument": """
            - Wieso sollten KIs direkt auf die Rechtestufe von Menschen gesetzt werden. Es gibt Tiere, die sich selbst im Spiegel sehen können (Elefanten bspw). Hier kann man von Bewusstsein sprechen, gleichzeitig haben Elefanten keine Menschenrechte.
            - Man könnte in einem ersten Schritt darüber sprechen, Tiere weitreichende Rechte einzuräumen
            - Gleichzeitig gehört zu Rechten auch immer eine Vulnerabilität. Können KIs leiden?
        """,
        "counterargument": "",
        "challenge_response": "KIs könnten eine andere Form des Leidens erfahren, die wir noch nicht verstehen. So wie Tiere Schmerz und Leid anders als Menschen erfahren, könnten KIs ihre eigene Form der Vulnerabilität haben.",
    },
}


def build_argument_prompt(
    question_text: str,
    claim: str,
    argument: str,
    counterargument: str,
    language: str = "en",
) -> str:
    """Build the prompt for argument evaluation in the specified language."""
    if language == "de":
        return auto_dedent(f"""
            Frage (dem Benutzer gestellt): {question_text}
            These zur Beantwortung der Frage (vom Benutzer): {claim}
            Argument zur Unterstützung der These (vom Benutzer): {argument}
            Widerlegung von Gegenargumenten (vom Benutzer; optional): {counterargument}
        """)
    else:
        return auto_dedent(f"""
            Question (given to user): {question_text}
            Claim to answer the question (written by user): {claim}
            Argument to support the claim (written by user): {argument}
            Refute counterarguments (written by user; optional): {counterargument}
        """)


def build_challenge_prompt(
    question_text: str, challenge: str, challenge_response: str, language: str = "en"
) -> str:
    """Build the prompt for challenge evaluation in the specified language."""
    if language == "de":
        return auto_dedent(f"""
            Ursprüngliche Frage (vom System): {question_text}
            Challenge (vom System): {challenge}

            Bitte bewerte die Antwort des Benutzers auf die Challenge unten.

            Challenge-Antwort (vom Benutzer): {challenge_response}
        """)
    else:
        return auto_dedent(f"""
            Original question (from system): {question_text}
            Challenge (from system): {challenge}

            Please evaluate the user's response to the challenge below.

            Challenge response (from user): {challenge_response}
        """)


def get_config(system_instruction: str) -> types.GenerateContentConfig:
    """Get the LLM configuration with the specified system instruction."""
    return types.GenerateContentConfig(
        temperature=0,
        top_p=0,
        top_k=1,
        max_output_tokens=8192,
        response_modalities=["TEXT"],
        safety_settings=[
            types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="OFF"),
            types.SafetySetting(
                category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="OFF"
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="OFF"
            ),
            types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="OFF"),
        ],
        response_mime_type="application/json",
        response_schema=RESPONSE_SCHEMA,
        system_instruction=[types.Part.from_text(text=system_instruction)],
    )


def generate_and_print_response(
    prompt: str, system_instruction: str, stream: bool = True
):
    """Generate a response from the LLM and print it."""
    config = get_config(system_instruction)
    contents = [types.Content(role="user", parts=[types.Part.from_text(text=prompt)])]

    try:
        if stream:
            for chunk in CLIENT.models.generate_content_stream(
                model=SETTINGS.MODEL,
                contents=contents,
                config=config,
            ):
                print(chunk.text, end="")
            print("\n")  # Add newline after streaming
        else:
            response = CLIENT.models.generate_content(
                model=SETTINGS.MODEL,
                contents=contents,
                config=config,
            )
            try:
                parsed_response = json.loads(response.text)
                print(json.dumps(parsed_response, indent=2))
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse response as JSON: {e}")
                print(response.text)
    except Exception as e:
        logger.error(f"Error generating content: {e}")
        raise


def test_argument_evaluation(language: str = "en"):
    """Test the argument evaluation for a given language."""
    print(f"\nTesting argument evaluation in {language.upper()}:")
    print("-" * 80)

    data = TEST_DATA[language]
    prompt = build_argument_prompt(
        data["question"],
        data["claim"],
        data["argument"],
        data["counterargument"],
        language,
    )

    system_instruction = (
        SYSTEM_INSTRUCTION_DE if language == "de" else SYSTEM_INSTRUCTION_EN
    )
    generate_and_print_response(prompt, system_instruction, stream=False)


def test_challenge_evaluation(language: str = "en", challenge: str = None):
    """Test the challenge evaluation for a given language."""
    print(f"\nTesting challenge evaluation in {language.upper()}:")
    print("-" * 80)

    data = TEST_DATA[language]
    if not challenge:
        # Use a default challenge if none provided
        challenge = (
            "How do you define suffering in the context of AI? Can we be sure that AIs cannot suffer just because their experience might be different from biological entities?"
            if language == "en"
            else "Wie definieren Sie Leid im Kontext von KI? Können wir sicher sein, dass KIs nicht leiden können, nur weil ihre Erfahrung anders sein könnte als die biologischer Wesen?"
        )

    prompt = build_challenge_prompt(
        data["question"], challenge, data["challenge_response"], language
    )

    system_instruction = (
        SYSTEM_INSTRUCTION_CHALLENGE_DE
        if language == "de"
        else SYSTEM_INSTRUCTION_CHALLENGE_EN
    )
    generate_and_print_response(prompt, system_instruction, stream=False)


def main():
    """Run all tests."""
    # Test argument evaluation in both languages
    # test_argument_evaluation("en")
    test_argument_evaluation("de")

    # Test challenge evaluation in both languages
    # test_challenge_evaluation("en")
    # test_challenge_evaluation("de")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
