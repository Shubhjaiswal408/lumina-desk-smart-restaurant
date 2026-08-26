"""Speech-to-text for the guest's command.

record_utterance() captures one spoken command from the background AudioCapture
using simple energy-based voice-activity detection (records from the first word
until the guest goes quiet). transcribe() sends that audio to Groq's Whisper
(fast + accurate) and falls back to offline Vosk if the cloud is unreachable.
"""
import io
import json
import re
import wave

import numpy as np
import requests

import config
import menu
import net
import settings

# Whisper takes a prompt that biases it toward words it would otherwise mangle
# ("paneer tikka", not "an intika"). Groq caps that prompt at 896 characters.
# The full menu is several times longer, and sending it whole makes every cloud
# transcription fail with a 400 — silently dropping the system onto offline
# Vosk, which is much less accurate. So send only the distinctive words.
_PROMPT_LIMIT = 880

# Words Whisper already knows perfectly well; spending prompt budget on them
# would crowd out the ones it actually needs help with.
_GENERIC = {
    "and", "with", "the", "of",
    "veg", "cheese", "cheesy", "garlic", "bread", "burger", "pizza", "fries",
    "rings", "ring", "roll", "rolls", "shake", "milkshake", "coffee", "cold",
    "hot", "iced", "tea", "green", "apple", "lime", "mango", "strawberry",
    "vanilla", "chocolate", "choco", "corn", "onion", "potato", "spicy",
    "sweet", "double", "classic", "crispy", "plain", "salted", "special",
    "combo", "regular", "medium", "large", "stuffed", "mexican", "italian",
    "chips", "sauce", "shots", "slice", "patty", "brownie", "cake", "lava",
    "nachos", "supreme", "delight", "magic", "crunch", "fiesta", "mushroom",
    "sugarfree", "explosion", "american", "indo", "asian", "veggie", "veggies",
}

_prompt_cache: dict = {}


def _stt_prompt() -> str:
    """Distinctive menu words, most common first, trimmed to fit Groq's limit.
    Rebuilt whenever the menu changes so newly added dishes are heard too."""
    names = tuple(d["name"] for d in menu.all_dishes())
    if _prompt_cache.get("key") != names:
        counts: dict[str, int] = {}
        for n in names:
            for w in re.findall(r"[A-Za-z][A-Za-z'-]+", n):
                if len(w) < 4 or w.lower() in _GENERIC:
                    continue
                counts[w] = counts.get(w, 0) + 1
        head = "Indian restaurant order. Menu: "
        out = head
        for w in sorted(counts, key=lambda w: (-counts[w], w)):
            nxt = out + (w if out == head else ", " + w)
            if len(nxt) + 1 > _PROMPT_LIMIT:
                break
            out = nxt
        _prompt_cache.update(key=names, text=out + ".")
    return _prompt_cache["text"]


# ---------- recording (VAD) ----------

def _rms(frame: np.ndarray) -> float:
    if frame.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(frame.astype(np.float32) ** 2)))


def record_utterance(capture) -> np.ndarray | None:
    """Record one command. Returns int16 mono @16k, or None if nothing spoken."""
    frame_sec = 0.1
    silence_needed = int(config.VAD_SILENCE_SEC / frame_sec)
    start_timeout = int(config.VAD_START_TIMEOUT_SEC / frame_sec)
    max_frames = int(config.VAD_MAX_SEC / frame_sec)

    # Calibrate the noise floor from the first few frames of "room".
    noise = []
    for _ in range(3):
        try:
            noise.append(_rms(capture.read(timeout=1.0)))
        except Exception:
            break
    noise_floor = max(noise) if noise else 0.0
    threshold = max(config.VAD_RMS_THRESHOLD, noise_floor * 2.5)

    preroll = []          # keep last ~0.3 s so we don't clip the first word
    voiced = []
    started = False
    silence_run = 0
    waited = 0

    while True:
        try:
            frame = capture.read(timeout=1.0)
        except Exception:
            break

        loud = _rms(frame) >= threshold

        if not started:
            preroll.append(frame)
            if len(preroll) > 3:
                preroll.pop(0)
            if loud:
                started = True
                voiced.extend(preroll)
                voiced.append(frame)
            else:
                waited += 1
                if waited >= start_timeout:
                    return None  # nobody spoke
        else:
            voiced.append(frame)
            silence_run = silence_run + 1 if not loud else 0
            if silence_run >= silence_needed or len(voiced) >= max_frames:
                break

    if not voiced:
        return None
    audio = np.concatenate(voiced).astype(np.int16)
    # Reject clips that aren't clearly speech (too quiet or too short) so we
    # never send noise to Whisper (which would hallucinate random words).
    # Reject clips that aren't clearly speech. The floor has to move with the
    # room: a fixed 500 was below the ~1100 RMS of this one, so ordinary noise
    # sailed through to Whisper, which duly hallucinated "Okay." and "Exactly."
    # — and Lumina answered them as if a guest had spoken.
    floor = max(config.VAD_MIN_SPEECH_RMS, noise_floor * 1.6)
    if len(audio) < int(0.4 * config.SAMPLE_RATE) or _rms(audio) < floor:
        return None
    return audio


# ---------- transcription ----------

def _pcm_to_wav(pcm: np.ndarray) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(config.SAMPLE_RATE)
        w.writeframes(pcm.tobytes())
    return buf.getvalue()


def _groq_transcribe(pcm: np.ndarray, key: str) -> tuple[str, str]:
    """Returns (text, detected_language). No language pin -> Whisper auto-detects
    across ~99 languages; verbose_json gives us the detected language back."""
    wav = _pcm_to_wav(pcm)
    resp = net.session().post(
        config.GROQ_STT_URL,
        headers={"Authorization": f"Bearer {key}"},
        files={"file": ("command.wav", wav, "audio/wav")},
        data={"model": config.GROQ_STT_MODEL, "response_format": "verbose_json",
              "temperature": "0", "prompt": _stt_prompt()},
        timeout=15,
    )
    resp.raise_for_status()
    j = resp.json()
    return j.get("text", "").strip(), (j.get("language", "english") or "english")


def _vosk_transcribe(pcm: np.ndarray, vosk_model) -> str:
    from vosk import KaldiRecognizer
    rec = KaldiRecognizer(vosk_model, config.SAMPLE_RATE)
    rec.AcceptWaveform(pcm.tobytes())
    return json.loads(rec.FinalResult()).get("text", "").strip()


# Given silence or noise, Whisper doesn't return nothing — it returns one of a
# small set of stock phrases. None of them is ever a real thing to say to a
# waiter, and answering them is what makes Lumina feel like it's talking to
# itself.
_HALLUCINATIONS = {
    "okay", "ok", "okay.", "thank you", "thanks", "thank you.", "bye", "bye.",
    "exactly", "exactly.", "you", "yeah", "hmm", "mm", "uh", "um", "so",
    "thank you for watching", "thanks for watching", "please subscribe",
    "subscribe", "the end", ".", "...", "silence", "[silence]", "music",
    "[music]", "applause", "[applause]", "bye bye", "see you", "i'm sorry",
}


def _is_hallucination(text: str) -> bool:
    """Whisper's stock output for 'nothing was said'."""
    t = (text or "").strip().lower().rstrip(".!?,")
    if not t:
        return True
    # It often repeats one of them: "Okay. Okay."
    parts = {p.strip().rstrip(".!?,") for p in t.split(".") if p.strip()}
    return bool(parts) and parts <= _HALLUCINATIONS


def transcribe(pcm: np.ndarray, vosk_model=None) -> tuple[str, str, str]:
    """Return (text, engine_used, language).

    Online/auto: Groq Whisper (accurate, multilingual), Vosk as the safety net.
    Offline mode: Vosk only — no network call is even attempted.
    """
    if pcm is None or pcm.size == 0:
        return "", "none", "english"
    key = settings.groq_key()
    if key:
        try:
            text, lang = _groq_transcribe(pcm, key)
            return text, "groq", lang
        except Exception as e:
            print(f"  (Groq STT failed, using offline Vosk: {e})", flush=True)
    if vosk_model is not None:
        return _vosk_transcribe(pcm, vosk_model), "vosk", "english"
    return "", "none", "english"
