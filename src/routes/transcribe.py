import logging
import re
import uuid
from datetime import UTC, datetime, time

from flask import Blueprint, jsonify, request, session
from google import genai
from google.cloud import speech, storage

from config import get_settings
from extensions import db, google_credentials
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
    import gc

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

        prompt = f"""
        Please improve this speech-to-text transcription and make it more readable while preserving its original meaning.
        Focus on fixing punctuation, capitalization, obvious recognition errors, and removing filler words like "um", "uh", "you know".
        The user tried to answer this question: {question_text}

        Original transcription:
        {transcript}
        """

        if language == "de":
            prompt = f"""
            Bitte verbessere diese Sprache-zu-Text-Transkription und verbessere die Lesbarkeit unter Beibehaltung ihrer ursprünglichen Bedeutung.
            Konzentriere dich auf die Korrektur von Zeichensetzung, Großschreibung, offensichtlichen Erkennungsfehlern und entferne Füllwörter wie "ähm", "äh", "sozusagen".
            Der Benutzer versucht, diese Frage zu beantworten: {question_text}

            Ursprüngliche Transkription:
            {transcript}
            """

        logger.debug("Starting LLM post-processing")
        try:
            response = CLIENT.models.generate_content(
                model=SETTINGS.MODEL,
                contents=[
                    genai.types.Content(
                        role="user", parts=[genai.types.Part.from_text(text=prompt)]
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
            if hasattr(response, "text"):
                improved_transcript = response.text.strip()
            elif hasattr(response, "parts") and response.parts:
                improved_transcript = response.parts[0].text.strip()
            else:
                logger.warning(
                    "Unexpected response format from LLM, using original transcript"
                )
                improved_transcript = transcript

            # Free up memory
            del prompt
            del response
            gc.collect()

            logger.debug(
                f"LLM post-processing completed. Result: {improved_transcript}"
            )
            return improved_transcript
        except Exception as e:
            logger.error(f"Error in LLM post-processing: {str(e)}", exc_info=True)
            # If LLM processing fails, return the original transcript
            return transcript

    except Exception as e:
        logger.error(f"Error in post-processing setup: {str(e)}", exc_info=True)
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
    Transcribes the audio content. If the audio is longer than a certain threshold,
    it is split into chunks that are transcribed concurrently.
    """
    import gc
    import io
    from concurrent.futures import ThreadPoolExecutor, as_completed

    from flask import session
    from pydub import AudioSegment

    chunk_length_ms = SETTINGS.VOICE_CHUNK_LIMIT
    # Determine the input format based on file_mime.
    input_format = "webm" if "webm" in file_mime or "ogg" in file_mime else "wav"
    logger.debug(
        f"Audio format determined as: {input_format} from mime type: {file_mime}"
    )

    try:
        logger.debug("Loading audio file for processing")
        audio = AudioSegment.from_file(io.BytesIO(audio_content), format=input_format)
        logger.debug(
            f"Audio loaded successfully. Duration: {len(audio)}ms, Channels: {audio.channels}, Sample width: {audio.sample_width}, Frame rate: {audio.frame_rate}"
        )
        # Free up memory
        del audio_content
        gc.collect()
    except Exception as e:
        logger.error(f"Error loading audio file for chunking: {e}", exc_info=True)
        return ""

    # Capture session-dependent data before launching background tasks.
    language = session.get("language", SETTINGS.DEFAULT_LANGUAGE)
    language_code = getattr(SETTINGS, "LANGUAGE_CODES", {}).get(language, "en-US")

    # Log the language being used for transcription.
    logger.info("Transcribing audio using language: %s (%s)", language, language_code)

    def process_audio_chunk(audio_segment, language_code):
        """
        Exports the given AudioSegment to a WAV byte stream and then performs synchronous speech recognition.
        """
        try:
            # Convert the audio segment's sample rate to 16000 Hz, sample width to 16 bit (2 bytes),
            # and ensure it's in mono (1 channel)
            logger.debug(
                f"Processing chunk. Original properties - Duration: {len(audio_segment)}ms, Channels: {audio_segment.channels}, Sample width: {audio_segment.sample_width}, Frame rate: {audio_segment.frame_rate}"
            )

            audio_segment = (
                audio_segment.set_frame_rate(16000).set_sample_width(2).set_channels(1)
            )
            logger.debug(
                f"Chunk converted. New properties - Duration: {len(audio_segment)}ms, Channels: {audio_segment.channels}, Sample width: {audio_segment.sample_width}, Frame rate: {audio_segment.frame_rate}"
            )

            buffer = io.BytesIO()
            audio_segment.export(buffer, format="wav")
            chunk_bytes = buffer.getvalue()
            logger.debug(f"Exported WAV chunk size: {len(chunk_bytes)} bytes")

            # Free up memory
            del buffer

            # Prepare Google Speech API client and config.
            client = speech.SpeechClient(credentials=google_credentials)
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=16000,  # Matches the exported WAV header
                language_code=language_code,
                model=SETTINGS.VOICE_MODEL,
                use_enhanced=SETTINGS.VOICE_ENHANCED,
                enable_automatic_punctuation=SETTINGS.VOICE_PUNCTUATION,
                audio_channel_count=1,
            )
            logger.debug(
                f"Speech recognition config: model={SETTINGS.VOICE_MODEL}, enhanced={SETTINGS.VOICE_ENHANCED}, punctuation={SETTINGS.VOICE_PUNCTUATION}"
            )

            audio_request = speech.RecognitionAudio(content=chunk_bytes)
            try:
                # Use synchronous recognition with a timeout.
                logger.debug("Starting speech recognition request")
                response = client.recognize(
                    config=config, audio=audio_request, timeout=30
                )
                chunk_transcript = ""
                for result in response.results:
                    chunk_transcript += result.alternatives[0].transcript + " "
                logger.debug(
                    f"Speech recognition successful. Transcript length: {len(chunk_transcript)}"
                )
                # Free up memory
                del chunk_bytes
                del audio_request
                gc.collect()
                return chunk_transcript
            except Exception as e:
                logger.error(f"Error transcribing chunk: {e}", exc_info=True)
                return ""
        except Exception as e:
            logger.error(f"Error processing audio chunk: {e}", exc_info=True)
            return ""

    # If the entire audio is short enough, process it as one chunk.
    if len(audio) <= chunk_length_ms:
        logger.debug(f"Processing audio as single chunk (duration: {len(audio)}ms)")
        transcript = process_audio_chunk(audio, language_code)
        # Free up memory
        del audio
        gc.collect()
        return transcript.strip()
    else:
        # Split audio into chunks.
        logger.debug(
            f"Splitting audio into chunks. Total duration: {len(audio)}ms, Chunk size: {chunk_length_ms}ms"
        )
        chunks = [
            audio[i : i + chunk_length_ms]
            for i in range(0, len(audio), chunk_length_ms)
        ]
        logger.debug(f"Split into {len(chunks)} chunks")
        # Free up original audio to save memory
        del audio
        gc.collect()

        transcript_chunks = ["" for _ in range(len(chunks))]

        # Process each chunk with limited concurrency to avoid memory issues
        # Limit to max 2 concurrent threads to reduce memory usage
        max_workers = min(2, len(chunks))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_index = {
                executor.submit(process_audio_chunk, chunk, language_code): idx
                for idx, chunk in enumerate(chunks)
            }
            for future in as_completed(future_to_index):
                idx = future_to_index[future]
                try:
                    transcript_chunks[idx] = future.result().strip()
                    logger.debug(f"Chunk {idx} processed successfully")
                except Exception as e:
                    logger.error(f"Error processing chunk {idx}: {e}", exc_info=True)
                    transcript_chunks[idx] = ""

        # Free up chunks to save memory
        del chunks
        gc.collect()

        full_transcript = " ".join(transcript_chunks)
        # Replace any occurrence of multiple whitespace characters with a single space
        clean_transcript = re.sub(r"\s+", " ", full_transcript).strip()
        logger.debug(
            f"All chunks processed. Final transcript length: {len(clean_transcript)}"
        )
        return clean_transcript


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
        user.last_monthly_voice_reset = user.last_monthly_voice_reset or datetime.now(
            UTC
        )

        db.session.commit()

        # Get the current language and question
        language = session.get("language", SETTINGS.DEFAULT_LANGUAGE)
        question_text = request.args.get("question", "")
        logger.debug(f"Using language: {language}, Question: {question_text}")

        # Process the initial transcription
        logger.debug("Starting initial transcription")
        try:
            transcript = transcribe_audio(audio_file.read(), audio_file.content_type)
            logger.debug(f"Initial transcription result: {transcript}")
        except Exception as e:
            logger.error(f"Error during initial transcription: {str(e)}", exc_info=True)
            return jsonify({"error": "Error during transcription"}), 500

        # Return early if transcription failed
        if not transcript:
            logger.error("Initial transcription failed - empty transcript")
            return jsonify(
                {
                    "error": "No text could be identified in the recording",
                    "status": "no_text",
                }
            ), 204

        logger.debug("Initial transcription successful, starting post-processing")
        # Post-process the transcription with LLM, including the question context
        try:
            improved_transcript = post_process_transcription(
                transcript, language, question_text
            )
            logger.debug(f"Post-processing result: {improved_transcript}")
        except Exception as e:
            logger.error(f"Error during post-processing: {str(e)}", exc_info=True)
            return jsonify({"error": "Error during transcription"}), 500

        if not improved_transcript:
            logger.error("Post-processing failed - empty result")
            return jsonify({"error": "Error during transcription"}), 500

        was_improved = improved_transcript != transcript
        logger.info(f"Transcription was improved: {was_improved}")

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
        return jsonify({"error": "Error processing voice recording"}), 500
