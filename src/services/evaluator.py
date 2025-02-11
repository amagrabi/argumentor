import json
import random
from typing import Dict

from google.genai import types

from config import get_settings
from services.base_evaluator import BaseEvaluator
from services.llm import CLIENT, RESPONSE_SCHEMA, SYSTEM_INSTRUCTION

SETTINGS = get_settings()


class DummyEvaluator(BaseEvaluator):
    def evaluate(
        self, question_text: str, claim: str, argument: str, counterargument: str
    ) -> Dict:
        scores = {
            "Logical Structure": random.randint(1, 10),
            "Clarity": random.randint(1, 10),
            "Depth": random.randint(1, 10),
            "Objectivity": random.randint(1, 10),
            "Creativity": random.randint(1, 10),
        }

        total_score = sum(scores.values()) / len(scores)
        feedback = {
            "Logical Structure": "Your argument structure shows good coherence. Consider strengthening the connection between premises and conclusion.",
            "Clarity": "Your points are clearly expressed. Try to be even more concise in future responses.",
            "Depth": "Good analysis of key factors. Consider exploring additional philosophical implications.",
            "Objectivity": "Well-balanced perspective. Watch for potential emotional appeals.",
            "Creativity": "Interesting approach to the problem. Consider exploring even more unconventional angles.",
        }

        if total_score >= 8:
            overall_feedback = "Excellent work! Your argument is well-structured and communicated clearly."
        elif total_score >= 6:
            overall_feedback = (
                "Good effort! There is room for improvement in clarity and depth."
            )
        else:
            overall_feedback = "Your response shows potential but needs significant refinement in its reasoning."

        # Generate a dummy challenge that prompts the user to refine further.
        challenge_text = "While your argument is persuasive, consider addressing potential counterarguments and clarifying any ambiguous points."

        return {
            "scores": scores,
            "total_score": total_score,
            "feedback": feedback,
            "overall_feedback": overall_feedback,
            "challenge": challenge_text,
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
            Question: {question_text}
            Claim: {claim}
            Argument: {argument}
            Counterargument Rebuttal (Optional): {counterargument}
        """
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
                response_schema=RESPONSE_SCHEMA,
                system_instruction=[types.Part.from_text(text=SYSTEM_INSTRUCTION)],
            ),
        )

        return self._parse_response(json.loads(response.text))

    def _parse_response(self, response) -> Dict:
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
