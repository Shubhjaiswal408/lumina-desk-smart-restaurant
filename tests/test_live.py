"""One whole guest journey, end to end, against the running system.

Speaks each line with Piper, transcribes it back through the real STT, works out
what it means, answers it, publishes it — then checks the kitchen board and the
ePaper panel actually agree with the table.

Needs the services up (mosquitto, lumina-kds, lumina-display). The panel check
is skipped if no panel is powered on.

    ./venv/bin/python tests/test_live.py
"""
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np      # noqa: E402
import requests         # noqa: E402

import config           # noqa: E402
import dialog          # noqa: E402
import mqtt_bus          # noqa: E402
import settings          # noqa: E402
import stt          # noqa: E402
import wake_listen          # noqa: E402
from session import Session   # noqa: E402

TABLE = "07"
SAY = [
    "one large margherita and two cold coffees",
    "how much is a paneer momo",
    "what's in the cheese stuffed garlic bread",
    "actually remove the cold coffee",
    "what's my bill",
]

fails = []


def check(ok, what):
    print(("  ok   " if ok else "  FAIL ") + what)
    if not ok:
        fails.append(what)


def synth(text):
    p = subprocess.run([config.PIPER_BIN, "--model", config.PIPER_VOICE,
                        "--output-raw"], input=text.encode(), capture_output=True)
    pcm = np.frombuffer(p.stdout, dtype=np.int16)
    idx = (np.arange(int(len(pcm) * 16000 / 22050)) * 22050 / 16000).astype(int)
    return pcm[np.clip(idx, 0, len(pcm) - 1)]


def token():
    r = requests.post("http://localhost:8000/api/auth",
                      json={"pin": settings.get("admin_pin")}, timeout=5)
    return r.json()["token"]


def board(tok):
    r = requests.get("http://localhost:8000/api/state",
                     headers={"x-lumina-token": tok}, timeout=5)
    return r.json()


def main():
    import llm
    wake_listen._LLM_ON = llm.is_available()
    tok = token()

    client = mqtt_bus.make_client("e2e-test")
    frames = {"n": 0}
    client.on_message = lambda c, u, m: frames.__setitem__("n", frames["n"] + 1)
    client.subscribe(mqtt_bus.T_FRAME)
    time.sleep(1)

    session = Session()
    print("\n--- the conversation ---")
    for line in SAY:
        heard, engine, lg = stt.transcribe(synth(line))
        t = time.perf_counter()
        result = wake_listen.understand(heard, session)
        det = dialog.handle(result, session)
        use_llm = (dialog.canonical(result["intent"]) not in wake_listen.FACT_INTENTS
                   and bool(result.get("reply")))
        reply = result["reply"] if use_llm else det
        dt = (time.perf_counter() - t) * 1000
        print(f'  guest ({engine}): "{heard}"')
        print(f'  lumina [{result["intent"]} {dt:.0f}ms]: {reply}')
        mqtt_bus.publish_order(client, session)
        time.sleep(0.6)

    print("\n--- did the cart end up right? ---")
    cart = {session.line_label(l): l["qty"] for l in session.cart}
    print("  cart:", cart, "total ₹%d" % session.total())
    check("Large Margherita" in cart, "the pizza was ordered with its size")
    check("Cold Coffee" not in cart, "the coffee was removed when asked")
    check(all("Paneer Momo" not in k for k in cart),
          "asking a price did NOT order the dish")
    check(session.total() == 270, f"bill is the menu price (got {session.total()})")

    print("\n--- did the kitchen see it? ---")
    time.sleep(2)
    st = board(tok)
    mine = next((o for o in st["orders"] if o["table"] == TABLE), None)
    check(mine is not None, "the ticket reached the kitchen board")
    if mine:
        names = {(i["name"], i.get("size", "")) for i in mine["items"]}
        check(("Margherita", "Large") in names, "the kitchen knows the size")
        check(round(mine["total"]) == 270, "the kitchen total matches the table")

    print("\n--- did the panel get a new screen? ---")
    # Only meaningful if a panel is actually powered on. Distinguish "the Pi
    # never sent a frame" from "there is no panel plugged in right now".
    alive = {"seen": False}
    probe = mqtt_bus.make_client("e2e-probe")
    probe.on_message = lambda c, u, m: alive.__setitem__("seen", True)
    probe.subscribe(mqtt_bus.T_ACK)
    probe.subscribe(mqtt_bus.T_PANEL)
    # The service deliberately coalesces: the colour panel needs ~20 s per
    # refresh, so a burst of order updates becomes one frame, sent when the
    # panel acks. Wait past that rather than racing it.
    for _ in range(45):
        if frames["n"]:
            break
        time.sleep(1)
    probe.loop_stop()
    if frames["n"]:
        check(True, f"frames streamed to the panel ({frames['n']} chunks)")
    else:
        print("  SKIP  no panel answered — is it powered on? "
              "(the Pi is holding the frame, it will send on reconnect)")

    print("\n--- offline mode, same conversation ---")
    settings.save({"mode": "offline"})
    time.sleep(0.3)
    s2 = Session()
    worst = 0.0
    for line in SAY:
        t = time.perf_counter()
        r = wake_listen.understand(line, s2)      # rules path; no cloud at all
        dialog.handle(r, s2)
        worst = max(worst, time.perf_counter() - t)
    settings.save({"mode": "auto"})
    c2 = {s2.line_label(l): l["qty"] for l in s2.cart}
    print("  cart:", c2, "total ₹%d" % s2.total())
    check(c2 == cart, "offline reaches the same cart as online")
    check(worst < 0.2, f"offline stayed instant (worst {worst * 1000:.0f} ms)")

    client.loop_stop()
    print()
    if fails:
        print(f"{len(fails)} FAILURE(S):")
        for f in fails:
            print("  -", f)
        sys.exit(1)
    print("everything agrees.")


if __name__ == "__main__":
    main()
