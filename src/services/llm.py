from google import genai

from config import get_settings
from extensions import google_credentials as CREDENTIALS
from utils import auto_dedent

SETTINGS = get_settings()


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

    In addition, return a 'challenge' text that encourages the user to improve their
    submitted argument by pointing out potential logical inconsistencies, flaws, unclear
    points, or unaddressed counterarguments.

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
