import logging
import re
import sys
import uuid
import weakref
from contextlib import contextmanager
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

# Use weakrefs for the client pool to prevent strong references
SPEECH_CLIENT_POOL = []
MAX_POOL_SIZE = 2

# We'll use a weak reference for the Gemini client
_CLIENT_REF = None


def get_gemini_client():
    """Get or create a Gemini client with weakref tracking"""
    global _CLIENT_REF
    client = None if _CLIENT_REF is None else _CLIENT_REF()

    if client is None:
        client = genai.Client(
            vertexai=True,
            credentials=google_credentials,
            project=SETTINGS.GCLOUD_PROJECT_NAME,
            location=SETTINGS.GCLOUD_PROJECT_REGION,
        )
        # Store as weak reference so it can be garbage collected if memory pressure occurs
        _CLIENT_REF = weakref.ref(client)

    return client


def cleanup_gemini_client():
    """Force explicit cleanup of Gemini client"""
    global _CLIENT_REF
    if _CLIENT_REF is not None:
        client = _CLIENT_REF()
        if client is not None:
            # Try to close client if it has a close method
            if hasattr(client, "close") and callable(getattr(client, "close")):
                try:
                    client.close()
                except Exception as e:
                    logger.debug(f"Error closing Gemini client: {e}")
        _CLIENT_REF = None

    # Force garbage collection
    import gc

    gc.collect(2)


@contextmanager
def get_speech_client():
    """
    Resource manager for speech clients that reuses clients from the pool
    or creates new ones when needed, with more aggressive cleanup.
    """
    client = None
    try:
        # Try to get a client from the pool
        if SPEECH_CLIENT_POOL:
            client = SPEECH_CLIENT_POOL.pop()
            # Verify the client is still usable
            if not hasattr(client, "recognize"):
                # Client appears to be in an invalid state, create a new one
                if hasattr(client, "close") and callable(getattr(client, "close")):
                    try:
                        client.close()
                    except Exception:
                        pass
                client = speech.SpeechClient(credentials=google_credentials)
        else:
            # Create a new client if pool is empty
            client = speech.SpeechClient(credentials=google_credentials)

        # Yield the client for use
        yield client

    except Exception as e:
        logger.error(f"Speech client error: {e}")
        if client is not None:
            try:
                if hasattr(client, "close") and callable(getattr(client, "close")):
                    client.close()
            except Exception:
                pass
            client = None
        raise

    finally:
        # Return client to the pool if it's still valid
        if client is not None:
            # Only keep a limited number of clients in the pool
            if len(SPEECH_CLIENT_POOL) < MAX_POOL_SIZE:
                SPEECH_CLIENT_POOL.append(client)
            else:
                # If pool is full, force close the client
                try:
                    if hasattr(client, "close") and callable(getattr(client, "close")):
                        client.close()
                except Exception as e:
                    logger.debug(f"Error closing speech client: {e}")
                client = None

        # Try to force Python to clear internal caches
        import gc

        gc.collect(2)


def clear_speech_client_pool():
    """Explicitly close and clear all speech clients in the pool"""
    global SPEECH_CLIENT_POOL

    for client in SPEECH_CLIENT_POOL:
        try:
            if hasattr(client, "close") and callable(getattr(client, "close")):
                client.close()
        except Exception as e:
            logger.debug(f"Error closing pooled speech client: {e}")

    # Clear the pool
    SPEECH_CLIENT_POOL.clear()

    # Force garbage collection
    import gc

    gc.collect(2)


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

    # Force a full garbage collection before starting
    gc.collect(2)

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
            # Get the shared client
            client = get_gemini_client()

            llm_response = client.models.generate_content(
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
            if "system_prompt" in locals():
                del system_prompt
            if llm_response:
                del llm_response

            # Force garbage collection
            gc.collect(0)  # Collect youngest generation first
            gc.collect(1)  # Collect middle generation
            gc.collect(2)  # Full collection including oldest objects

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
            if "system_prompt" in locals():
                del system_prompt
            if llm_response:
                del llm_response

            # Force garbage collection
            gc.collect(0)
            gc.collect(1)
            gc.collect(2)
            return transcript

    except Exception as e:
        logger.error(f"Error in post-processing setup: {str(e)}", exc_info=True)
        # Force garbage collection
        gc.collect(2)
        return transcript


@contextmanager
def managed_audio_segment(audio_content, format_name):
    """
    Context manager for handling AudioSegment objects to ensure proper cleanup.
    """
    import gc
    import io

    from pydub import AudioSegment

    audio = None
    audio_buffer = None

    try:
        audio_buffer = io.BytesIO(audio_content)
        audio = AudioSegment.from_file(audio_buffer, format=format_name)
        yield audio
    finally:
        # Clean up resources in reverse order of creation
        if audio is not None:
            # Remove any circular references in the audio object
            for attr_name in dir(audio):
                if not attr_name.startswith("_"):
                    try:
                        setattr(audio, attr_name, None)
                    except (AttributeError, TypeError):
                        pass
            del audio

        if audio_buffer is not None:
            audio_buffer.close()
            del audio_buffer

        # Clear the memory
        gc.collect(2)


def upload_audio_to_gcs(audio_content, file_mime):
    # Initialize a GCS client with our credentials
    storage_client = None
    try:
        storage_client = storage.Client(credentials=google_credentials)
        bucket_name = SETTINGS.GCS_BUCKET
        bucket = storage_client.bucket(bucket_name)
        extension = "webm" if "webm" in file_mime or "ogg" in file_mime else "wav"
        filename = f"voice_recordings/{uuid.uuid4()}.{extension}"
        blob = bucket.blob(filename)
        blob.upload_from_string(audio_content, content_type=file_mime)
        logger.debug(f"Uploaded audio file to GCS: gs://{bucket_name}/{filename}")
        return f"gs://{bucket_name}/{filename}"
    finally:
        # Try to clean up the storage client
        if storage_client:
            try:
                if hasattr(storage_client, "close") and callable(
                    getattr(storage_client, "close")
                ):
                    storage_client.close()
            except Exception as e:
                logger.debug(f"Error closing storage client: {e}")
            storage_client = None
            import gc

            gc.collect(2)


def transcribe_audio(audio_content, file_mime):
    """
    Transcribes the audio content. If the audio is longer than a certain threshold,
    it is split into chunks that are transcribed concurrently.
    """
    import gc
    import io
    import sys
    from concurrent.futures import ThreadPoolExecutor, as_completed

    from flask import session

    # Force a full garbage collection before starting
    gc.collect(0)  # Young generation
    gc.collect(1)  # Middle generation
    gc.collect(2)  # Old generation

    # Try to clear type caches
    try:
        sys._clear_type_cache()
    except AttributeError as e:
        logger.debug(f"Could not clear type cache: {e}")

    chunk_length_ms = SETTINGS.VOICE_CHUNK_LIMIT
    # Determine the input format based on file_mime.
    input_format = "webm" if "webm" in file_mime or "ogg" in file_mime else "wav"
    logger.debug(
        f"Audio format determined as: {input_format} from mime type: {file_mime}"
    )

    # Capture session-dependent data before launching background tasks.
    language = session.get("language", SETTINGS.DEFAULT_LANGUAGE)
    language_code = getattr(SETTINGS, "LANGUAGE_CODES", {}).get(language, "en-US")

    # Log the language being used for transcription.
    logger.info("Transcribing audio using language: %s (%s)", language, language_code)

    def process_audio_chunk(audio_segment, language_code):
        """
        Exports the given AudioSegment to a WAV byte stream and then performs synchronous speech recognition.
        """
        import gc

        buffer = None
        chunk_bytes = None
        audio_request = None

        try:
            # Convert the audio segment's sample rate to 16000 Hz, sample width to 16 bit (2 bytes),
            # and ensure it's in mono (1 channel)
            logger.debug(
                f"Processing chunk. Original properties - Duration: {len(audio_segment)}ms, Channels: {audio_segment.channels}, Sample width: {audio_segment.sample_width}, Frame rate: {audio_segment.frame_rate}"
            )

            # Create a new audio segment with the proper settings
            processed_segment = (
                audio_segment.set_frame_rate(16000).set_sample_width(2).set_channels(1)
            )

            # Clear reference to the original segment if it's different
            if processed_segment is not audio_segment:
                # Clean internal references
                for attr_name in dir(audio_segment):
                    if not attr_name.startswith("_"):
                        try:
                            setattr(audio_segment, attr_name, None)
                        except (AttributeError, TypeError):
                            pass
                del audio_segment
                gc.collect(2)

            audio_segment = processed_segment
            logger.debug(
                f"Chunk converted. New properties - Duration: {len(audio_segment)}ms, Channels: {audio_segment.channels}, Sample width: {audio_segment.sample_width}, Frame rate: {audio_segment.frame_rate}"
            )

            buffer = io.BytesIO()
            audio_segment.export(buffer, format="wav")
            chunk_bytes = buffer.getvalue()
            logger.debug(f"Exported WAV chunk size: {len(chunk_bytes)} bytes")

            # Free up memory
            if buffer:
                buffer.close()
                del buffer
                buffer = None

            # Clear processed segment as soon as possible
            for attr_name in dir(audio_segment):
                if not attr_name.startswith("_"):
                    try:
                        setattr(audio_segment, attr_name, None)
                    except (AttributeError, TypeError):
                        pass
            del audio_segment
            gc.collect(0)

            # Use resource manager for speech client
            with get_speech_client() as client:
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

                # Free up memory but don't destroy the client (it's handled by the context manager)
                if chunk_bytes:
                    del chunk_bytes
                    chunk_bytes = None
                if audio_request:
                    del audio_request
                    audio_request = None
                if response:
                    # Clear any references in the response
                    for result in response.results:
                        for alt in result.alternatives:
                            alt.transcript = None
                    del response
                    response = None

                # Force garbage collection
                gc.collect(2)
                return chunk_transcript
        except Exception as e:
            logger.error(f"Error transcribing chunk: {e}", exc_info=True)
            return ""
        finally:
            # Ensure all resources are cleaned up
            if "buffer" in locals() and buffer:
                buffer.close()
                del buffer
            if "chunk_bytes" in locals() and chunk_bytes:
                del chunk_bytes
            if "audio_request" in locals() and audio_request:
                del audio_request
            gc.collect(2)

    # Use a context manager to handle the audio segment
    with managed_audio_segment(audio_content, input_format) as audio:
        if not audio:
            logger.error("Failed to load audio")
            return ""

        # Free up memory from audio_content since we've loaded the audio
        del audio_content
        gc.collect(2)

        # If the entire audio is short enough, process it as one chunk.
        if len(audio) <= chunk_length_ms:
            logger.debug(f"Processing audio as single chunk (duration: {len(audio)}ms)")
            transcript = process_audio_chunk(audio, language_code)
            # Audio will be cleaned up by the context manager
            # Force garbage collection
            gc.collect(2)
            return transcript.strip()
        else:
            # Split audio into chunks.
            logger.debug(
                f"Splitting audio into chunks. Total duration: {len(audio)}ms, Chunk size: {chunk_length_ms}ms"
            )

            # Calculate number of chunks and process them
            num_chunks = (len(audio) + chunk_length_ms - 1) // chunk_length_ms
            logger.debug(f"Will create {num_chunks} chunks")

            transcript_chunks = []

            # Process each chunk with limited concurrency to avoid memory issues
            # Limit to max 2 concurrent threads to reduce memory usage
            max_workers = min(2, num_chunks)

            # Use executor as context manager for auto-cleanup
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = []

                # Submit tasks in batches to avoid keeping all chunks in memory
                for i in range(0, num_chunks):
                    start_ms = i * chunk_length_ms
                    end_ms = min(start_ms + chunk_length_ms, len(audio))

                    # Extract chunk and submit for processing
                    chunk = audio[start_ms:end_ms]
                    futures.append(
                        executor.submit(process_audio_chunk, chunk, language_code)
                    )
                    # Delete reference to chunk immediately
                    del chunk

                    # Perform garbage collection every few chunks to prevent memory build-up
                    if i % 3 == 0:
                        gc.collect(0)

                # Collect results as they complete
                for future in as_completed(futures):
                    try:
                        result = future.result().strip()
                        transcript_chunks.append(result)
                        logger.debug(
                            f"Chunk processed successfully, result length: {len(result)}"
                        )
                    except Exception as e:
                        logger.error(f"Error processing chunk: {e}", exc_info=True)
                        transcript_chunks.append("")

                # Clear references to futures
                futures.clear()
                del futures

            # Audio will be cleaned up by the context manager

            # Force garbage collection after all chunks are processed
            gc.collect(0)  # Young generation
            gc.collect(1)  # Middle generation
            gc.collect(2)  # Old generation

            # Join the transcripts
            full_transcript = " ".join(transcript_chunks)

            # Replace any occurrence of multiple whitespace characters with a single space
            clean_transcript = re.sub(r"\s+", " ", full_transcript).strip()
            logger.debug(
                f"All chunks processed. Final transcript length: {len(clean_transcript)}"
            )

            # Final cleanup
            del transcript_chunks
            del full_transcript

            # Try to clear cached imports and internal references
            try:
                # Reset import caches
                import importlib

                importlib.invalidate_caches()

                # Clear Python's internal reference caches
                sys._clear_type_cache()
                if hasattr(sys, "gettotalrefcount"):  # Only in debug builds
                    sys.gettotalrefcount()

                # Force garbage collection on all generations
                gc.collect(0)
                gc.collect(1)
                gc.collect(2)
            except Exception as e:
                # If any cleanup step fails, still do basic collection
                logger.debug(f"Error during advanced cleanup: {e}")
                gc.collect(2)

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
    import gc

    # Force a full garbage collection before starting
    gc.collect(2)

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
        audio_content = None
        transcript = None
        try:
            audio_content = audio_file.read()
            transcript = transcribe_audio(audio_content, audio_file.content_type)
            logger.debug(f"Initial transcription result: {transcript}")
            # Explicitly clean up large audio content
            if audio_content:
                del audio_content
                audio_content = None
            # Force garbage collection
            gc.collect(2)
        except Exception as e:
            logger.error(f"Error during initial transcription: {str(e)}", exc_info=True)
            # Ensure cleanup even on error
            if "audio_content" in locals() and audio_content:
                del audio_content
            # Force garbage collection
            gc.collect(2)
            return jsonify({"error": "Error during transcription"}), 500

        # Return early if transcription failed
        if not transcript:
            logger.error("Initial transcription failed - empty transcript")
            # Force garbage collection
            gc.collect(2)
            return jsonify(
                {
                    "error": "No text could be identified in the recording",
                    "status": "no_text",
                }
            ), 204

        logger.debug("Initial transcription successful, starting post-processing")
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
            # Force garbage collection
            gc.collect(2)
        except Exception as e:
            logger.error(f"Error during post-processing: {str(e)}", exc_info=True)
            # Ensure cleanup even on error
            if "transcript" in locals() and transcript:
                del transcript
            # Force garbage collection
            gc.collect(2)
            return jsonify({"error": "Error during transcription"}), 500

        if not improved_transcript:
            logger.error("Post-processing failed - empty result")
            # Force garbage collection
            gc.collect(2)
            return jsonify({"error": "Error during transcription"}), 500

        was_improved = improved_transcript != original_transcript
        logger.info(f"Transcription was improved: {was_improved}")

        # Clean up before returning
        if "original_transcript" in locals():
            del original_transcript

        # Try to clear any cached objects in the Google libraries
        # Don't reset the global client, just ensure it's cleaned up if needed
        gc.collect(2)

        # After processing, add explicit cleanup of all clients
        try:
            # At the end of the request, explicitly clean up clients
            clear_speech_client_pool()
            cleanup_gemini_client()

            # Force final garbage collection
            gc.collect(0)
            gc.collect(1)
            gc.collect(2)

            # Try to clear Python's internal caches
            sys._clear_type_cache()

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
            clear_speech_client_pool()
            cleanup_gemini_client()
            gc.collect(2)
            return jsonify({"error": "Error processing voice recording"}), 500

    except Exception as e:
        logger.error(f"Error in voice transcription: {str(e)}")
        db.session.rollback()
        # Ensure memory cleanup on any exception
        clear_speech_client_pool()
        cleanup_gemini_client()
        gc.collect(2)
        return jsonify({"error": "Error processing voice recording"}), 500
