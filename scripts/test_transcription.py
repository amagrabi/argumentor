import argparse
import mimetypes
import os

from flask import Flask, session

from src.routes.transcribe import SETTINGS, transcribe_audio


def guess_mime_type(file_path):
    """Return a MIME type based on the file extension. Default to 'audio/wav' if unknown."""
    mime_type, _ = mimetypes.guess_type(file_path)
    if mime_type:
        return mime_type
    return "audio/wav"


def main():
    parser = argparse.ArgumentParser(
        description="Test audio transcription with different Google Speech-to-Text models."
    )
    parser.add_argument(
        "--files",
        nargs="+",
        required=True,
        help="List of paths to audio files (e.g., /path/to/audio.wav /path/to/audio.webm).",
    )
    parser.add_argument(
        "--models",
        nargs="+",
        default=["default", "telephony"],
        help="List of Google Speech-to-Text models to test (e.g., default telephony).",
    )
    parser.add_argument(
        "--languages",
        nargs="+",
        default=[],
        help="List of target languages corresponding to each file (e.g., --languages en de means the first file uses English and the second German). If fewer languages than files are provided, the remaining files will use the default language.",
    )
    parser.add_argument(
        "--enhanced",
        action=argparse.BooleanOptionalAction,
        default=SETTINGS.VOICE_ENHANCED,
        help="Enable or disable enhanced speech transcription.",
    )
    args = parser.parse_args()

    # Save the original settings so they can be restored later.
    original_model = SETTINGS.VOICE_MODEL
    original_enhanced = SETTINGS.VOICE_ENHANCED

    # Update the enhanced flag according to the command-line argument.
    SETTINGS.VOICE_ENHANCED = args.enhanced

    # Create a minimal Flask app for a request context; transcribe_audio uses session.
    app = Flask(__name__)
    app.secret_key = "test_secret_key"

    with app.test_request_context():
        # Set a default language in the session (if not already set).
        session["language"] = getattr(SETTINGS, "DEFAULT_LANGUAGE", "en")

        # Print an indicator at the top regarding the enhanced setting.
        print(
            f"Enhanced Speech Transcription: {'Enabled' if SETTINGS.VOICE_ENHANCED else 'Disabled'}"
        )

        for model in args.models:
            # Update the voice model configuration for this test run.
            SETTINGS.VOICE_MODEL = model
            print(f"\n--- Testing with model: {model} ---")
            for idx, file_path in enumerate(args.files):
                if not os.path.exists(file_path):
                    print(f"File not found: {file_path}")
                    continue

                # Determine target language for this file.
                target_language = (
                    args.languages[idx]
                    if idx < len(args.languages)
                    else getattr(SETTINGS, "DEFAULT_LANGUAGE", "en")
                )
                session["language"] = target_language

                mime_type = guess_mime_type(file_path)
                with open(file_path, "rb") as audio_file:
                    audio_content = audio_file.read()

                print(
                    f"\nTranscribing file: {file_path} (MIME type: {mime_type}) using language: {target_language}"
                )
                transcript = transcribe_audio(audio_content, mime_type)
                print("Transcription:")
                print(transcript)

    # Restore the original configuration.
    SETTINGS.VOICE_MODEL = original_model
    SETTINGS.VOICE_ENHANCED = original_enhanced


if __name__ == "__main__":
    # python -m scripts.test_transcription \
    # --files ~/Downloads/test1.webm \
    # --languages de \
    # --enhanced \
    # --models default telephony latest_long
    main()
