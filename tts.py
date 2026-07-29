"""Text-to-speech through the reSpeaker's speaker — multilingual + fast.

Piper is kept RESIDENT (one long-lived process per voice) so we don't reload the
model on every sentence — that reload was the ~1.5s "speaks late" lag. Text is
fed to the running process and raw audio streams straight to aplay.

English (and Hindi if present) use natural Piper voices; any other language falls
back to espeak-ng (~100 languages, robotic but universal).
"""
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
        self.proc.stdin.write((text.replace("\n", " ") + "\n").encode("utf-8"))
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
    print(f"[Lumina/{lang}] {text}")
    try:
        import settings
        state = settings.get("assistant_state")
        if state != "active":
            print(f"  ({state} — not spoken)", flush=True)
            return
    except Exception:
        pass
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
