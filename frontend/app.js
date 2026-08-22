const recordButton = document.getElementById("recordButton");
const recordingIndicator = document.getElementById("recordingIndicator");
const loadingIndicator = document.getElementById("loadingIndicator");
const errorMessage = document.getElementById("errorMessage");
const transcriptionField = document.getElementById("transcription");

let mediaRecorder = null;
let mediaStream = null;
let audioChunks = [];
let isRecording = false;

function setError(message) {
  if (!message) {
    errorMessage.textContent = "";
    errorMessage.classList.add("hidden");
    return;
  }

  errorMessage.textContent = message;
  errorMessage.classList.remove("hidden");
}

function setLoading(isLoading) {
  loadingIndicator.classList.toggle("hidden", !isLoading);
  recordButton.disabled = isLoading;
}

function setRecordingUI(recording) {
  isRecording = recording;
  recordButton.textContent = recording ? "Stop Listening" : "Start Listening";
  recordButton.classList.toggle("recording", recording);
  recordingIndicator.classList.toggle("hidden", !recording);
}

async function uploadAudio(blob) {
  const formData = new FormData();
  formData.append("audio_file", blob, "recording.webm");

  setLoading(true);

  try {
    const response = await fetch("/api/transcribe/", {
      method: "POST",
      body: formData,
    });

    const rawBody = await response.text();
    let data = null;

    try {
      data = rawBody ? JSON.parse(rawBody) : null;
    } catch {
      data = null;
    }

    if (!response.ok) {
      if (response.status === 504) {
        throw new Error(
          "The server is still preparing Whisper. Please try again shortly."
        );
      }

      throw new Error(
        (data && data.error) ||
          `Transcription failed (HTTP ${response.status}).`
      );
    }

    transcriptionField.value = (data && data.text) || "";
  } catch (error) {
    setError(error.message || "Transcription failed.");
  } finally {
    setLoading(false);
  }
}

function stopAndReleaseStream() {
  if (mediaStream) {
    mediaStream.getTracks().forEach((track) => track.stop());
    mediaStream = null;
  }
}

async function startRecording() {
  setError("");

  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    setError("Your browser does not support microphone recording.");
    return;
  }

  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    audioChunks = [];

    mediaRecorder = new MediaRecorder(mediaStream);

    mediaRecorder.addEventListener("dataavailable", (event) => {
      if (event.data && event.data.size > 0) {
        audioChunks.push(event.data);
      }
    });

    mediaRecorder.addEventListener("stop", async () => {
      const mimeType = mediaRecorder.mimeType || "audio/webm";
      const audioBlob = new Blob(audioChunks, { type: mimeType });
      stopAndReleaseStream();

      if (audioBlob.size === 0) {
        setError("No audio was recorded.");
        return;
      }

      await uploadAudio(audioBlob);
    });

    mediaRecorder.start();
    setRecordingUI(true);
  } catch {
    setError("Microphone permission denied or unavailable.");
    stopAndReleaseStream();
  }
}

function stopRecording() {
  if (!mediaRecorder || mediaRecorder.state === "inactive") {
    return;
  }

  mediaRecorder.stop();
  setRecordingUI(false);
}

recordButton.addEventListener("click", async () => {
  if (isRecording) {
    stopRecording();
  } else {
    await startRecording();
  }
});
