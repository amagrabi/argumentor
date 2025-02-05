import json

from google import genai
from google.genai import types
from google.oauth2 import service_account

from config import get_settings

SETTINGS = get_settings()

CREDENTIALS = service_account.Credentials.from_service_account_file(
    SETTINGS.GOOGLE_APPLICATION_CREDENTIALS,
    scopes=["https://www.googleapis.com/auth/cloud-platform"],
)

CLIENT = genai.Client(
    vertexai=True,
    credentials=CREDENTIALS,
    project=SETTINGS.GCLOUD_PROJECT_NAME,
    location=SETTINGS.GCLOUD_PROJECT_REGION,
)

SYSTEM_INSTRUCTION = """You are an argument evaluation system. Arguments always start with a claim and then the reasoning to support the claim.
                    In the end there might be a section for counterargument rebuttal, but that is optional. Evaluate the argument overall as well as in terms
                    of the factors clarity, logical structure, depth, objectivity, creativity. Rate from a scale of 1 to 10
                    and give explanations for each score. Make sure you evaluate arguments rationally.
                    Claims could potentially be unpopular or sound strange/radical, but if an argument is well-constructed,
                    it should get a high rating regardless. Return ALL fields in the required JSON format.
                    Never omit any rating or explanation fields. Use the exact field names from the schema."""


RESPONSE_SCHEMA = response_schema = {
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
        "logical_structure_explanation": {
            "type": "STRING",
            "nullable": False,
        },
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
}


def evaluate_answer_llm(question_text, claim, argument, counterargument):
    prompt = f"""
        Question: {question_text}
        Claim: {claim}
        Argument: {argument}
        Counterargument Rebuttal (Optional): {counterargument}
    """

    response = CLIENT.models.generate_content(
        model="gemini-exp-1206",
        contents=[
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=prompt)],
            ),
        ],
        config=types.GenerateContentConfig(
            temperature=0,
            top_p=0,
            top_k=1,
            max_output_tokens=8192,
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
            response_schema=RESPONSE_SCHEMA,
            system_instruction=[types.Part.from_text(text=SYSTEM_INSTRUCTION)],
        ),
    )

    return parse_llm_response(json.loads(response.text))


def parse_llm_response(response):
    """
    Convert LLM response format to our evaluation format
    """
    return {
        "scores": {
            "Logical Structure": response["logical_structure_rating"],
            "Clarity": response["clarity_rating"],
            "Depth": response["depth_rating"],
            "Objectivity": response["objectivity_rating"],
            "Creativity": response["creativity_rating"],
        },
        "total_score": response["overall_rating"],
        "feedback": {
            "Logical Structure": response["logical_structure_explanation"],
            "Clarity": response["clarity_explanation"],
            "Depth": response["depth_explanation"],
            "Objectivity": response["objectivity_explanation"],
            "Creativity": response["creativity_explanation"],
        },
        "overall_feedback": response["overall_explanation"],
    }
