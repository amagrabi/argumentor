from google import genai
from google.genai import types
from google.oauth2 import service_account

from config import get_settings

SETTINGS = get_settings()

# Load service account credentials
credentials = service_account.Credentials.from_service_account_file(
    SETTINGS.GOOGLE_APPLICATION_CREDENTIALS,
    scopes=["https://www.googleapis.com/auth/cloud-platform"],
)

QUESTION = """Will you or will you not win the lottery today?"""

CLAIM = """I will win the lottery today."""
ARGUMENT = """I have a very strong feeling that my lottery ticket is the winning ticket, so I’m quite confident I will win a lot of money tonight."""
COUNTERARGUMENT_REBUTTAL = """"""

PROMPT = f"""Question: {QUESTION}
    Claim: {CLAIM}
    Argument: {ARGUMENT}
    Counterargument Rebuttal (Optional): {COUNTERARGUMENT_REBUTTAL}
"""


def generate():
    client = genai.Client(
        vertexai=True,
        credentials=credentials,
        project=SETTINGS.GCLOUD_PROJECT_NAME,
        location=SETTINGS.GCLOUD_PROJECT_REGION,
    )

    model = "gemini-exp-1206"  # gemini-2.0-flash-exp   # gemini-1.5-pro-latest
    contents = [
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=PROMPT)],
        ),
    ]
    generate_content_config = types.GenerateContentConfig(
        temperature=0,  # default: 2
        top_p=0,  # default: 0.95
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
                "depth_rating": {
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
            "required": [
                "overall_explanation",
                "overall_rating",
                "clarity_explanation",
                "clarity_rating",
                "logical_structure_explanation",
                "logical_structure_rating",
                "depth_explanation",
                "depth_rating",
                "objectivity_explanation",
                "objectivity_rating",
                "creativity_explanation",
                "creativity_rating",
            ],
        },
        system_instruction=[
            types.Part.from_text(
                text="""You are an argument evaluation system. Arguments always start with a claim and then the reasoning to support the claim.
                In the end there might be a section for counterargument rebuttal, but that is optional. Evaluate the argument overall as well as in terms
                of the factors clarity, logical structure, depth, objectivity, creativity. Rate from a scale of 1 to 10
                and give explanations for each score. Make sure you evaluate arguments rationally.
                Claims could potentially be unpopular or sound strange/radical, but if an argument is well-constructed,
                it should get a high rating regardless. Return ALL fields in the required JSON format.
                Never omit any rating or explanation fields. Use the exact field names from the schema."""
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
