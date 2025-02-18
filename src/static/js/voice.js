import { CHAR_LIMITS } from "./constants.js";

// HTML elements for voice recording
const recordButton = document.getElementById("recordButton"); // Button to start recording
const stopButton = document.getElementById("stopButton"); // Button for manual stop (optional)
const transcriptField = document.getElementById("voiceTranscript"); // Textarea to display transcript
const recordingStatus = document.getElementById("recordingStatus");
const voiceCount = document.getElementById("voiceCount");

let mediaRecorder;
let audioChunks = [];
let recordingTimeout;

// Use the constant instead of hardcoded value
const MAX_VOICE_LENGTH = CHAR_LIMITS.VOICE;

recordButton.addEventListener("click", async () => {
  recordButton.disabled = true;
  stopButton.disabled = false;
  recordingStatus.textContent = "Recording...";

  // Request access to the user's microphone
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  mediaRecorder = new MediaRecorder(stream, {
    mimeType: "audio/webm;codecs=opus",
    bitsPerSecond: 128000,
  });
  audioChunks = [];

  console.log("MediaRecorder MIME Type:", mediaRecorder.mimeType);

  mediaRecorder.addEventListener("dataavailable", (event) => {
    audioChunks.push(event.data);
  });

  mediaRecorder.addEventListener("stop", async () => {
    recordingStatus.textContent = "Transcribing...";
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
      recordingStatus.textContent =
        "Transcription complete. You may edit the text.";
    } catch (error) {
      recordingStatus.textContent = "Error during transcription.";
      console.error(error);
    }
    recordButton.disabled = false;
    stopButton.disabled = true;
  });

  mediaRecorder.start();
  // Automatically stop recording after 3 minutes (180000 ms)
  recordingTimeout = setTimeout(() => {
    if (mediaRecorder && mediaRecorder.state !== "inactive") {
      mediaRecorder.stop();
    }
  }, 180000);
});

stopButton.addEventListener("click", () => {
  clearTimeout(recordingTimeout);
  if (mediaRecorder && mediaRecorder.state !== "inactive") {
    mediaRecorder.stop();
  }
  recordButton.disabled = false;
  stopButton.disabled = true;
});

// Update remaining character count as user edits
transcriptField.addEventListener("input", () => {
  const remaining = MAX_VOICE_LENGTH - transcriptField.value.length;
  voiceCount.textContent = remaining.toString();
});

// Toggle Input Mode functionality
const toggleInputModeButton = document.getElementById("toggleInputMode");
const textInputSection = document.getElementById("textInputSection"); // container for text inputs
const voiceInputSection = document.getElementById("voiceInputSection");

let currentInputMode = "text"; // default mode

toggleInputModeButton.addEventListener("click", () => {
  if (currentInputMode === "text") {
    currentInputMode = "voice";
    toggleInputModeButton.textContent = "Switch to Text Input";
    textInputSection.style.display = "none";
    voiceInputSection.style.display = "block";
  } else {
    currentInputMode = "text";
    toggleInputModeButton.textContent = "Switch to Voice Input";
    voiceInputSection.style.display = "none";
    textInputSection.style.display = "block";
  }
});

// Expose currentInputMode globally for submission logic
window.currentInputMode = () => currentInputMode;
