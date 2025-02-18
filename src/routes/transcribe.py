import logging

from flask import Blueprint, jsonify, request, session
from google.cloud import speech

from config import get_settings

logger = logging.getLogger(__name__)
transcribe_bp = Blueprint("transcribe", __name__)
SETTINGS = get_settings()


def transcribe_audio(audio_content, file_mime):
    client = speech.SpeechClient()
    audio = speech.RecognitionAudio(content=audio_content)
    logger.debug(f"Received audio content of {len(audio_content)} bytes")

    # Get current language from session
    current_language = session.get("language", SETTINGS.DEFAULT_LANGUAGE)

    language_code = SETTINGS.LANGUAGE_CODES.get(current_language, "en-US")
    logger.debug(f"Using language code: {language_code}")

    # Use WEBM_OPUS for WebM audio (WebM typically contains Opus-encoded audio)
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
        model="default",
        audio_channel_count=1,
        enable_word_confidence=True,
        enable_word_time_offsets=True,
    )

    try:
        # Use long_running_recognize for longer recordings
        operation = client.long_running_recognize(config=config, audio=audio)
        response = operation.result(timeout=180)

        transcript = ""
        for result in response.results:
            transcript += result.alternatives[0].transcript + " "
        return transcript.strip()
    except Exception as e:
        logger.error(f"Transcription error: {str(e)}")
        return ""


@transcribe_bp.route("/transcribe_voice", methods=["POST"])
def transcribe_voice():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    file = request.files["file"]
    audio_content = file.read()
    logger.debug(f"File MIME type received: {file.mimetype}")
    transcript = transcribe_audio(audio_content, file.mimetype)
    return jsonify({"transcript": transcript})
