"""Text-to-speech through the reSpeaker's speaker — multilingual + fast.

Piper is kept RESIDENT (one long-lived process per voice) so we don't reload the
model on every sentence — that reload was the ~1.5s "speaks late" lag. Text is
fed to the running process and raw audio streams straight to aplay.

English (and Hindi if present) use natural Piper voices; any other language falls
back to espeak-ng (~100 languages, robotic but universal).
"""
import asyncio
import json
import os
import select
import shutil
import subprocess

import config

_ESPEAK = shutil.which("espeak-ng") or shutil.which("espeak")
_PIPER_OK = os.path.exists(config.PIPER_BIN)

_HERE = os.path.dirname(os.path.abspath(__file__))
# espeak language code -> Piper voice file
VOICE_FILES = {"en": config.PIPER_VOICE}
_hi = os.path.join(_HERE, "voices", "hi_IN-priyamvada-medium.onnx")
if os.path.exists(_hi):
    VOICE_FILES["hi"] = _hi


# Piper emits nothing until it has synthesised a whole line, so one long line
# means the guest hears silence for the length of the whole sentence. Breaking
# the opening clause off its own line gets the first words out roughly 300 ms
# sooner; the rest follows as one piece so the delivery still sounds joined up.
_LEAD_MIN, _LEAD_MAX = 12, 72
_MARKS = (", ", ". ", "? ", "! ", " — ", "; ", ": ")


def _phrases(text: str) -> list[str]:
    """Split off the first clause, at the EARLIEST natural break that isn't
    trivially short. Later breaks would leave the opening chunk long, which is
    the thing we are trying to avoid."""
    text = text.strip()
    if len(text) <= _LEAD_MAX:
        return [text]
    cut = -1
    for mark in _MARKS:
        i = text.find(mark, _LEAD_MIN)
        if i != -1 and (cut < 0 or i < cut):
            cut = i
    if cut < 0 or cut > _LEAD_MAX:
        return [text]
    return [text[:cut + 1].strip(), text[cut + 1:].strip()]


class _PiperProc:
    """A resident Piper process for one voice (model stays loaded)."""
    def __init__(self, voice):
        self.voice = voice
        self.sr = self._sample_rate(voice)
        self.proc = None

    @staticmethod
    def _sample_rate(voice):
        try:
            j = json.load(open(voice + ".json"))
            return int(j.get("audio", {}).get("sample_rate", 22050))
        except Exception:
            return 22050

    def _ensure(self):
        if self.proc is None or self.proc.poll() is not None:
            self.proc = subprocess.Popen(
                [config.PIPER_BIN, "--model", self.voice, "--output-raw",
                 "--length_scale", str(config.PIPER_LENGTH_SCALE)],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            )

    def speak(self, text):
        """Generate + play one line, STREAMING audio to aplay as it's produced so
        speech starts almost immediately. Returns True if any audio played."""
        self._ensure()
        payload = "\n".join(_phrases(text.replace("\n", " "))) + "\n"
        self.proc.stdin.write(payload.encode("utf-8"))
        self.proc.stdin.flush()
        aplay = subprocess.Popen(
            ["aplay", "-q", "-r", str(self.sr), "-f", "S16_LE", "-c", "1",
             "-D", config.PLAYBACK_DEVICE],
            stdin=subprocess.PIPE,
        )
        fd = self.proc.stdout.fileno()
        first, got = True, False
        while True:
            r, _, _ = select.select([fd], [], [], 3.0 if first else 0.5)
            if r:
                chunk = os.read(fd, 4096)
                if not chunk:
                    break
                aplay.stdin.write(chunk)   # play as it generates
                got, first = True, False
            else:
                break  # gap after audio (or nothing produced) -> utterance done
        try:
            aplay.stdin.close()
        except Exception:
            pass
        aplay.wait()
        return got


_procs = {}


def _piper(text, code):
    proc = _procs.get(code)
    if proc is None:
        proc = _PiperProc(VOICE_FILES[code])
        _procs[code] = proc
    return proc.speak(text)


# --- online neural voices (Microsoft Edge) ---------------------------------
# Piper is fast and local, but it speaks American English to guests in Gujarat.
# These are the same neural voices Edge's read-aloud uses: free, no key, and
# they include Indian English, Hindi and Gujarati. The cost is latency — the
# service takes ~600 ms to answer no matter how short the line, because that is
# connection setup rather than synthesis, so there is nothing to optimise away.
# Piper stays the fallback and the whole of offline mode.
EDGE_VOICES = {
    "en": "en-IN-NeerjaNeural",   # Indian English, not American
    "hi": "hi-IN-SwaraNeural",
    "gu": "gu-IN-DhwaniNeural",
    "mr": "mr-IN-AarohiNeural",
    "ta": "ta-IN-PallaviNeural",
    "te": "te-IN-ShrutiNeural",
    "bn": "bn-IN-TanishaaNeural",
    "kn": "kn-IN-SapnaNeural",
    "ml": "ml-IN-SobhanaNeural",
    "pa": "pa-IN-OjasNeural",
    "ur": "ur-IN-GulNeural",
    "es": "es-ES-ElviraNeural",
    "fr": "fr-FR-DeniseNeural",
    "de": "de-DE-KatjaNeural",
    "ar": "ar-EG-SalmaNeural",
    "zh": "zh-CN-XiaoxiaoNeural",
    "ja": "ja-JP-NanamiNeural",
    "ru": "ru-RU-SvetlanaNeural",
}
_EDGE_TIMEOUT = 8.0        # a table in silence is worse than a robotic voice
_MPG123 = shutil.which("mpg123")


async def _edge_pump(text, voice, sink):
    import edge_tts
    import settings
    played = False
    rate = str(settings.get("tts_rate", "+12%"))
    async for chunk in edge_tts.Communicate(text, voice, rate=rate).stream():
        if chunk["type"] == "audio" and chunk["data"]:
            sink.write(chunk["data"])       # play as it arrives
            sink.flush()
            played = True
    return played


def _edge(text, code) -> bool:
    """Speak with an online neural voice. False means 'nothing was played' —
    the caller can safely fall back without the guest hearing it twice."""
    voice = EDGE_VOICES.get(code)
    if not voice or not _MPG123:
        return False
    try:
        import settings
        if settings.force_local() or settings.get("tts_engine") != "natural":
            return False
    except Exception:
        return False

    player = subprocess.Popen(
        [_MPG123, "-q", "--no-control", "-a", config.PLAYBACK_DEVICE, "-"],
        stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    played = False
    try:
        played = asyncio.run(asyncio.wait_for(
            _edge_pump(text, voice, player.stdin), _EDGE_TIMEOUT))
    except Exception as e:
        print(f"[TTS] online voice failed ({e}); using Piper", flush=True)
    finally:
        try:
            player.stdin.close()
        except Exception:
            pass
        player.wait()
    return played


def _speak_espeak(text, lang="en"):
    if not _ESPEAK:
        print(f"[TTS unavailable] {text}")
        return
    espeak = subprocess.Popen(
        [_ESPEAK, "-v", lang, "-s", str(config.TTS_RATE),
         "-a", str(config.TTS_AMPLITUDE), "--stdout", text],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
    )
    aplay = subprocess.Popen(["aplay", "-q", "-D", config.PLAYBACK_DEVICE], stdin=espeak.stdout)
    espeak.stdout.close()
    aplay.wait()
    espeak.wait()


def speak(text, lang="en"):
    """Say `text` in the given espeak language code (default English).

    When the assistant isn't active its microphone is closed, so nothing should
    be coming through here anyway — but unprompted messages (a payment landing,
    say) still can. Log them and show them on the ePaper; don't say them out
    loud into a room that asked for quiet.
    """
    print(f"[Lumina/{lang}] {text}", flush=True)
    try:
        import settings
        state = settings.get("assistant_state")
        if state != "active":
            print(f"  ({state} — not spoken)", flush=True)
            return
    except Exception:
        pass
    # Best voice first, then the fastest local one, then something that at least
    # speaks. Each step only runs if the previous played nothing at all, so a
    # guest never hears the same line twice.
    try:
        if _edge(text, lang):
            return
    except Exception as e:
        print(f"[TTS] online voice failed ({e}); using Piper")
    if lang in VOICE_FILES and _PIPER_OK:
        try:
            if _piper(text, lang):
                return
        except Exception as e:
            print(f"[TTS] Piper failed ({e}); using espeak")
    _speak_espeak(text, lang)


# Backwards-compat helper used by a timing test.
def _speak_piper(text, voice):
    return _piper(text, "en")


if __name__ == "__main__":
    import sys, time
    t = " ".join(sys.argv[1:]) or "Hello, this is Lumina, your table assistant."
    for i in range(2):
        t0 = time.time()
        speak(t)
        print(f"call {i+1}: {time.time()-t0:.2f}s")
