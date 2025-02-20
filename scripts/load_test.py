import asyncio
import time
from pathlib import Path

import aiohttp


async def send_transcription_request(session, audio_file_path):
    # Read file content
    with open(audio_file_path, "rb") as f:
        file_data = f.read()

    # Create form data
    form = aiohttp.FormData()
    form.add_field("file", file_data, filename="test.webm", content_type="audio/webm")

    start = time.time()
    try:
        async with session.post(
            "http://localhost:8000/transcribe_voice", data=form
        ) as response:
            duration = time.time() - start
            return response.status, duration
    except Exception as e:
        print(f"Error during request: {e}")
        return 500, time.time() - start


async def main():
    # Ensure test file exists
    audio_path = Path("test_audio.webm")
    if not audio_path.exists():
        print(f"Error: Test file {audio_path} not found")
        return

    print("Starting load test with 4 concurrent requests...")
    async with aiohttp.ClientSession() as session:
        tasks = []
        for i in range(4):
            tasks.append(send_transcription_request(session, audio_path))

        results = await asyncio.gather(*tasks)

        for i, (status, duration) in enumerate(results, 1):
            print(f"Request {i}: Status={status}, Duration={duration:.2f}s")


if __name__ == "__main__":
    asyncio.run(main())
