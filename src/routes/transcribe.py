import logging
import uuid

from flask import Blueprint, jsonify, request, session
from google.cloud import speech, storage

from config import get_settings

logger = logging.getLogger(__name__)
transcribe_bp = Blueprint("transcribe", __name__)
SETTINGS = get_settings()


def upload_audio_to_gcs(audio_content, file_mime):
    # Initialize a GCS client
    storage_client = storage.Client()
    # The bucket name should be configured in your settings (or set a default)
    bucket_name = SETTINGS.GCS_BUCKET
    bucket = storage_client.bucket(bucket_name)
    extension = "webm" if "webm" in file_mime or "ogg" in file_mime else "wav"
    filename = f"voice_recordings/{uuid.uuid4()}.{extension}"
    blob = bucket.blob(filename)
    blob.upload_from_string(audio_content, content_type=file_mime)
    logger.debug(f"Uploaded audio file to GCS: gs://{bucket_name}/{filename}")
    return f"gs://{bucket_name}/{filename}"


def transcribe_audio(audio_content, file_mime, delete_after_transcription=True):
    # Upload the audio to GCS and get its URI
    gcs_uri = upload_audio_to_gcs(audio_content, file_mime)

    client = speech.SpeechClient()
    logger.debug(f"Using GCS URI for transcription: {gcs_uri}")

    current_language = session.get("language", SETTINGS.DEFAULT_LANGUAGE)
    language_code = getattr(SETTINGS, "LANGUAGE_CODES", {}).get(
        current_language, "en-US"
    )

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

    logger.debug(f"Transcription config: {config}")

    audio = speech.RecognitionAudio(uri=gcs_uri)
    transcript = ""
    try:
        # Use long_running_recognize for longer recordings (up to 3 minutes)
        operation = client.long_running_recognize(config=config, audio=audio)
        response = operation.result(timeout=180)

        for result in response.results:
            transcript += result.alternatives[0].transcript + " "
    except Exception as e:
        logger.error(f"Transcription error: {str(e)}")
        transcript = ""
    finally:
        if delete_after_transcription:
            try:
                storage_client = storage.Client()
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
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    file = request.files["file"]
    audio_content = file.read()
    logger.debug(f"File MIME type received: {file.mimetype}")
    transcript = transcribe_audio(audio_content, file.mimetype)
    return jsonify({"transcript": transcript})
