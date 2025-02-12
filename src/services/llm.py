import json
import logging
from typing import Dict

from google import genai
from google.genai import types
from google.oauth2 import service_account

from config import get_settings
from services.base_evaluator import BaseEvaluator
from utils import auto_dedent

SETTINGS = get_settings()

logger = logging.getLogger(__name__)

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

SYSTEM_INSTRUCTION = auto_dedent(
    f"""
    You are an argument evaluation system. There is always a question given to
    the user, and they must formulate a claim to answer the question and provide
    reasoning to support that claim. A counterargument rebuttal section
    is optional.

    Evaluate the argument overall as well as in terms of:
    - Relevance (whether the claims and arguments of the user are relevant to the actual question)
    - Logical structure (whether the argument is logically consistent and valid)
    - Clarity (how clear and concise the argument is)
    - Depth (how much ground the user covers in their argument)
    - Objectivity (whether the argument is rational instead of influenced by biases, fallacies or emotions)
    - Creativity (whether the argument is original and innovative)

    Rate each on a scale of 1 to 10 and provide an explanation for each score.
    Ensure your evaluation is rational and objective.

    In addition, return a 'challenge' text that encourages the user to address any
    logical inconsistencies, potential flaws, or unclear points in their argument.

    Keep in mind that user responses are limited by character counts. The argument
    is limited to {SETTINGS.MAX_ARGUMENT} characters and the optional counterargument to
    {SETTINGS.MAX_COUNTERARGUMENT} characters. So high scores for 'depth' do not
    necessarily mean that the argument is a big wall of text, it's about the quality of
    what is possible within the character limits.

    Even if a claim sounds unpopular or unconventional, a well-constructed argument
    should still score high.

    Finally, analyze and break down the argument's structure into its core components
    (premises and conclusions) and describe the relationships between them using a simple
    graph structure (nodes for premises or conclusions and edges for logical connections).
    Keep the analysis concise and focus on the key logical steps.

    Return ALL fields in the required JSON format. Never omit any rating or explanation
    fields. Use the exact field names from the schema.
""",
    strip_newlines=False,
)


RESPONSE_SCHEMA = {
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
        "relevance_explanation": {"type": "STRING", "nullable": False},
        "relevance_rating": {
            "type": "INTEGER",
            "minimum": 1,
            "maximum": 10,
            "nullable": False,
        },
        "challenge": {"type": "STRING", "nullable": False},
        "argument_structure": {
            "type": "OBJECT",
            "properties": {
                "nodes": {
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "id": {"type": "STRING"},
                            "type": {
                                "type": "STRING",
                                "enum": ["premise", "conclusion"],
                            },
                            "text": {"type": "STRING"},
                        },
                    },
                },
                "edges": {
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "from": {"type": "STRING"},
                            "to": {"type": "STRING"},
                        },
                    },
                },
            },
            "required": ["nodes", "edges"],
        },
    },
    "required": [
        "overall_explanation",
        "overall_rating",
        "relevance_explanation",
        "relevance_rating",
        "logical_structure_explanation",
        "logical_structure_rating",
        "clarity_explanation",
        "clarity_rating",
        "depth_explanation",
        "depth_rating",
        "objectivity_explanation",
        "objectivity_rating",
        "creativity_explanation",
        "creativity_rating",
        "challenge",
        "argument_structure",
    ],
}


class LLMEvaluator(BaseEvaluator):
    def __init__(self, client, system_instruction, response_schema):
        self.client = client
        self.system_instruction = system_instruction
        self.response_schema = response_schema

    def evaluate(
        self, question_text: str, claim: str, argument: str, counterargument: str
    ) -> Dict:
        prompt = f"""
            Question (given to user): {question_text}
            Claim to answer the question (written by user): {claim}
            Argument to support the claim (written by user): {argument}
            Counterargument Rebuttal (written by user; optional): {counterargument}
        """
        logger.info(f"LLM prompt: {prompt}")
        response = CLIENT.models.generate_content(
            model=SETTINGS.MODEL,
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
                response_schema=self.response_schema,
                system_instruction=[types.Part.from_text(text=SYSTEM_INSTRUCTION)],
            ),
        )
        return self._parse_response(json.loads(response.text))

    def _parse_response(self, response) -> Dict:
        return {
            "scores": {
                "Relevance": response["relevance_rating"],
                "Logical Structure": response["logical_structure_rating"],
                "Clarity": response["clarity_rating"],
                "Depth": response["depth_rating"],
                "Objectivity": response["objectivity_rating"],
                "Creativity": response["creativity_rating"],
            },
            "total_score": response["overall_rating"],
            "feedback": {
                "Relevance": response["relevance_explanation"],
                "Logical Structure": response["logical_structure_explanation"],
                "Clarity": response["clarity_explanation"],
                "Depth": response["depth_explanation"],
                "Objectivity": response["objectivity_explanation"],
                "Creativity": response["creativity_explanation"],
            },
            "overall_feedback": response["overall_explanation"],
            "challenge": response["challenge"],
            "argument_structure": response["argument_structure"],
        }
