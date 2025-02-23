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
from utils import get_daily_voice_count, get_voice_limit

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
"""

TRANSCRIPTION_SYSTEM_PROMPT_DE = """
Du bist ein Transkriptions-Nachbearbeiter. Du siehst Text, der von
Benutzern aufgenommen wurde, die eine schwierige Frage beantworten und
Argumente zur Unterstützung einer bestimmten These konstruieren.

Deine Aufgabe ist es, die Qualität der Sprache-zu-Text-Transkriptionen zu verbessern durch:
1. Korrektur von Zeichensetzung und Großschreibung
2. Korrektur offensichtlicher Worterkennungsfehler oder Ergänzung fehlender Wörter basierend auf dem Kontext
3. Beibehaltung der ursprünglichen Bedeutung bei gleichzeitiger Verbesserung der Lesbarkeit
4. Entfernung bedeutungsloser Füllwörter wie "ähm" oder "sozusagen"

Nimm nur dann Änderungen vor, wenn du sehr sicher bist, dass sie die Transkriptionsgenauigkeit oder Lesbarkeit verbessern.
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
        logger.debug(f"Original transcription before post-processing: {transcript}")

        # Select the appropriate system prompt based on language
        system_prompt = TRANSCRIPTION_SYSTEM_PROMPTS.get(
            language, TRANSCRIPTION_SYSTEM_PROMPT_EN
        )

        prompt = f"""
        Please improve this speech-to-text transcription while preserving its original meaning.
        Focus on fixing punctuation, capitalization, and obvious recognition errors.
        The user tried to answer this question: {question_text}

        Original transcription:
        {transcript}
        """

        if language == "de":
            prompt = f"""
            Bitte verbessere diese Sprache-zu-Text-Transkription unter Beibehaltung ihrer ursprünglichen Bedeutung.
            Konzentriere dich auf die Korrektur von Zeichensetzung, Großschreibung und offensichtlichen Erkennungsfehlern.
            Der Benutzer versucht, diese Frage zu beantworten: {question_text}

            Ursprüngliche Transkription:
            {transcript}
            """

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

        improved_transcript = response.text.strip()
        logger.debug(
            f"Improved transcription after post-processing: {improved_transcript}"
        )

        if improved_transcript == transcript:
            logger.debug("No improvements made during post-processing")
        else:
            logger.debug("Transcription was improved during post-processing")

        return improved_transcript if improved_transcript else transcript

    except Exception as e:
        logger.error(f"Error in LLM post-processing: {str(e)}")
        return transcript  # Return original transcript if post-processing fails


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
    import io
    from concurrent.futures import ThreadPoolExecutor, as_completed

    from flask import session
    from pydub import AudioSegment

    chunk_length_ms = SETTINGS.VOICE_CHUNK_LIMIT
    # Determine the input format based on file_mime.
    input_format = "webm" if "webm" in file_mime or "ogg" in file_mime else "wav"

    try:
        audio = AudioSegment.from_file(io.BytesIO(audio_content), format=input_format)
    except Exception as e:
        logger.error(f"Error loading audio file for chunking: {e}")
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
        # Convert the audio segment's sample rate to 16000 Hz, sample width to 16 bit (2 bytes),
        # and ensure it's in mono (1 channel)
        audio_segment = (
            audio_segment.set_frame_rate(16000).set_sample_width(2).set_channels(1)
        )
        buffer = io.BytesIO()
        audio_segment.export(buffer, format="wav")
        chunk_bytes = buffer.getvalue()

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

        audio_request = speech.RecognitionAudio(content=chunk_bytes)
        try:
            # Use synchronous recognition with a timeout.
            response = client.recognize(config=config, audio=audio_request, timeout=30)
            chunk_transcript = ""
            for result in response.results:
                chunk_transcript += result.alternatives[0].transcript + " "
            return chunk_transcript
        except Exception as e:
            logger.error(f"Error transcribing chunk: {e}")
            return ""

    # If the entire audio is short enough, process it as one chunk.
    if len(audio) <= chunk_length_ms:
        transcript = process_audio_chunk(audio, language_code)
        return transcript.strip()
    else:
        # Split audio into chunks.
        chunks = [
            audio[i : i + chunk_length_ms]
            for i in range(0, len(audio), chunk_length_ms)
        ]
        transcript_chunks = ["" for _ in range(len(chunks))]

        # Process each chunk concurrently.
        with ThreadPoolExecutor(max_workers=len(chunks)) as executor:
            future_to_index = {
                executor.submit(process_audio_chunk, chunk, language_code): idx
                for idx, chunk in enumerate(chunks)
            }
            for future in as_completed(future_to_index):
                idx = future_to_index[future]
                try:
                    transcript_chunks[idx] = future.result().strip()
                except Exception as e:
                    logger.error(f"Error processing chunk {idx}: {e}")
                    transcript_chunks[idx] = ""
        full_transcript = " ".join(transcript_chunks)
        # Replace any occurrence of multiple whitespace characters with a single space
        clean_transcript = re.sub(r"\s+", " ", full_transcript).strip()
        return clean_transcript


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
        error_message = f"Daily voice recording limit reached ({voice_limit}). "
        if user.tier == "anonymous":
            error_message += (
                'Log in for higher limits <a href="#" class="underline" '
                'onclick="showAuthModal(); return false;">here</a>.'
            )
        else:
            error_message += (
                'If you need a higher limit, let me know in the <a href="#" class="underline" '
                'onclick="showFeedbackModal(); return false;">feedback</a>.'
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
        if (
            not user.last_voice_transcription
            or user.last_voice_transcription < today_start
        ):
            user.daily_voice_count = 1
        else:
            user.daily_voice_count += 1
        user.last_voice_transcription = datetime.now(UTC)
        db.session.commit()

        # Get the current language and question
        language = session.get("language", SETTINGS.DEFAULT_LANGUAGE)
        question_text = request.args.get("question", "")
        logger.debug(f"Using language: {language}, Question: {question_text}")

        # Process the initial transcription
        logger.debug("Starting initial transcription")
        transcript = transcribe_audio(audio_file.read(), audio_file.content_type)

        # Return early if transcription failed
        if not transcript:
            logger.error("Initial transcription failed")
            return jsonify({"error": "Error during transcription"}), 500

        logger.debug("Initial transcription successful, starting post-processing")
        # Post-process the transcription with LLM, including the question context
        improved_transcript = post_process_transcription(
            transcript, language, question_text
        )
        logger.debug("Post-processing complete")

        was_improved = improved_transcript != transcript
        logger.debug(f"Transcription was improved: {was_improved}")

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
