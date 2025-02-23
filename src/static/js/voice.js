import { CHAR_LIMITS, VOICE_LIMITS, DEFAULT_LANGUAGE } from "./constants.js";
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

// Function to format max recording time as MM:SS
function formatMaxRecordingTime() {
  const ms = VOICE_LIMITS.MAX_RECORDING_TIME;
  return formatTime(ms);
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
      // Immediately update the UI to reflect that recording has stopped.
      stopRecording();

      // Now update the status to indicate that transcription is starting.
      recordingStatus.innerHTML =
        (translations?.main?.voiceInput?.status?.transcribing ||
          "Transcribing...") + '<span class="spinner"></span>';

      const audioBlob = new Blob(audioChunks, {
        type: "audio/webm",
      });
      const formData = new FormData();
      formData.append("file", audioBlob, "recording");

      // Get the current language from local storage (or fallback to "en")
      const language = localStorage.getItem("language") || "en";

      // Get the current question from session storage
      const currentQuestion = JSON.parse(
        sessionStorage.getItem("currentQuestion")
      );
      const questionText = currentQuestion ? currentQuestion.description : "";

      try {
        // Set longer timeout for fetch
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 120000); // 2 minutes

        const response = await fetch(
          `/transcribe_voice?lang=${language}&question=${encodeURIComponent(
            questionText
          )}`,
          {
            method: "POST",
            body: formData,
            signal: controller.signal,
          }
        );

        clearTimeout(timeoutId);

        const data = await response.json();

        if (!response.ok) {
          recordingStatus.innerHTML =
            data.error ||
            translations?.main?.voiceInput?.status?.transcriptionError ||
            "Error during transcription.";
          recordButton.disabled = false;
          return;
        }

        // Show post-processing status
        recordingStatus.innerHTML =
          (translations?.main?.voiceInput?.status?.postProcessing ||
            "Post-processing...") + '<span class="spinner"></span>';

        let transcript = data.transcript || "";

        // Update status based on whether the transcription was improved
        recordingStatus.innerHTML = data.was_improved
          ? translations?.main?.voiceInput?.status?.transcriptionImproved ||
            "Transcription complete and enhanced. You may edit the text."
          : translations?.main?.voiceInput?.status?.transcriptionComplete ||
            "Transcription complete. You may edit the text.";

        transcriptField.value = transcript;
        voiceCount.textContent = (
          VOICE_LIMITS.MAX_CHARS - transcript.length
        ).toString();

        // If the transcript exceeds the character limit, highlight it.
        if (transcript.length > VOICE_LIMITS.MAX_CHARS) {
          transcriptField.classList.add("border-red-500");
          recordingStatus.innerHTML =
            translations?.main?.voiceInput?.status?.tooLong ||
            "Transcription exceeds character limit. Please edit before submitting.";
        } else {
          transcriptField.classList.remove("border-red-500");
        }
      } catch (error) {
        if (error.name === "AbortError") {
          recordingStatus.innerHTML =
            translations?.main?.voiceInput?.status?.transcriptionTimeout ||
            "Transcription timed out. Please try a shorter recording.";
        } else {
          recordingStatus.innerHTML =
            translations?.main?.voiceInput?.status?.transcriptionError ||
            "Error during transcription.";
        }
        console.error(error);
        recordButton.disabled = false;
      }
      // Re-enable the record button once transcription is complete.
      recordButton.disabled = false;
    });

    mediaRecorder.start();
    // Automatically stop recording after MAX_RECORDING_TIME
    recordingTimeout = setTimeout(() => {
      if (mediaRecorder && mediaRecorder.state !== "inactive") {
        mediaRecorder.stop();
      }
    }, VOICE_LIMITS.MAX_RECORDING_TIME);

    // Update max recording time display
    document.getElementById("maxRecordingTime").textContent =
      formatMaxRecordingTime();
  } catch (error) {
    console.error("Error accessing microphone:", error);
    recordingStatus.innerHTML =
      translations?.main?.voiceInput?.status?.microphoneError ||
      "Error accessing microphone.";
  }
}

function stopRecording() {
  // If the recorder is still active, stop it.
  if (mediaRecorder && mediaRecorder.state !== "inactive") {
    mediaRecorder.stop();
  }
  // Always perform the UI reset.
  isRecording = false;
  clearInterval(timerInterval);
  recordingTimer.classList.add("hidden");
  recordButton.classList.remove("bg-red-50", "border-red-500", "text-red-500");
  recordButton.innerHTML = `<svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
      d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"/>
  </svg>`;
}

// Update remaining character count as user edits
transcriptField.addEventListener("input", () => {
  const remaining = MAX_VOICE_LENGTH - transcriptField.value.length;
  voiceCount.textContent = remaining.toString();
  // Clear error message on input
  document.getElementById("errorMessage").textContent = "";
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
