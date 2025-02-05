from google import genai
from google.genai import types

from config import get_settings

SETTINGS = get_settings()


def generate():
    client = genai.Client(
        vertexai=True,
        project=SETTINGS.GCLOUD_PROJECT_NAME,
        location="us-central1",
    )

    model = "gemini-2.0-flash-exp"
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(
                    text="""Evaluate this argument overall as well as in terms of the factors clarity, logical structure, depth, objectivity, creativity. Rate from a scale of 1 to 10 and give explanations for each score: \"I have a very strong feeling that my lottery ticket is the winning ticket, so I’m quite confident I will win a lot of money tonight.\""""
                )
            ],
        ),
    ]
    generate_content_config = types.GenerateContentConfig(
        temperature=0,
        top_p=0.95,
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
        response_schema={
            "type": "OBJECT",
            "properties": {
                "overall_explanation": {"type": "STRING", "nullable": False},
                "overall_rating": {
                    "type": "INTEGER",
                    "minimum": 1,
                    "maximum": 10,
                    "nullable": False,
                },
                "clarity_explanation": {"type": "STRING", "nullable": False},
                "clarity_rating": {
                    "type": "INTEGER",
                    "minimum": 1,
                    "maximum": 10,
                    "nullable": False,
                },
                "logical_structure_explanation": {"type": "STRING", "nullable": False},
                "logical_structure_rating": {
                    "type": "INTEGER",
                    "minimum": 1,
                    "maximum": 10,
                    "nullable": False,
                },
                "depth_explanation": {"type": "STRING", "nullable": False},
                "depth_structure_rating": {
                    "type": "INTEGER",
                    "minimum": 1,
                    "maximum": 10,
                    "nullable": False,
                },
                "objectivity_explanation": {"type": "STRING", "nullable": False},
                "objectivity_rating": {
                    "type": "INTEGER",
                    "minimum": 1,
                    "maximum": 10,
                    "nullable": False,
                },
                "creativity_explanation": {"type": "STRING", "nullable": False},
                "creativity_rating": {
                    "type": "INTEGER",
                    "minimum": 1,
                    "maximum": 10,
                    "nullable": False,
                },
            },
        },
        system_instruction=[
            types.Part.from_text(
                text="""You are responsible for rating and evaluating arguments on a reasoning and decision-making platform."""
            )
        ],
    )

    for chunk in client.models.generate_content_stream(
        model=model,
        contents=contents,
        config=generate_content_config,
    ):
        print(chunk.text, end="")


if __name__ == "__main__":
    generate()
