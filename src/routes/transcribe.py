import logging
import re
import uuid
from datetime import UTC, datetime, time

from flask import Blueprint, jsonify, request, session
from google.cloud import speech, storage

from config import get_settings
from extensions import db, google_credentials
from models import User
from utils import get_daily_voice_count, get_voice_limit

logger = logging.getLogger(__name__)
transcribe_bp = Blueprint("transcribe", __name__)
SETTINGS = get_settings()


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
        return jsonify(
            {
                "error": (
                    f"Daily voice recording limit reached ({voice_limit}). "
                    'If you need a higher limit, send me <a href="#" class="underline" onclick="showFeedbackModal(); return false;">feedback</a>.'
                )
            }
        ), 429

    # Get the audio file from the request
    if "file" not in request.files:
        return jsonify({"error": "No audio file provided"}), 400

    audio_file = request.files["file"]
    if not audio_file:
        return jsonify({"error": "No audio file provided"}), 400

    try:
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

        # Process the transcription
        transcript = transcribe_audio(audio_file.read(), audio_file.content_type)
        return jsonify({"transcript": transcript})
    except Exception as e:
        logger.error(f"Error in voice transcription: {str(e)}")
        db.session.rollback()
        return jsonify({"error": "Error processing voice recording"}), 500
