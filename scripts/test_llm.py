from google.genai import types

from config import get_settings
from services.llm import CLIENT, RESPONSE_SCHEMA, SYSTEM_INSTRUCTION_EN

SETTINGS = get_settings()

QUESTION = "Will you or will you not win the lottery today?"
CLAIM = "I will win the lottery today."
ARGUMENT = (
    "I have a very strong feeling that my lottery ticket is the winning ticket, "
    "so I'm quite confident I will win a lot of money tonight."
)
COUNTERARGUMENT_REBUTTAL = ""

PROMPT = f"""Question: {QUESTION}
Claim: {CLAIM}
Argument: {ARGUMENT}
Refuting Counterarguments (Optional): {COUNTERARGUMENT_REBUTTAL}
"""


def generate():
    config = types.GenerateContentConfig(
        temperature=0,  # default was 2
        top_p=0,  # default was 0.95
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
        system_instruction=[types.Part.from_text(text=SYSTEM_INSTRUCTION_EN)],
    )

    contents = [
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=PROMPT)],
        ),
    ]

    for chunk in CLIENT.models.generate_content_stream(
        model=SETTINGS.MODEL,
        contents=contents,
        config=config,
    ):
        print(chunk.text, end="")


if __name__ == "__main__":
    generate()
