import { CHAR_LIMITS } from "./constants.js";
import { translations } from "./translations.js";

// HTML elements for voice recording
const textModeTab = document.getElementById("textModeTab");
const voiceModeTab = document.getElementById("voiceModeTab");
const textInputSection = document.getElementById("textInputSection");
const voiceInputSection = document.getElementById("voiceInputSection");
const recordButton = document.getElementById("recordButton");
const recordingTimer = document.getElementById("recordingTimer");
const timerDisplay = document.getElementById("timerDisplay");
const recordingStatus = document.getElementById("recordingStatus");
const transcriptField = document.getElementById("voiceTranscript"); // Textarea to display transcript
const voiceCount = document.getElementById("voiceCount");

let mediaRecorder;
let audioChunks = [];
let recordingTimeout;
let isRecording = false;
let timerInterval;
let startTime;

// Use the constant instead of hardcoded value
const MAX_VOICE_LENGTH = CHAR_LIMITS.VOICE;

// Function to format time as MM:SS
function formatTime(ms) {
  const seconds = Math.floor(ms / 1000);
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes}:${remainingSeconds.toString().padStart(2, "0")}`;
}

// Function to update timer display
function updateTimer() {
  const elapsed = Date.now() - startTime;
  timerDisplay.textContent = formatTime(elapsed);
}

// Function to toggle recording state
function toggleRecording() {
  if (!isRecording) {
    startRecording();
  } else {
    stopRecording();
  }
}

// Update the recording functions
async function startRecording() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream, {
      mimeType: "audio/webm;codecs=opus",
      bitsPerSecond: 128000,
    });

    isRecording = true;
    recordButton.classList.add("bg-red-50", "border-red-500", "text-red-500");
    recordButton.innerHTML = `
      <svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <rect x="6" y="6" width="12" height="12" rx="2" />
      </svg>
    `;

    recordingStatus.textContent =
      translations?.main?.voiceInput?.status?.recording || "Recording...";
    recordingTimer.classList.remove("hidden");
    startTime = Date.now();
    timerInterval = setInterval(updateTimer, 1000);

    audioChunks = [];
    mediaRecorder.addEventListener("dataavailable", (event) => {
      audioChunks.push(event.data);
    });

    mediaRecorder.addEventListener("stop", async () => {
      recordingStatus.innerHTML =
        (translations?.main?.voiceInput?.status?.transcribing ||
          "Transcribing...") + '<span class="loading-dots"></span>';
      const audioBlob = new Blob(audioChunks, {
        type: "audio/webm",
      });
      const formData = new FormData();
      formData.append("file", audioBlob, "recording");

      try {
        const response = await fetch("/transcribe_voice", {
          method: "POST",
          body: formData,
        });
        const data = await response.json();
        let transcript = data.transcript || "";

        // Truncate if exceeds maximum length
        if (transcript.length > MAX_VOICE_LENGTH) {
          transcript = transcript.substring(0, MAX_VOICE_LENGTH);
        }

        transcriptField.value = transcript;
        voiceCount.textContent = (
          MAX_VOICE_LENGTH - transcript.length
        ).toString();
        recordingStatus.innerHTML =
          translations?.main?.voiceInput?.status?.transcriptionComplete ||
          "Transcription complete. You may edit the text.";
      } catch (error) {
        recordingStatus.innerHTML =
          translations?.main?.voiceInput?.status?.transcriptionError ||
          "Error during transcription.";
        console.error(error);
      }
      recordButton.disabled = false;
      stopRecording();
    });

    mediaRecorder.start();
    // Automatically stop recording after 3 minutes (180000 ms)
    recordingTimeout = setTimeout(() => {
      if (mediaRecorder && mediaRecorder.state !== "inactive") {
        mediaRecorder.stop();
      }
    }, 180000);
  } catch (error) {
    console.error("Error accessing microphone:", error);
    recordingStatus.innerHTML =
      translations?.main?.voiceInput?.status?.microphoneError ||
      "Error accessing microphone.";
  }
}

function stopRecording() {
  if (mediaRecorder && mediaRecorder.state !== "inactive") {
    isRecording = false;
    mediaRecorder.stop();
    clearInterval(timerInterval);
    recordingTimer.classList.add("hidden");
    recordButton.classList.remove(
      "bg-red-50",
      "border-red-500",
      "text-red-500"
    );
    recordButton.innerHTML = `
      <svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"/>
      </svg>
    `;
  }
}

// Update remaining character count as user edits
transcriptField.addEventListener("input", () => {
  const remaining = MAX_VOICE_LENGTH - transcriptField.value.length;
  voiceCount.textContent = remaining.toString();
});

// Update the tab switching logic
textModeTab.addEventListener("click", () => {
  textModeTab.classList.add("active", "text-gray-800");
  textModeTab.classList.remove("text-gray-500");
  voiceModeTab.classList.remove("active", "text-gray-800");
  voiceModeTab.classList.add("text-gray-500");
  textInputSection.style.display = "block";
  voiceInputSection.style.display = "none";
  window.currentInputMode = "text";
});

voiceModeTab.addEventListener("click", () => {
  voiceModeTab.classList.add("active", "text-gray-800");
  voiceModeTab.classList.remove("text-gray-500");
  textModeTab.classList.remove("active", "text-gray-800");
  textModeTab.classList.add("text-gray-500");
  voiceInputSection.style.display = "block";
  textInputSection.style.display = "none";
  window.currentInputMode = "voice";
});

// Update the record button click handler
recordButton.addEventListener("click", toggleRecording);
