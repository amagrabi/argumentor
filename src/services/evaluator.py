import json
import logging
import random
from typing import Dict

from google.genai import types

from config import get_settings
from services.base_evaluator import BaseEvaluator

SETTINGS = get_settings()
logger = logging.getLogger(__name__)


class DummyEvaluator(BaseEvaluator):
    def evaluate(
        self, question_text: str, claim: str, argument: str, counterargument: str
    ) -> Dict:
        scores = {
            "Relevance": random.randint(1, 10),
            "Logical Structure": random.randint(1, 10),
            "Clarity": random.randint(1, 10),
            "Depth": random.randint(1, 10),
            "Objectivity": random.randint(1, 10),
            "Creativity": random.randint(1, 10),
        }

        total_score = sum(scores.values()) / len(scores)
        feedback = {
            "Relevance": "While your argument is somewhat connected to the question, ensure that all points directly address the topic.",
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

        challenge_text = "While your argument is persuasive, consider addressing potential counterarguments and clarifying any ambiguous points."

        argument_structure = {
            "nodes": [
                {
                    "id": "p1",
                    "type": "premise",
                    "text": "Main premise from the argument",
                },
                {"id": "p2", "type": "premise", "text": "Supporting premise"},
                {"id": "c1", "type": "conclusion", "text": claim},
            ],
            "edges": [{"from": "p1", "to": "c1"}, {"from": "p2", "to": "c1"}],
        }

        return {
            "scores": scores,
            "total_score": total_score,
            "feedback": feedback,
            "overall_feedback": overall_feedback,
            "challenge": challenge_text,
            "argument_structure": argument_structure,
        }

    def evaluate_challenge(self, answer, challenge_response: str) -> Dict:
        # A clean, separate evaluation for challenge responses:
        # Here we use a slightly lower scoring range (1 to 8) so that
        # challenge responses do not inadvertently get inflated scores.
        scores = {
            "Relevance": random.randint(1, 8),
            "Logical Structure": random.randint(1, 8),
            "Clarity": random.randint(1, 8),
            "Depth": random.randint(1, 8),
            "Objectivity": random.randint(1, 8),
            "Creativity": random.randint(1, 8),
        }
        total_score = sum(scores.values()) / len(scores)
        feedback = {
            "Relevance": "Your challenge response partially addresses the issue, but could be more directly relevant.",
            "Logical Structure": "The structure of your response is acceptable; clarifying connections could help.",
            "Clarity": "Some parts of your response are unclear; consider more precise language.",
            "Depth": "Your answer touches on key points but lacks deeper analysis.",
            "Objectivity": "Ensure your response remains objective in evaluating the argument.",
            "Creativity": "Your approach is interesting, but could use further innovation.",
        }
        if total_score >= 7:
            overall_feedback = (
                "Excellent challenge response with strong critical insights."
            )
        elif total_score >= 5:
            overall_feedback = (
                "Good challenge response, though there's room for further refinement."
            )
        else:
            overall_feedback = "The challenge response needs significant improvement to address the issues effectively."

        # No need to recompute an argument structure for challenge responses.
        return {
            "scores": scores,
            "total_score": total_score,
            "feedback": feedback,
            "overall_feedback": overall_feedback,
            "challenge": answer.challenge,
            "argument_structure": {},
        }


class LLMEvaluator(BaseEvaluator):
    def __init__(self, client, system_instructions, response_schema):
        self.client = client
        self.system_instructions = system_instructions
        self.response_schema = response_schema

    def build_argument_prompt(
        self, question_text: str, claim: str, argument: str, counterargument: str
    ) -> str:
        # Get current language from Flask session
        from flask import session

        language = session.get("language", SETTINGS.DEFAULT_LANGUAGE)

        if language == "de":
            return f"""
                Frage (dem Benutzer gestellt): {question_text}
                These zur Beantwortung der Frage (vom Benutzer): {claim}
                Argument zur Unterstützung der These (vom Benutzer): {argument}
                Widerlegung von Gegenargumenten (vom Benutzer; optional): {counterargument}
            """
        else:
            return f"""
                Question (given to user): {question_text}
                Claim to answer the question (written by user): {claim}
                Argument to support the claim (written by user): {argument}
                Counterargument rebuttal (written by user; optional): {counterargument}
            """

    def evaluate(
        self, question_text: str, claim: str, argument: str, counterargument: str
    ) -> Dict:
        from flask import session

        language = session.get("language", SETTINGS.DEFAULT_LANGUAGE)
        system_instruction = self.system_instructions.get(
            language, self.system_instructions[SETTINGS.DEFAULT_LANGUAGE]
        )

        prompt = self.build_argument_prompt(
            question_text, claim, argument, counterargument
        )

        try:
            response = self.client.models.generate_content(
                model=SETTINGS.MODEL,
                contents=[
                    types.Content(
                        role="user", parts=[types.Part.from_text(text=prompt)]
                    )
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
                    system_instruction=[types.Part.from_text(text=system_instruction)],
                ),
            )

            try:
                return self._parse_response(json.loads(response.text))
            except (json.JSONDecodeError, KeyError) as e:
                logger.error(f"Failed to parse LLM response: {e}")
                logger.debug(f"Prompt used: {prompt}")
                logger.debug(f"Raw response: {response.text}")
                raise

        except Exception as e:
            logger.error(f"LLM API call failed: {e}")
            logger.debug(f"Prompt used: {prompt}")
            logger.debug(f"System instruction used: {system_instruction}")
            raise

    def build_challenge_prompt(self, answer, challenge_response: str) -> str:
        from flask import session

        from utils import auto_dedent

        language = session.get("language", "en")

        if language == "de":
            return auto_dedent(f"""
                Ursprüngliche Frage (vom System): {answer.question_text}
                Ursprüngliche These (vom Benutzer): {answer.claim}
                Ursprüngliches Argument (vom Benutzer): {answer.argument}
                Ursprüngliche Widerlegung von Gegenargumenten (vom Benutzer; optional): {answer.counterargument}
                Challenge (vom System): {answer.challenge}

                Bitte bewerte die Antwort des Benutzers auf die Challenge unten.
                Konzentriere dich ausschließlich auf die Qualität dieser Challenge-Antwort und
                bewerte nicht erneut die ursprüngliche These oder das ursprüngliche Argument.

                Challenge-Antwort (vom Benutzer): {challenge_response}
            """)
        else:
            return auto_dedent(f"""
                Original question (from system): {answer.question_text}
                Original claim (from user): {answer.claim}
                Original argument (from user): {answer.argument}
                Original counterargument rebuttal (from user; optional): {answer.counterargument}
                Challenge (from system): {answer.challenge}

                Please evaluate the user's response to the challenge below.
                Focus solely on the quality of this challenge response, and do not re-evaluate the original claim or argument.

                Challenge response (from user): {challenge_response}
            """)

    def evaluate_challenge(self, answer, challenge_response: str) -> Dict:
        from flask import session

        language = session.get("language", SETTINGS.DEFAULT_LANGUAGE)
        system_instruction = self.system_instructions.get(
            language, self.system_instructions[SETTINGS.DEFAULT_LANGUAGE]
        )

        prompt = self.build_challenge_prompt(answer, challenge_response)

        try:
            response = self.client.models.generate_content(
                model=SETTINGS.MODEL,
                contents=[
                    types.Content(
                        role="user", parts=[types.Part.from_text(text=prompt)]
                    )
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
                    system_instruction=[types.Part.from_text(text=system_instruction)],
                ),
            )

            try:
                return self._parse_response(json.loads(response.text))
            except (json.JSONDecodeError, KeyError) as e:
                logger.error(f"Failed to parse challenge response: {e}")
                logger.debug(f"Challenge prompt used: {prompt}")
                logger.debug(f"Raw challenge response: {response.text}")
                raise

        except Exception as e:
            logger.error(f"LLM API call failed for challenge: {e}")
            logger.debug(f"Challenge prompt used: {prompt}")
            logger.debug(f"System instruction used: {system_instruction}")
            raise

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
