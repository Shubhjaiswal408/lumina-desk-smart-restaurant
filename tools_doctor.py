"""Check every backend Lumina depends on, including the fallbacks.

The cloud paths get exercised constantly; the offline ones only matter on the
day the internet dies, which is exactly when nobody wants to discover they were
broken. This runs all of them.

    ./venv/bin/python tools_doctor.py
"""
import os
import shutil
import subprocess
import sys
import time

import numpy as np

import config
import settings

OK, BAD, WARN = "  ok  ", " FAIL ", " warn "
problems = []


def report(state, what, detail=""):
    print(f"{state} {what}" + (f"  — {detail}" if detail else ""), flush=True)
    if state is BAD:
        problems.append(what)


def timed(fn):
    t = time.perf_counter()
    out = fn()
    return out, (time.perf_counter() - t) * 1000


def say(text: str) -> np.ndarray:
    """Piper as a stand-in guest, resampled to the mic's 16 kHz."""
    p = subprocess.run([config.PIPER_BIN, "--model", config.PIPER_VOICE,
                        "--output-raw"], input=text.encode(), capture_output=True)
    pcm = np.frombuffer(p.stdout, dtype=np.int16)
    idx = (np.arange(int(len(pcm) * 16000 / 22050)) * 22050 / 16000).astype(int)
    return pcm[np.clip(idx, 0, len(pcm) - 1)]


def heading(t):
    print(f"\n{t}\n" + "-" * len(t))


# ---------------------------------------------------------------- wake word --
heading("Wake word")
try:
    import wake
    report(OK if config.OWW_IS_CUSTOM else WARN,
           f'"{config.WAKE_PHRASE}"',
           "custom model" if config.OWW_IS_CUSTOM
           else "models/hey_lumina.onnx missing — listening for 'Hey Jarvis'")
    det, ms = timed(lambda: wake.WakeDetector())
    silence = np.zeros(config.FRAME_SAMPLES, dtype=np.int16)
    score = det.score(silence)
    report(OK, "detector runs", f"loaded in {ms:.0f} ms, silence scores {score:.3f}")
    report(OK if score < 0.3 else BAD, "silence doesn't trigger it")
except Exception as e:
    report(BAD, "wake word", str(e))

# --------------------------------------------------------------------- STT --
heading("Speech to text")
PHRASE = "one large margherita and two cold coffees"
pcm = say(PHRASE)
report(OK, "test audio synthesised", f"{len(pcm) / 16000:.1f}s of speech")

import stt  # noqa: E402

prompt = stt._stt_prompt()
report(OK if len(prompt) <= 896 else BAD, "Whisper prompt fits Groq's cap",
       f"{len(prompt)}/896 chars")

key = settings.groq_key()
if key:
    try:
        (text, lg), ms = timed(lambda: stt._groq_transcribe(pcm, key))
        report(OK if text else BAD, "Groq Whisper", f'{ms:.0f} ms — "{text}" [{lg}]')
    except Exception as e:
        report(BAD, "Groq Whisper", str(e))
else:
    report(WARN, "Groq Whisper", "no API key (offline mode?)")

try:
    from vosk import Model, SetLogLevel
    SetLogLevel(-1)
    if os.path.isdir(config.VOSK_MODEL_PATH):
        m, ms = timed(lambda: Model(config.VOSK_MODEL_PATH))
        text, ms2 = timed(lambda: stt._vosk_transcribe(pcm, m))
        report(OK if text else BAD, "Vosk (offline fallback)",
               f'model {ms:.0f} ms, transcribe {ms2:.0f} ms — "{text}"')
    else:
        report(BAD, "Vosk", f"model folder missing: {config.VOSK_MODEL_PATH}")
except Exception as e:
    report(BAD, "Vosk", str(e))

# --------------------------------------------------------------------- LLM --
heading("Understanding")
import dialog     # noqa: E402
import intents    # noqa: E402
import llm        # noqa: E402
from session import Session  # noqa: E402

r, ms = timed(lambda: intents.parse_intent(PHRASE))
cart = Session()
dialog.handle(r, cart)
got = [(cart.line_label(l), l["qty"]) for l in cart.cart]
report(OK if len(got) == 2 else BAD, "rule parser (the instant path)",
       f"{ms:.1f} ms — {got}")

if key:
    # Groq retires models. When llama-3.3-70b went, every call 404'd and the
    # tables quietly ran on rules for who knows how long. Check it still exists.
    try:
        import requests
        ids = {m["id"] for m in requests.get(
            "https://api.groq.com/openai/v1/models",
            headers={"Authorization": f"Bearer {key}"}, timeout=10).json()["data"]}
        for label, want in (("chat", config.GROQ_LLM_MODEL),
                            ("speech", config.GROQ_STT_MODEL)):
            report(OK if want in ids else BAD, f"{label} model exists on Groq", want)
    except Exception as e:
        report(WARN, "Groq model list", str(e))

    try:
        out, ms = timed(lambda: llm._via_groq(PHRASE, Session()))
        report(OK, f"Groq {config.GROQ_LLM_MODEL}",
               f"{ms:.0f} ms — intent={out['intent']}, "
               f"{len(out.get('items') or [])} item(s)")
    except Exception as e:
        # A 429 means the key is fine and the quota isn't. Service continues:
        # rules answer instantly instead. That's a note, not a fault.
        rate_limited = "429" in str(e) or "Too Many Requests" in str(e)
        report(WARN if rate_limited else BAD, "Groq LLM",
               "rate limited — free tier quota; rules cover the turn"
               if rate_limited else str(e))
else:
    report(WARN, "Groq LLM", "no API key")

try:
    import requests
    requests.get("http://localhost:11434/api/version", timeout=3).raise_for_status()
    try:
        out, ms = timed(lambda: llm._via_local(PHRASE, Session()))
        report(OK, f"local {llm.LOCAL_MODEL.split('/')[-1]}",
               f"{ms:.0f} ms — intent={out['intent']}")
    except Exception as e:
        report(WARN, "local model answered badly", f"{e} (rules cover this)")
except Exception:
    report(WARN, "Ollama", "not running — offline mode falls back to rules only")

# --------------------------------------------------------------------- TTS --
heading("Speech")
import tts  # noqa: E402

report(OK if tts._PIPER_OK else BAD, "Piper binary", config.PIPER_BIN)
for code, voice in tts.VOICE_FILES.items():
    report(OK if os.path.exists(voice) else BAD, f"voice [{code}]",
           os.path.basename(voice))

REPLY = "I've added 1 Large Margherita and 2 Cold Coffees to your order, 468 rupees."
lead = tts._phrases(REPLY)[0]
report(OK if lead != REPLY else WARN, "reply splits for a fast first word",
       f'leads with "{lead[:40]}…"')

import select  # noqa: E402

for code in tts.VOICE_FILES:
    try:
        proc = tts._procs.setdefault(code, tts._PiperProc(tts.VOICE_FILES[code]))
        proc._ensure()
        time.sleep(0.8)
        fd = proc.proc.stdout.fileno()
        t = time.perf_counter()
        proc.proc.stdin.write(b"testing one two three\n")
        proc.proc.stdin.flush()
        n = 0
        if select.select([fd], [], [], 8.0)[0]:
            n = len(os.read(fd, 4096))
        ms = (time.perf_counter() - t) * 1000
        while select.select([fd], [], [], 0.6)[0]:
            if not os.read(fd, 262144):
                break
        report(OK if n else BAD, f"Piper generates [{code}]",
               f"first audio in {ms:.0f} ms")
    except Exception as e:
        report(BAD, f"Piper [{code}]", str(e))

engine = settings.get("tts_engine")
if engine == "natural" and not settings.force_local():
    report(OK if tts._MPG123 else BAD, "mpg123 (decodes the online voice)",
           tts._MPG123 or "not installed — run: sudo apt install mpg123")
    try:
        import asyncio as _aio
        import edge_tts  # noqa: F401

        async def _first_chunk():
            import time as _t
            t0 = _t.perf_counter()
            async for c in edge_tts.Communicate(
                    "testing", tts.EDGE_VOICES["en"],
                    rate=str(settings.get("tts_rate"))).stream():
                if c["type"] == "audio" and c["data"]:
                    return _t.perf_counter() - t0
            return None

        ms = _aio.run(_aio.wait_for(_first_chunk(), 12))
        report(OK if ms else BAD, f"online voice {tts.EDGE_VOICES['en']}",
               f"first audio in {ms * 1000:.0f} ms" if ms else "no audio returned")
    except ImportError:
        report(BAD, "edge-tts", "not installed — run: pip install edge-tts")
    except Exception as e:
        report(WARN, "online voice", f"{e} — Piper covers it")
else:
    report(WARN, "online voice", f"off (tts_engine={engine}, mode={settings.get('mode')})")

report(OK if tts._ESPEAK else BAD, "espeak-ng (any other language)",
       tts._ESPEAK or "not installed")
report(OK if shutil.which("aplay") else BAD, "aplay", config.PLAYBACK_DEVICE)

# ------------------------------------------------------------------- audio --
heading("Audio devices")
try:
    import sounddevice as sd
    devs = sd.query_devices()
    cur = devs[config.INPUT_DEVICE_INDEX]
    report(OK, f"input index {config.INPUT_DEVICE_INDEX}", cur["name"])
    ins = [d for d in devs if d["max_input_channels"] > 0]
    if ins:
        report(OK, "microphone is free", f"{cur['max_input_channels']} channel(s)")
    else:
        # PortAudio reports zero channels on a card someone else already holds.
        # While the assistant is listening that is the correct, healthy state.
        voice = subprocess.run(["systemctl", "is-active", "lumina-voice"],
                               capture_output=True, text=True).stdout.strip()
        report(OK if voice == "active" else BAD, "microphone",
               "in use by lumina-voice (expected)" if voice == "active"
               else "no input channels and the voice service isn't running")
except Exception as e:
    report(BAD, "audio devices", str(e))

# ---------------------------------------------------------------- services --
heading("Services")
for unit in ("mosquitto", "lumina-voice", "lumina-display",
             "lumina-kds", "lumina-payments"):
    out = subprocess.run(["systemctl", "is-active", unit],
                         capture_output=True, text=True).stdout.strip()
    report(OK if out == "active" else BAD, unit, out)

heading("Settings")
report(OK, "brain mode", settings.get("mode"))
report(OK, "assistant", settings.get("assistant_state"))
report(OK if settings.get("upi_vpa") else WARN, "UPI id",
       settings.get("upi_vpa") or "not set")
report(OK if settings.get("feedback_url") else WARN, "feedback form",
       settings.get("feedback_url") or "not set — the QR stays hidden")

print()
if problems:
    print(f"{len(problems)} problem(s):")
    for p in problems:
        print("  -", p)
    sys.exit(1)
print("every backend answered.")
