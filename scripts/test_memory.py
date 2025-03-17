import gc
import logging
import os
import sys
import time

# Add immediate print for debugging
print("Script starting...")

# Add the project root to the path so we can import modules properly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
print(f"Python path: {sys.path}")

try:
    import psutil

    print("psutil imported successfully")
except ImportError as e:
    print(f"Error importing psutil: {e}")
    print("Please install psutil with: pip install psutil")
    sys.exit(1)

try:
    from flask import Flask, session

    from config import get_settings

    print("Flask and config imported successfully")
except ImportError as e:
    print(f"Error importing Flask or config: {e}")
    sys.exit(1)

try:
    from src.routes.transcribe import transcribe_audio

    print("transcribe_audio imported successfully")
except ImportError as e:
    print(f"Error importing transcribe_audio: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)

# Configure logging - make sure we see all levels
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Add a console handler to ensure output is visible
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
logger.addHandler(console_handler)

logger.info("Logger initialized")

# Create a Flask app for testing
app = Flask(__name__)
app.config["TESTING"] = True
app.secret_key = "test_secret_key"

try:
    SETTINGS = get_settings()
    logger.info("Settings loaded successfully")
except Exception as e:
    logger.error(f"Error loading settings: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)


def get_memory_usage():
    """Get current memory usage of the process in MB"""
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    return memory_info.rss / 1024 / 1024  # Convert to MB


def test_transcription_memory(audio_file_path, content_type="audio/webm"):
    """Test memory usage before, during, and after transcription"""
    # Force garbage collection before starting
    gc.collect(2)

    # Record initial memory usage
    initial_memory = get_memory_usage()
    logger.info(f"Initial memory usage: {initial_memory:.2f} MB")

    # Read the audio file
    with open(audio_file_path, "rb") as f:
        audio_content = f.read()

    # Record memory after loading audio
    after_load_memory = get_memory_usage()
    logger.info(
        f"Memory after loading audio: {after_load_memory:.2f} MB (Δ: {after_load_memory - initial_memory:.2f} MB)"
    )

    # Create a Flask request context for testing
    with app.test_request_context():
        # Set session variables that might be needed
        session["language"] = SETTINGS.DEFAULT_LANGUAGE
        session["user_id"] = "test_user"

        # Perform transcription
        logger.info("Starting transcription...")
        transcript = transcribe_audio(audio_content, content_type)
        logger.info(f"Transcription result: {transcript}")

    # Record memory after transcription
    after_transcription_memory = get_memory_usage()
    logger.info(
        f"Memory after transcription: {after_transcription_memory:.2f} MB (Δ: {after_transcription_memory - after_load_memory:.2f} MB)"
    )

    # Delete audio content and force garbage collection
    del audio_content
    gc.collect(2)

    # Wait a bit to allow garbage collection to complete
    time.sleep(2)

    # Record memory after cleanup
    after_cleanup_memory = get_memory_usage()
    logger.info(
        f"Memory after cleanup: {after_cleanup_memory:.2f} MB (Δ: {after_cleanup_memory - after_transcription_memory:.2f} MB)"
    )

    # Final garbage collection
    gc.collect(2)
    time.sleep(2)

    # Record final memory
    final_memory = get_memory_usage()
    logger.info(f"Final memory usage: {final_memory:.2f} MB")
    logger.info(f"Memory difference from start: {final_memory - initial_memory:.2f} MB")

    return {
        "initial_memory": initial_memory,
        "after_load_memory": after_load_memory,
        "after_transcription_memory": after_transcription_memory,
        "after_cleanup_memory": after_cleanup_memory,
        "final_memory": final_memory,
        "memory_leak": final_memory - initial_memory,
    }


if __name__ == "__main__":
    # Default test audio file path
    audio_file_path = "tmp/test_audio.wav"
    content_type = "audio/wav"

    # Check if file exists
    if not os.path.exists(audio_file_path):
        logger.warning(f"Test audio file not found: {audio_file_path}")
        logger.info("Generating a test audio file...")

        try:
            # Try to import and use the generate_test_audio function
            from generate_test_audio import generate_test_audio

            os.makedirs("test_data", exist_ok=True)
            audio_file_path = generate_test_audio("tmp/test_audio.wav")
        except ImportError:
            logger.error(
                "Could not import generate_test_audio. Please run scripts/generate_test_audio.py first."
            )
            exit(1)

    # Run the test
    logger.info(f"Testing with audio file: {audio_file_path}")
    results = test_transcription_memory(audio_file_path, content_type)

    # Print summary
    logger.info("\n--- MEMORY TEST SUMMARY ---")
    logger.info(f"Initial memory: {results['initial_memory']:.2f} MB")
    logger.info(f"Peak memory: {results['after_transcription_memory']:.2f} MB")
    logger.info(f"Final memory: {results['final_memory']:.2f} MB")
    logger.info(f"Memory not reclaimed: {results['memory_leak']:.2f} MB")

    # Run multiple tests to see if memory keeps increasing
    logger.info("\n--- RUNNING MULTIPLE TESTS ---")
    for i in range(3):
        logger.info(f"\nTest run #{i + 1}")
        results = test_transcription_memory(audio_file_path, content_type)
        time.sleep(5)  # Wait between tests
