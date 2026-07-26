"""Central configuration for Lumina Desk device-side service."""

# --- Audio hardware (reSpeaker XVF3800 4-Mic Array) ---
# ALSA card index shown by `aplay -l` / `arecord -l`
RESPEAKER_CARD = 2
# ALSA device string used for playback (speaker hangs off the reSpeaker out)
PLAYBACK_DEVICE = f"plughw:{RESPEAKER_CARD},0"
# PortAudio input device index shown by sounddevice.query_devices()
INPUT_DEVICE_INDEX = 0
# reSpeaker XVF3800 captures at 16 kHz natively -> perfect for openWakeWord
SAMPLE_RATE = 16000
# openWakeWord expects 80 ms frames (1280 samples @ 16 kHz)
FRAME_SAMPLES = 1280
# The reSpeaker presents 2 processed channels; we use channel 0.
CAPTURE_CHANNELS = 1

# --- Wake word (Vosk phrase spotting — custom "Hey Lumina", no account) ---
import os as _os

_HERE = _os.path.dirname(_os.path.abspath(__file__))

# Offline Vosk speech model (also reused for Stage 2 speech-to-text).
VOSK_MODEL_PATH = _os.path.join(_HERE, "vosk-model-small-en-us-0.15")

# --- Wake word engine: openWakeWord (accurate neural model) ---
# Drop a trained "hey_lumina.onnx" into models/ and it's used automatically;
# until then we fall back to the built-in "hey_jarvis" so the system still runs.
_HEY_LUMINA = _os.path.join(_HERE, "models", "hey_lumina.onnx")
OWW_IS_CUSTOM = _os.path.exists(_HEY_LUMINA)
OWW_MODEL = _HEY_LUMINA if OWW_IS_CUSTOM else "hey_jarvis"
# The word guests say is always "Hey Lumina". Until the custom model is trained,
# the engine actually listens for "Hey Jarvis" (a dev-only stand-in).
WAKE_PHRASE = "Hey Lumina"

OWW_THRESHOLD = 0.4        # wake confidence needed to trigger (raise if false fires)
OWW_VAD_THRESHOLD = 0.3    # Silero VAD gate; higher = stricter "is this speech"
# Seconds to ignore further detections after a trigger (avoids double-fires).
WAKE_COOLDOWN_SEC = 3.0

# --- Command recording (voice activity detection) ---
# A 0.1 s frame is "speech" if its RMS exceeds this. Auto-raised to sit above
# the measured room noise floor at each recording, so this is just a floor.
# Higher = needs clearer speech to start (avoids capturing noise -> Whisper
# hallucinating random words).
VAD_RMS_THRESHOLD = 700
# After recording, the whole clip must average at least this RMS to be sent for
# transcription — rejects noise/near-silence that Whisper would hallucinate on.
VAD_MIN_SPEECH_RMS = 500
# Stop recording after this much continuous silence once the guest has started.
VAD_SILENCE_SEC = 0.6
# Give up if no speech starts within this long after the prompt.
VAD_START_TIMEOUT_SEC = 5.0
# Hard cap on a single command's length.
VAD_MAX_SEC = 12.0

# --- Speech-to-text engine ---
# Primary: Groq cloud Whisper (fast, accurate). Fallback: offline Vosk.
def _load_groq_key():
    key = _os.environ.get("GROQ_API_KEY")
    if key:
        return key.strip()
    path = _os.path.join(_HERE, ".groq_key")
    if _os.path.exists(path):
        with open(path) as f:
            return f.read().strip()
    return ""

GROQ_API_KEY = _load_groq_key()
GROQ_STT_MODEL = "whisper-large-v3-turbo"
GROQ_STT_URL = "https://api.groq.com/openai/v1/audio/transcriptions"

# --- NLU fallback LLM ---
# When rules can't classify an utterance: use Groq's fast LLM if online
# (~1 s), else the local LFM2 via Ollama (~6 s, offline).
GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"
# 70B is far more reliable at intent/slot extraction than 8B (still ~1-2 s, free).
GROQ_LLM_MODEL = "llama-3.3-70b-versatile"

# --- Text to speech ---
# Primary: Piper neural TTS (offline, natural). Fallback: espeak-ng.
PIPER_BIN = _os.path.join(_HERE, "piper", "piper")
# Medium voice — fast on the Pi CPU (high-quality lags too much per sentence).
PIPER_VOICE = _os.path.join(_HERE, "voices", "en_US-amy-medium.onnx")
PIPER_LENGTH_SCALE = 1.0

# espeak-ng fallback settings (used only if Piper is unavailable)
TTS_VOICE = "en-us+f3"
TTS_RATE = 155
TTS_PITCH = 55
TTS_AMPLITUDE = 200

# --- Branding ---
ASSISTANT_NAME = "Lumina"

# --- Table identity + MQTT bus ---
# This device's table. Topics live under lumina/table/<TABLE_ID>/...
TABLE_ID = "07"
MQTT_HOST = "localhost"   # local broker on the Pi
MQTT_PORT = 1883

# Display transport: "wifi" streams frames to the battery panel over MQTT;
# "serial" pushes to a USB-connected panel.
DISPLAY_TRANSPORT = "wifi"

# An empty table idle this long starts a fresh session (safety net for table
# turnover; the main reset happens when the kitchen marks the order served).
SESSION_IDLE_RESET_SEC = 1800   # 30 min

# --- UPI payments (dynamic QR) ---
# Standard NPCI deep link. Only `am` (amount) changes per bill — everything else
# is your merchant identity. Put your real VPA here (the UPI ID money goes to).
# Placeholder only — set the real one in the console (Settings → UPI ID), which
# stores it in settings.json (gitignored). Never commit a real VPA.
UPI_VPA = "yourname@upi"
UPI_PAYEE_NAME = "Lumina Desk"
UPI_CURRENCY = "INR"
# `{am}` is substituted with the bill amount, `{tn}` note, `{tr}` txn reference.
UPI_URL_TEMPLATE = ("upi://pay?pa={pa}&pn={pn}&am={am}&cu={cu}&tn={tn}&tr={tr}")

# FamApp emails the merchant on every incoming payment; payment_watcher.py reads
# that mailbox over IMAP to auto-confirm bills (no gateway/webhook needed).
PAYMENT_EMAIL = "you@gmail.com"     # override in Settings (settings.json)

# --- Admin console lock ---
# Staff PIN for the web console. Change it here (LAN-only device, shared PIN).
# Default PIN for a fresh install. CHANGE IT — your real PIN lives in
# settings.json (gitignored), not here.
ADMIN_PIN = "0000"

# --- Feedback QR (shown on the thank-you screen after payment) ---
# Must be a PUBLIC url — guests are often on mobile data, so a LAN address like
# techiesms.local would fail. A Google Form link works well and needs no infra.
# Leave empty to hide the feedback QR entirely.
FEEDBACK_URL = ""      # e.g. "https://forms.gle/xxxxxxxx"
