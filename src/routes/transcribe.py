import logging
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


def transcribe_audio(audio_content, file_mime, delete_after_transcription=False):
    # Upload the audio to GCS and get its URI
    gcs_uri = upload_audio_to_gcs(audio_content, file_mime)

    # Initialize speech client with our credentials
    client = speech.SpeechClient(credentials=google_credentials)

    current_language = session.get("language", SETTINGS.DEFAULT_LANGUAGE)
    language_code = getattr(SETTINGS, "LANGUAGE_CODES", {}).get(
        current_language, "en-US"
    )

    # Add debug logging
    logger.debug(f"Current language: {current_language}")
    logger.debug(f"Using language code for speech recognition: {language_code}")

    # Configure encoding and sample rate based on file mime type
    if "webm" in file_mime or "ogg" in file_mime:
        encoding = speech.RecognitionConfig.AudioEncoding.WEBM_OPUS
        sample_rate_hertz = 48000
    else:
        encoding = speech.RecognitionConfig.AudioEncoding.LINEAR16
        sample_rate_hertz = 16000

    config = speech.RecognitionConfig(
        encoding=encoding,
        sample_rate_hertz=sample_rate_hertz,
        language_code=language_code,
        model=SETTINGS.VOICE_MODEL,
        use_enhanced=SETTINGS.VOICE_ENHANCED,
        enable_automatic_punctuation=SETTINGS.VOICE_PUNCTUATION,
        audio_channel_count=1,
        # enable_word_confidence=True,
        # enable_word_time_offsets=True,
    )

    # logger.debug(f"Transcription config: {config}")

    audio = speech.RecognitionAudio(uri=gcs_uri)
    transcript = ""
    try:
        # Use long_running_recognize for longer recordings
        operation = client.long_running_recognize(config=config, audio=audio)
        response = operation.result(timeout=120)

        for result in response.results:
            transcript += result.alternatives[0].transcript + " "
    except Exception as e:
        logger.error(f"Transcription error: {str(e)}")
        transcript = ""
    finally:
        if delete_after_transcription:
            try:
                storage_client = storage.Client(credentials=google_credentials)
                bucket_name = SETTINGS.GCS_BUCKET
                bucket = storage_client.bucket(bucket_name)
                # Extract the filename from the uri
                file_path = gcs_uri.replace(f"gs://{bucket_name}/", "")
                blob = bucket.blob(file_path)
                blob.delete()
                logger.debug(f"Deleted temporary audio file from GCS: {gcs_uri}")
            except Exception as delete_error:
                logger.error(
                    f"Error deleting temporary audio file from GCS: {delete_error}"
                )
    return transcript.strip()


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
