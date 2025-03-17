import logging
import os
import wave

import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def generate_test_audio(output_path, duration_seconds=5, sample_rate=16000):
    """Generate a simple test audio file with a sine wave"""
    # Create a sine wave
    t = np.linspace(0, duration_seconds, int(duration_seconds * sample_rate), False)
    tone = np.sin(2 * np.pi * 440 * t)  # 440 Hz tone

    # Normalize to 16-bit range
    audio = (tone * 32767).astype(np.int16)

    # Create WAV file
    with wave.open(output_path, "w") as wf:
        wf.setnchannels(1)  # Mono
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes(audio.tobytes())

    logger.info(f"Generated test audio file: {output_path}")
    logger.info(f"Duration: {duration_seconds} seconds, Sample rate: {sample_rate} Hz")

    return output_path


if __name__ == "__main__":
    # Create output directory if it doesn't exist
    os.makedirs("test_data", exist_ok=True)

    # Generate test audio file
    output_path = "tmp/test_audio.wav"
    generate_test_audio(output_path)

    logger.info(f"Test audio file created at: {output_path}")
    logger.info("You can use this file for memory testing with scripts/test_memory.py")
