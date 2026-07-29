"""Measure where a turn actually spends its time.

Speaks test phrases with Piper, feeds that audio back through the real
STT -> understand -> reply -> speak path, and reports each stage. Guessing at
latency is how you end up optimising the fast part.

    ./venv/bin/python tools_bench.py            # current settings
    ./venv/bin/python tools_bench.py --offline  # force the local path
"""
import os
import select
import statistics
import subprocess
import sys
import time

import numpy as np

import config
import dialog
import settings
import stt
import tts
import wake_listen
from session import Session

PHRASES = [
    "one large margherita and two cold coffees",
    "what's my bill",
    "how much is a paneer momo",
    "remove the cold coffee",
    "can you bring two glasses of water",
]


def synth(text: str) -> np.ndarray:
    """Render a phrase to 16 kHz mono PCM with Piper — our stand-in for a guest."""
    p = subprocess.run(
        [config.PIPER_BIN, "--model", config.PIPER_VOICE, "--output-raw"],
        input=text.encode(), capture_output=True)
    pcm = np.frombuffer(p.stdout, dtype=np.int16)
    # Piper voices are 22.05 kHz; the mic path is 16 kHz.
    idx = (np.arange(int(len(pcm) * 16000 / 22050)) * 22050 / 16000).astype(int)
    return pcm[np.clip(idx, 0, len(pcm) - 1)]


def time_to_first_sound(reply: str) -> float:
    """What the guest actually waits for: the first sample out of Piper.

    Uses the resident process and the same phrase splitting as tts.speak, but
    doesn't open the speaker — the bench shouldn't shout across the room.
    """
    proc = tts._procs.setdefault("en", tts._PiperProc(config.PIPER_VOICE))
    proc._ensure()
    fd = proc.proc.stdout.fileno()
    t = time.perf_counter()
    proc.proc.stdin.write(("\n".join(tts._phrases(reply)) + "\n").encode())
    proc.proc.stdin.flush()
    select.select([fd], [], [], 6.0)
    os.read(fd, 4096)
    first = time.perf_counter() - t
    while True:                # drain fully, or the next read returns stale audio
        r, _, _ = select.select([fd], [], [], 0.9)
        if not r or not os.read(fd, 262144):
            break
    return first


def bench(rounds: int = 3):
    import llm
    wake_listen._LLM_ON = llm.is_available()      # main() normally sets this
    print(f"mode={settings.get('mode', 'auto')}  "
          f"cloud_key={'yes' if settings.groq_key() else 'no'}  "
          f"llm_on={wake_listen._LLM_ON}\n")

    stages: dict[str, list] = {"stt": [], "understand": [], "reply": [], "speak": []}
    audio = {p: synth(p) for p in PHRASES}
    time_to_first_sound("warming up")             # load the model before timing

    print(f"{'phrase':<40}{'stt':>8}{'think':>8}{'reply':>8}{'speak':>8}  total  brain")
    print("-" * 88)

    for _ in range(rounds):
        for phrase in PHRASES:
            s = Session()
            t = time.perf_counter()
            text, engine, wlang = stt.transcribe(pcm := audio[phrase])
            d_stt = time.perf_counter() - t

            t = time.perf_counter()
            result = wake_listen.understand(text, s)
            d_und = time.perf_counter() - t
            brain = "rules" if d_und < 0.10 else "cloud"

            t = time.perf_counter()
            det = dialog.handle(result, s)
            use_llm = (dialog.canonical(result["intent"]) not in wake_listen.FACT_INTENTS
                       and bool(result.get("reply")))
            reply = result["reply"] if use_llm else det
            d_rep = time.perf_counter() - t

            d_tts = time_to_first_sound(reply)

            for k, v in (("stt", d_stt), ("understand", d_und),
                         ("reply", d_rep), ("speak", d_tts)):
                stages[k].append(v)
            total = d_stt + d_und + d_rep + d_tts
            print(f"{phrase[:38]:<40}{d_stt:>7.2f}s{d_und:>7.2f}s"
                  f"{d_rep:>7.2f}s{d_tts:>7.2f}s {total:>5.2f}s  {brain}")

    print("-" * 88)
    med_total = 0.0
    for k in ("stt", "understand", "reply", "speak"):
        med = statistics.median(stages[k])
        med_total += med
        print(f"  {k:<12} median {med * 1000:7.0f} ms   worst {max(stages[k]) * 1000:7.0f} ms")
    print(f"  {'PIPELINE':<12} median {med_total * 1000:7.0f} ms")
    print(f"\n  Guest also waits {config.VAD_SILENCE_SEC:.1f}s of silence to prove "
          f"they finished speaking.")
    print(f"  So mouth-shut to first word: ~{med_total + config.VAD_SILENCE_SEC:.2f}s")


if __name__ == "__main__":
    if "--offline" in sys.argv:
        settings.save({"mode": "offline"})
    try:
        bench()
    finally:
        if "--offline" in sys.argv:
            settings.save({"mode": "auto"})
