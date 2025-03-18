import gc
import io
import logging
import platform
import re
import resource
import uuid
from datetime import UTC, datetime, time

from flask import Blueprint, jsonify, request, session
from google import genai
from google.cloud import storage

from config import get_settings
from extensions import db, google_credentials, openai_client
from models import User
from utils import (
    get_daily_voice_count,
    get_monthly_voice_count,
    get_monthly_voice_limit,
    get_voice_limit,
)

logger = logging.getLogger(__name__)
transcribe_bp = Blueprint("transcribe", __name__)
SETTINGS = get_settings()

# Initialize Gemini client
CLIENT = genai.Client(
    vertexai=True,
    credentials=google_credentials,
    project=SETTINGS.GCLOUD_PROJECT_NAME,
    location=SETTINGS.GCLOUD_PROJECT_REGION,
)

TRANSCRIPTION_SYSTEM_PROMPT_EN = """
You are a transcription post-processor. You are seeing text that has
been recorded by users who are answering a difficult question and constructing
arguments to support a specific claim.

Your task is to improve the quality of speech-to-text transcriptions by:
1. Fixing punctuation and capitalization
2. Correcting obvious word recognition errors or add missing words based on context
3. Maintaining the original meaning while making the text more readable
4. Remove meaningless filler words like "um" or "you know"

Only make changes when you are highly confident they improve transcription accuracy or readability.

You must ONLY output the improved transcription text.
Do not add any other text like "Here's the improved version" or "I'm ready".
If you cannot improve the text, output the original text exactly as is.
"""

TRANSCRIPTION_SYSTEM_PROMPT_DE = """
Du bist ein Transkriptions-Nachbearbeiter. Du siehst Text, der von
Benutzern aufgenommen wurde, die eine schwierige Frage beantworten und
Argumente zur Unterstützung einer bestimmten These konstruieren.

Deine Aufgabe ist es, die Qualität der Sprache-zu-Text-Transkriptionen zu verbessern durch:
1. Korrektur von Zeichensetzung und Großschreibung
2. Korrektur offensichtlicher Worterkennungsfehler oder Ergänzung fehlender Wörter basierend auf dem Kontext
3. Beibehaltung der ursprünglichen Bedeutung bei gleichzeitiger Verbesserung der Lesbarkeit
4. Entfernung bedeutungsloser Füllwörter wie "Ähm"/"ähm"/"äh" oder "sozusagen"

Nimm nur dann Änderungen vor, wenn du sehr sicher bist, dass sie die Transkriptionsgenauigkeit oder Lesbarkeit verbessern.

Du musst NUR den verbesserten Transkriptionstext ausgeben.
Füge keinen anderen Text wie "Hier ist die verbesserte Version" oder "Ich bin bereit" hinzu.
Wenn du den Text nicht verbessern kannst, gib den Originaltext genau so aus, wie er ist.
"""

TRANSCRIPTION_SYSTEM_PROMPTS = {
    "en": TRANSCRIPTION_SYSTEM_PROMPT_EN,
    "de": TRANSCRIPTION_SYSTEM_PROMPT_DE,
}


def post_process_transcription(
    transcript: str, language: str = "en", question_text: str = None
) -> str:
    """
    Uses LLM to improve the transcription quality by fixing common issues.
    """
    try:
        # Return early if transcript is empty or too short
        if not transcript or len(transcript.strip()) < 3:
            logger.debug("Transcript too short for post-processing")
            return transcript

        logger.debug(f"Original transcription before post-processing: {transcript}")

        # Select the appropriate system prompt based on language
        system_prompt = TRANSCRIPTION_SYSTEM_PROMPTS.get(
            language, TRANSCRIPTION_SYSTEM_PROMPT_EN
        )
        logger.debug(f"Selected system prompt for language {language}")

        user_prompt = f"""
        Please improve this speech-to-text transcription and make it more readable while preserving its original meaning.
        Focus on fixing punctuation, capitalization, obvious recognition errors, and removing filler words like "um", "uh", "you know".
        The user tried to answer this question: {question_text}

        Original transcription:
        {transcript}
        """

        if language == "de":
            user_prompt = f"""
            Bitte verbessere diese Sprache-zu-Text-Transkription und verbessere die Lesbarkeit unter Beibehaltung ihrer ursprünglichen Bedeutung.
            Konzentriere dich auf die Korrektur von Zeichensetzung, Großschreibung, offensichtlichen Erkennungsfehlern und entferne Füllwörter wie "ähm", "äh", "sozusagen".
            Der Benutzer versucht, diese Frage zu beantworten: {question_text}

            Ursprüngliche Transkription:
            {transcript}
            """

        logger.debug("Starting LLM post-processing")
        llm_response = None
        improved_transcript = None
        try:
            llm_response = CLIENT.models.generate_content(
                model=SETTINGS.MODEL,
                contents=[
                    genai.types.Content(
                        role="user",
                        parts=[genai.types.Part.from_text(text=user_prompt)],
                    )
                ],
                config=genai.types.GenerateContentConfig(
                    temperature=0.1,  # Low temperature for more consistent output
                    top_p=0.8,
                    top_k=40,
                    max_output_tokens=2048,
                    safety_settings=[
                        genai.types.SafetySetting(
                            category="HARM_CATEGORY_HATE_SPEECH", threshold="OFF"
                        ),
                        genai.types.SafetySetting(
                            category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="OFF"
                        ),
                        genai.types.SafetySetting(
                            category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="OFF"
                        ),
                        genai.types.SafetySetting(
                            category="HARM_CATEGORY_HARASSMENT", threshold="OFF"
                        ),
                    ],
                    system_instruction=[genai.types.Part.from_text(text=system_prompt)],
                ),
            )

            # Extract the text from the response
            if hasattr(llm_response, "text"):
                improved_transcript = llm_response.text.strip()
            elif hasattr(llm_response, "parts") and llm_response.parts:
                improved_transcript = llm_response.parts[0].text.strip()
            else:
                logger.warning(
                    "Unexpected response format from LLM, using original transcript"
                )
                improved_transcript = transcript

            # Free up memory
            if "user_prompt" in locals():
                del user_prompt
            if llm_response:
                del llm_response
            gc.collect()

            logger.debug(
                f"LLM post-processing completed. Result: {improved_transcript}"
            )
            return improved_transcript
        except Exception as e:
            logger.error(f"Error in LLM post-processing: {str(e)}", exc_info=True)
            # If LLM processing fails, return the original transcript
            # Clean up any resources
            if "user_prompt" in locals():
                del user_prompt
            if llm_response:
                del llm_response
            gc.collect()
            return transcript

    except Exception as e:
        logger.error(f"Error in post-processing setup: {str(e)}", exc_info=True)
        gc.collect()
        return transcript


def upload_audio_to_gcs(audio_content, file_mime):
    # Initialize a GCS client with our credentials
    storage_client = storage.Client(credentials=google_credentials)
    bucket_name = SETTINGS.GCS_BUCKET
    bucket = storage_client.bucket(bucket_name)
    extension = "webm" if "webm" in file_mime or "ogg" in file_mime else "wav"
    filename = f"voice_recordings/{uuid.uuid4()}.{extension}"
    blob = bucket.blob(filename)
    blob.upload_from_string(audio_content, content_type=file_mime)
    logger.debug(f"Uploaded audio file to GCS: gs://{bucket_name}/{filename}")
    return f"gs://{bucket_name}/{filename}"


def transcribe_audio(audio_content, file_mime):
    """
    Transcribes the audio content using OpenAI's Whisper API.
    """
    import gc

    from flask import session

    # Capture session-dependent data
    language = session.get("language", SETTINGS.DEFAULT_LANGUAGE)
    language_code = getattr(SETTINGS, "LANGUAGE_CODES", {}).get(language, "en-US")

    # Log the language being used for transcription
    logger.info("Transcribing audio using language: %s (%s)", language, language_code)

    try:
        # Determine the file extension based on mime type
        extension = "webm" if "webm" in file_mime or "ogg" in file_mime else "wav"
        temp_file_name = f"temp_audio_{uuid.uuid4()}.{extension}"

        logger.debug(f"Processing audio for Whisper API, mime type: {file_mime}")

        # Set up the OpenAI API parameters
        # language parameter is the BCP-47 language tag like 'en' or 'de'
        # simplified_language_code takes just the first part of language_code (en-US -> en)
        simplified_language_code = language_code.split("-")[0]

        logger.debug(f"Calling Whisper API with language: {simplified_language_code}")

        with io.BytesIO(audio_content) as audio_file:
            audio_file.name = temp_file_name
            response = openai_client.audio.transcriptions.create(
                model=SETTINGS.WHISPER_MODEL,
                file=audio_file,
                response_format=SETTINGS.WHISPER_RESPONSE_FORMAT,
                language=simplified_language_code,  # Optional, Whisper can auto-detect language
                temperature=0,  # Use lower temperature for more accurate transcription
            )

        # Get the transcript text from the response
        # When response_format is 'text', the response is a string directly
        if SETTINGS.WHISPER_RESPONSE_FORMAT == "text":
            # Handle the case where response is already a string
            transcript = response if isinstance(response, str) else response.text
        else:
            # For other formats like JSON, the response has a structure
            if hasattr(response, "text"):
                transcript = response.text
            else:
                # Fallback for other response formats
                logger.warning(
                    f"Handling non-standard response format: {type(response)}"
                )
                transcript = str(response)

        logger.debug(
            f"Whisper API transcription successful. Transcript length: {len(transcript)}"
        )

        # Force garbage collection
        gc.collect()

        # Return the cleaned transcript
        clean_transcript = re.sub(r"\s+", " ", transcript).strip()
        return clean_transcript

    except Exception as e:
        logger.error(f"Error in Whisper API transcription: {e}", exc_info=True)
        gc.collect()
        return ""


@transcribe_bp.route("/check_voice_limits", methods=["GET"])
def check_voice_limits():
    """
    Check if the user has reached their daily or monthly voice recording limits
    before they start recording.
    """
    user_uuid = session.get("user_id")
    if not user_uuid:
        return jsonify({"error": "User not identified."}), 400

    # Check daily voice recording count
    user = User.query.filter_by(uuid=user_uuid).first()
    if not user:
        return jsonify({"error": "User not found"}), 400

    daily_count = get_daily_voice_count(user_uuid)
    voice_limit = get_voice_limit(user.tier)

    if daily_count >= voice_limit:
        error_message = (
            f"Daily voice recording limit reached ({voice_limit}). "
            if session.get("language", SETTINGS.DEFAULT_LANGUAGE) == "en"
            else f"Tägliches Sprachaufnahmelimit erreicht ({voice_limit}). "
        )
        if user.tier == "anonymous":
            error_message += (
                (
                    'Log in for higher limits <a href="/login" class="underline">here</a>.'
                )
                if session.get("language", SETTINGS.DEFAULT_LANGUAGE) == "en"
                else (
                    'Für höhere Limits kannst du dich <a href="/login" class="underline">hier</a> anmelden.'
                )
            )
        else:
            error_message += (
                (
                    'Upgrade your account for higher limits <a href="/subscription" class="underline">here</a>.'
                )
                if session.get("language", SETTINGS.DEFAULT_LANGUAGE) == "en"
                else (
                    'Erhöhe dein Limit durch ein Upgrade deines Kontos <a href="/subscription" class="underline">hier</a>.'
                )
            )
        return jsonify({"error": error_message, "limit_reached": True}), 200

    # Check monthly voice recording count
    monthly_count = get_monthly_voice_count(user_uuid)
    monthly_limit = get_monthly_voice_limit(user.tier)

    if monthly_count >= monthly_limit:
        error_message = (
            f"Monthly voice recording limit reached ({monthly_limit}). "
            if session.get("language", SETTINGS.DEFAULT_LANGUAGE) == "en"
            else f"Monatliches Sprachaufnahmelimit erreicht ({monthly_limit}). "
        )
        if user.tier == "anonymous":
            error_message += (
                (
                    'Log in for higher limits <a href="/login" class="underline">here</a>.'
                )
                if session.get("language", SETTINGS.DEFAULT_LANGUAGE) == "en"
                else (
                    'Für höhere Limits kannst du dich <a href="/login" class="underline">hier</a> anmelden.'
                )
            )
        else:
            error_message += (
                (
                    'Upgrade your account for higher limits <a href="/subscription" class="underline">here</a>.'
                )
                if session.get("language", SETTINGS.DEFAULT_LANGUAGE) == "en"
                else (
                    'Erhöhe dein Limit durch ein Upgrade deines Kontos <a href="/subscription" class="underline">hier</a>.'
                )
            )
        return jsonify({"error": error_message, "limit_reached": True}), 200

    # If no limits are reached, return success
    return jsonify({"limit_reached": False}), 200


@transcribe_bp.route("/transcribe_voice", methods=["POST"])
def transcribe_voice():
    import tracemalloc

    tracemalloc.start()

    try:
        logger.debug("Starting voice transcription request")
        user_uuid = session.get("user_id")
        if not user_uuid:
            return jsonify({"error": "User not identified."}), 400

        # Check daily voice recording count
        user = User.query.filter_by(uuid=user_uuid).first()
        if not user:
            return jsonify({"error": "User not found"}), 400

        daily_count = get_daily_voice_count(user_uuid)
        voice_limit = get_voice_limit(user.tier)

        if daily_count >= voice_limit:
            error_message = (
                f"Daily voice recording limit reached ({voice_limit}). "
                if session.get("language", SETTINGS.DEFAULT_LANGUAGE) == "en"
                else f"Tägliches Sprachaufnahmelimit erreicht ({voice_limit}). "
            )
            if user.tier == "anonymous":
                error_message += (
                    (
                        'Log in for higher limits <a href="/login" class="underline">here</a>.'
                    )
                    if session.get("language", SETTINGS.DEFAULT_LANGUAGE) == "en"
                    else (
                        'Für höhere Limits kannst du dich <a href="/login" class="underline">hier</a> anmelden.'
                    )
                )
            else:
                error_message += (
                    (
                        'Upgrade your account for higher limits <a href="/subscription" class="underline">here</a>.'
                    )
                    if session.get("language", SETTINGS.DEFAULT_LANGUAGE) == "en"
                    else (
                        'Erhöhe dein Limit durch ein Upgrade deines Kontos <a href="/subscription" class="underline">hier</a>.'
                    )
                )
            return jsonify({"error": error_message}), 429

        # Check monthly voice recording count
        monthly_count = get_monthly_voice_count(user_uuid)
        monthly_limit = get_monthly_voice_limit(user.tier)

        if monthly_count >= monthly_limit:
            error_message = (
                f"Monthly voice recording limit reached ({monthly_limit}). "
                if session.get("language", SETTINGS.DEFAULT_LANGUAGE) == "en"
                else f"Monatliches Sprachaufnahmelimit erreicht ({monthly_limit}). "
            )
            if user.tier == "anonymous":
                error_message += (
                    (
                        'Log in for higher limits <a href="/login" class="underline">here</a>.'
                    )
                    if session.get("language", SETTINGS.DEFAULT_LANGUAGE) == "en"
                    else (
                        'Für höhere Limits kannst du dich <a href="/login" class="underline">hier</a> anmelden.'
                    )
                )
            else:
                error_message += (
                    (
                        'Upgrade your account for higher limits <a href="/subscription" class="underline">here</a>.'
                    )
                    if session.get("language", SETTINGS.DEFAULT_LANGUAGE) == "en"
                    else (
                        'Erhöhe dein Limit durch ein Upgrade deines Kontos <a href="/subscription" class="underline">hier</a>.'
                    )
                )
            return jsonify({"error": error_message}), 429

        # Get the audio file from the request
        if "file" not in request.files:
            return jsonify({"error": "No audio file provided"}), 400

        audio_file = request.files["file"]
        if not audio_file:
            return jsonify({"error": "No audio file provided"}), 400

        try:
            logger.debug("Processing voice transcription")
            # Update voice transcription count
            today_start = datetime.combine(datetime.now(UTC).date(), time.min)
            today_start = today_start.replace(tzinfo=UTC)

            # Ensure the datetime is timezone-aware before comparison
            last_transcription = user.last_voice_transcription
            if last_transcription and last_transcription.tzinfo is None:
                last_transcription = last_transcription.replace(tzinfo=UTC)

            if not last_transcription or last_transcription < today_start:
                user.daily_voice_count = 1
            else:
                user.daily_voice_count += 1
            user.last_voice_transcription = datetime.now(UTC)

            # Update monthly voice count
            user.monthly_voice_count = (user.monthly_voice_count or 0) + 1
            user.last_monthly_voice_reset = (
                user.last_monthly_voice_reset or datetime.now(UTC)
            )

            db.session.commit()

            # Get the current language and question
            language = session.get("language", SETTINGS.DEFAULT_LANGUAGE)
            question_text = request.args.get("question", "")
            logger.debug(f"Using language: {language}, Question: {question_text}")

            # Process the initial transcription
            logger.debug("Starting initial transcription")
            transcript = None
            try:
                # Access the audio file that was validated earlier
                audio_content = audio_file.read()
                if not audio_content:
                    logger.error("Empty audio file provided")
                    return jsonify({"error": "Empty audio file provided"}), 400

                transcript = transcribe_audio(audio_content, audio_file.content_type)
                logger.debug(f"Initial transcription result: {transcript}")
            except Exception as e:
                logger.error(
                    f"Error during initial transcription: {str(e)}", exc_info=True
                )
                return jsonify({"error": "Error during transcription"}), 500
            finally:
                # Ensure cleanup happens in all cases
                if "audio_content" in locals():
                    del audio_content
                gc.collect()

            # Return early if transcription failed
            if not transcript:
                logger.error("Initial transcription failed - empty transcript")
                gc.collect()
                return jsonify(
                    {
                        "error": "No text could be identified in the recording",
                        "status": "no_text",
                    }
                ), 204

            # TEMPORARILY DISABLED: Post-processing with LLM
            # The Whisper API provides high-quality transcriptions that don't require additional processing
            logger.debug(
                "LLM post-processing temporarily disabled, using raw Whisper transcription"
            )
            improved_transcript = transcript
            was_improved = False

            """
            # Post-process the transcription with LLM, including the question context
            improved_transcript = None
            original_transcript = transcript  # Save a copy for comparison
            try:
                improved_transcript = post_process_transcription(
                    transcript, language, question_text
                )
                logger.debug(f"Post-processing result: {improved_transcript}")
                # Clean up after post-processing
                if transcript:
                    del transcript
                    transcript = None
                gc.collect()
            except Exception as e:
                logger.error(f"Error during post-processing: {str(e)}", exc_info=True)
                # Ensure cleanup even on error
                if "transcript" in locals() and transcript:
                    del transcript
                gc.collect()
                return jsonify({"error": "Error during transcription"}), 500

            if not improved_transcript:
                logger.error("Post-processing failed - empty result")
                gc.collect()
                return jsonify({"error": "Error during transcription"}), 500

            was_improved = improved_transcript != original_transcript
            logger.info(f"Transcription was improved: {was_improved}")

            # Clean up before returning
            if "original_transcript" in locals():
                del original_transcript
            """

            # Final cleanup before returning response
            gc.collect()
            memory_divisor = 1024 if platform.system() != "Darwin" else 1024 * 1024
            logger.info(
                f"Memory usage after transcription: {resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / memory_divisor}MB"
            )
            return jsonify(
                {
                    "transcript": improved_transcript,
                    "status": "success",
                    "was_improved": was_improved,
                }
            )

        except Exception as e:
            logger.error(f"Error in voice transcription: {str(e)}")
            db.session.rollback()
            # Ensure memory cleanup on any exception
            gc.collect()
            return jsonify({"error": "Error processing voice recording"}), 500
    finally:
        # Ensure all references are cleared
        if "audio_content" in locals() and audio_content:
            del audio_content
        gc.collect()

        # After processing
        snapshot = tracemalloc.take_snapshot()
        top_stats = snapshot.statistics("lineno")
        logger.info("[ Top 10 memory allocations ]")
        for stat in top_stats[:10]:
            logger.info(stat)

        tracemalloc.stop()

        openai_client.close()
