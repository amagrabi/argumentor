import gc
import importlib.util
import logging
import os
import sys
import time
import tracemalloc

from pympler import muppy, summary, tracker

# Add the project root to the path so we can import modules properly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from flask import Flask, session

from config import get_settings
from src.routes.transcribe import transcribe_audio

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create a Flask app for testing
app = Flask(__name__)
app.config["TESTING"] = True
app.secret_key = "test_secret_key"
SETTINGS = get_settings()


def print_top_objects(top=20):
    """Print the top memory-consuming objects"""
    all_objects = muppy.get_objects()
    sum_obj = summary.summarize(all_objects)
    summary.print_(sum_obj, limit=top)


def profile_memory_usage(audio_file_path, content_type="audio/wav"):
    """Profile memory usage during transcription and identify potential leaks"""
    # Start tracemalloc
    tracemalloc.start()

    # Create a memory tracker
    tr = tracker.SummaryTracker()

    logger.info("Starting memory profiling...")
    logger.info("Initial memory snapshot:")
    print_top_objects()

    # Force garbage collection before starting
    gc.collect(2)

    # Take initial snapshot
    snapshot1 = tracemalloc.take_snapshot()

    # Read the audio file
    with open(audio_file_path, "rb") as f:
        audio_content = f.read()

    logger.info("\nMemory after loading audio:")
    tr.print_diff()

    # Create a Flask request context for testing
    with app.test_request_context():
        # Set session variables that might be needed
        session["language"] = SETTINGS.DEFAULT_LANGUAGE
        session["user_id"] = "test_user"

        # Perform transcription
        logger.info("\nStarting transcription...")
        transcript = transcribe_audio(audio_content, content_type)
        logger.info(f"Transcription result: {transcript}")

    logger.info("\nMemory after transcription:")
    tr.print_diff()

    # Delete audio content and force garbage collection
    del audio_content
    gc.collect(2)

    # Wait a bit to allow garbage collection to complete
    time.sleep(2)

    logger.info("\nMemory after cleanup:")
    tr.print_diff()

    # Take final snapshot
    snapshot2 = tracemalloc.take_snapshot()

    # Compare snapshots
    logger.info("\nTop memory differences:")
    top_stats = snapshot2.compare_to(snapshot1, "lineno")
    for stat in top_stats[:20]:
        logger.info(stat)

    # Final garbage collection
    gc.collect(2)
    time.sleep(2)

    logger.info("\nFinal memory state:")
    print_top_objects()

    # Stop tracemalloc
    tracemalloc.stop()


if __name__ == "__main__":
    # Install required packages if not already installed
    try:
        if importlib.util.find_spec("pympler") is None:
            logger.error("Pympler package not found. Please install it with:")
            logger.error("pip install pympler")
            exit(1)
        if importlib.util.find_spec("tracemalloc") is None:
            logger.error("tracemalloc module not available in this Python build")
            exit(1)
    except ImportError:
        logger.error("Required packages not found. Please install them with:")
        logger.error("pip install pympler")
        exit(1)

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

    # Run the profiling
    logger.info(f"Profiling with audio file: {audio_file_path}")
    profile_memory_usage(audio_file_path, content_type)

    logger.info("\n--- MEMORY PROFILING COMPLETE ---")
    logger.info("Check the output above to identify potential memory leaks")
    logger.info("Look for objects that persist after cleanup")
