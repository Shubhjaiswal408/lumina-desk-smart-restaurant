"""Lumina Desk — wake word -> listen -> understand -> respond.

Audio path (fixes the old 'input overflow'): a background thread (audio.py)
continuously drains the reSpeaker into a queue, so the device never overflows.
The main loop consumes frames from that queue.

Per interaction:
  1. Vosk phrase-spotter waits for "Hey Lumina".
  2. Lumina says a short prompt.
  3. The command is recorded with VAD and transcribed by Groq Whisper
     (offline Vosk fallback).
  4. Rules classify it (LFM2 fallback for odd phrasings); dialog responds.
     Facts (prices/allergens/bill) stay deterministic.

Run:  ./venv/bin/python wake_listen.py
Stop: Ctrl-C
"""
import json
import os
import sys
import time

from vosk import Model, SetLogLevel

import config
import dialog
import intents
import kds_data
import lang
import llm
import mqtt_bus
import payments
import responses
import settings
import stt
from audio import AudioCapture
from session import Session
from tts import speak
from wake import WakeDetector

SetLogLevel(-1)

_LLM_ON = False
_MQTT = None  # MQTT client or None


def _cart_sig(session):
    return tuple((l["dish"]["name"], l["qty"]) for l in session.cart)


def _handle_button(key: str, tbl, client):
    """The panel's three front buttons — a silent way to get service, so guests
    aren't forced to talk (loud room, shy guest, or the assistant is off).

      0 · left   → call a waiter
      1 · middle → show the bill / pay QR on the screen
      2 · right  → mute / unmute the assistant
    """
    session = tbl["session"]
    if key == "0":
        mqtt_bus.publish_event(client, "staff_called", table=config.TABLE_ID)
        speak("Of course — I've called a server for you.")
        print("  [button] waiter called", flush=True)

    elif key == "1":
        if session.is_empty():
            speak("There's nothing on your bill yet.")
            return
        total = session.total()
        url, ref = payments.upi_url(total, config.TABLE_ID)
        try:
            kds_data.record_payment(config.TABLE_ID, total, ref)
        except Exception as e:
            print(f"  (payment log failed: {e})", flush=True)
        client.publish(mqtt_bus.T_PAY, json.dumps(
            {"amount": total, "upi_url": url, "ref": ref,
             "vpa": settings.get("upi_vpa", config.UPI_VPA)}), retain=True)
        mqtt_bus.publish_event(client, "pay_requested",
                               table=config.TABLE_ID, total=total)
        speak(f"Your bill is {total:.0f} rupees. The QR code is on your screen.")
        print(f"  [button] bill shown (₹{total:.0f})", flush=True)

    elif key == "2":
        now_muted = settings.get("assistant_state") != "muted"
        state = "muted" if now_muted else "active"
        settings.save({"assistant_state": state})
        client.publish(mqtt_bus.T_ASSISTANT, state, retain=True)
        print(f"  [button] assistant {'muted' if now_muted else 'unmuted'}", flush=True)
        if not now_muted:                 # speak only when turning sound back on
            speak("I'm listening again.")


def understand(transcript: str, session) -> dict:
    """Work out what the guest wants.

    Online: straight to the cloud LLM — it's fast (~0.4 s) and handles anything.

    Offline: the on-device model takes ~9 s, so try the rule parser FIRST. It is
    instant and reliably right for the common commands (order X, what's my bill,
    remove the naan, what's in the pizza). Only genuinely unusual phrasing falls
    through to the slow local model. Most turns end up instant instead of 9 s.
    """
    if settings.force_local():
        rules = intents.parse_intent(transcript)
        if rules["intent"] not in ("unknown", "smalltalk"):
            print("  (rules — instant)", flush=True)
            return rules

    if _LLM_ON:
        try:
            return llm.understand(transcript, session)
        except Exception as e:
            print(f"  (LLM unavailable, using rules: {e})", flush=True)
    return intents.parse_intent(transcript)


def converse(capture, model, session, first_time: bool) -> None:
    """Hold a multi-turn conversation until the guest goes quiet or says they're
    done. No wake word needed between turns."""
    speak(responses.WELCOME if first_time else responses.greeting())

    misses = 0
    while True:
        capture.flush()  # drop our own speech before listening again
        pcm = stt.record_utterance(capture)

        if pcm is None:
            # Guest didn't say anything -> they're done for now. Sleep quietly;
            # no nagging "I didn't catch that".
            return

        transcript, engine, wlang = stt.transcribe(pcm, vosk_model=model)
        if not transcript:
            misses += 1
            if misses >= 2:
                return
            speak("Sorry, I didn't catch that — could you say it again?")
            continue
        misses = 0

        print(f'  guest said ({engine}/{wlang}): "{transcript}"', flush=True)
        t0 = time.time()
        result = understand(transcript, session)
        # Rich one-liner so the web Terminal shows what actually happened.
        bits = [f"intent={result['intent']}", f"in {time.time() - t0:.1f}s"]
        if result.get("items"):
            bits.append("items=" + ",".join(f"{i['quantity']}x{i['dish']['name']}"
                                            for i in result["items"]))
        elif result.get("dish"):
            bits.append(f"dish={result['dish']['name']}")
        if result.get("item"):
            bits.append(f"service={result['item']}")
        bits.append(f"cart={sum(l['qty'] for l in session.cart)} items "
                    f"₹{session.total():.0f}")
        print("  " + " · ".join(bits), flush=True)

        before = _cart_sig(session)
        det = dialog.handle(result, session)   # updates session; exact/grounded reply

        # Fact-critical intents must speak the exact numbers/allergens. Everything
        # else speaks the LLM's warm, natural reply (falls back to det if absent).
        # These must speak the real data — prices, allergens, and the actual list
        # of dishes. Everything else uses the LLM's warmer wording.
        FACT = {"check_bill", "split_bill", "pay", "ask_ingredient", "ask_allergen",
                "show_menu", "show_category"}
        use_llm = result["intent"] not in FACT and bool(result.get("reply"))
        reply = result["reply"] if use_llm else det

        if lang.is_english(wlang):
            speak(reply)
        else:
            # LLM replies are already in the guest's language; translate det ones.
            if not use_llm:
                reply = llm.translate(reply, lang.display_name(wlang))
            speak(reply, lang.espeak_code(wlang))

        # Publish to the bus when the order changed; the display service (and any
        # future subscriber) reacts. Also emit events for kitchen/staff later.
        if _MQTT:
            if _cart_sig(session) != before:
                mqtt_bus.publish_order(_MQTT, session)
            if result["intent"] == "call_staff":
                mqtt_bus.publish_event(_MQTT, "staff_called", table=config.TABLE_ID)
            elif result["intent"] == "request_item" and result.get("item"):
                # Actually tell the staff — otherwise "I'll ask a server" is a lie.
                mqtt_bus.publish_event(_MQTT, "service_request", table=config.TABLE_ID,
                                       item=result["item"],
                                       quantity=result.get("quantity", 1))
            elif result["intent"] == "pay" and not session.is_empty():
                # Put a scannable UPI QR on the table's ePaper straight away and
                # log the bill so the payment watcher can settle it.
                total = session.total()
                url, ref = payments.upi_url(total, config.TABLE_ID)
                try:
                    kds_data.record_payment(config.TABLE_ID, total, ref)
                except Exception as e:
                    print(f"  (payment log failed: {e})", flush=True)
                _MQTT.publish(mqtt_bus.T_PAY, json.dumps(
                    {"amount": total, "upi_url": url, "ref": ref,
                     "vpa": config.UPI_VPA}), retain=True)
                mqtt_bus.publish_event(_MQTT, "pay_requested",
                                       table=config.TABLE_ID, total=total)

        # Keep short conversation memory so corrections / pronouns resolve.
        session.remember("user", transcript)
        session.remember("assistant", reply)

        if result["intent"] in ("end", "end_conversation"):
            return  # closing line already spoken


def main() -> None:
    if not os.path.isdir(config.VOSK_MODEL_PATH):
        sys.exit(f"\n  ERROR: Vosk model not found at {config.VOSK_MODEL_PATH}\n")

    print("Loading models...", flush=True)
    model = Model(config.VOSK_MODEL_PATH)     # Vosk: offline STT fallback
    detector = WakeDetector()                 # openWakeWord: wake detection
    tbl = {"session": Session(), "welcomed": False, "last": time.time()}

    global _LLM_ON, _MQTT
    _LLM_ON = llm.is_available()

    def _on_bus(client, userdata, msg):
        """Kitchen says the table was served -> the party is done. Start a fresh
        session so the NEXT guests never inherit the old cart/bill.
        Also handles the three physical buttons on the panel."""
        if msg.topic == mqtt_bus.T_KITCHEN and msg.payload == b"served":
            if tbl["session"].cart or tbl["welcomed"]:
                tbl["session"] = Session()
                tbl["welcomed"] = False
                print("  [table] served -> session reset for next guests", flush=True)
                mqtt_bus.publish_order(client, tbl["session"])

        elif msg.topic == mqtt_bus.T_BUTTON:
            _handle_button(msg.payload.decode().strip(), tbl, client)

    try:
        _MQTT = mqtt_bus.make_client(f"voice-table-{config.TABLE_ID}", on_message=_on_bus)
        _MQTT.subscribe(mqtt_bus.T_KITCHEN)
        _MQTT.subscribe(mqtt_bus.T_BUTTON)
    except Exception as e:
        print(f"  (MQTT bus unavailable: {e})", flush=True)
        _MQTT = None
    if config.OWW_IS_CUSTOM:
        print(f"  Wake word: “{config.WAKE_PHRASE}” (openWakeWord, custom model)", flush=True)
    else:
        print(f"  Wake word: “{config.WAKE_PHRASE}” — TEMP: engine listens for “Hey Jarvis” "
              f"until models/hey_lumina.onnx is added", flush=True)
    print(f"  Command STT: {'Groq Whisper' if config.GROQ_API_KEY else 'Vosk (offline)'}", flush=True)
    print(f"  LFM2 fallback: {'ON' if _LLM_ON else 'OFF'}", flush=True)
    print(f"  MQTT bus: {'ON' if _MQTT else 'OFF'}", flush=True)
    if _MQTT:
        mqtt_bus.publish_order(_MQTT, tbl["session"])   # opening (empty) screen
        mqtt_bus.publish_status(_MQTT, "idle")

    last_trigger = 0.0

    print(
        f'\n  Lumina Desk is listening. Say "{config.WAKE_PHRASE}", then a command.\n'
        f"  Ctrl-C to stop.\n",
        flush=True,
    )

    with AudioCapture() as capture:
        while True:
            frame = capture.read(timeout=2.0)     # int16 mono @16k
            score = detector.score(frame)

            now = time.time()
            # Safety net: an empty table left idle for a long time starts fresh,
            # so a forgotten greeting never carries into the next party.
            if (tbl["welcomed"] and not tbl["session"].cart
                    and now - tbl["last"] > config.SESSION_IDLE_RESET_SEC):
                tbl["session"] = Session()
                tbl["welcomed"] = False

            # Staff can switch the assistant off from the console or a panel
            # button; the service keeps running, it just stops responding.
            if settings.get("assistant_state") == "off":
                continue

            thresh = float(settings.get("wake_threshold", config.OWW_THRESHOLD))
            if score >= thresh and (now - last_trigger) > config.WAKE_COOLDOWN_SEC:
                last_trigger = now
                print(f"\n  >>> WAKE ({score:.2f})", flush=True)

                converse(capture, model, tbl["session"], first_time=not tbl["welcomed"])
                tbl["welcomed"] = True
                tbl["last"] = time.time()

                detector.reset()
                capture.flush()
                last_trigger = time.time()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped.")
