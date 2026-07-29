"""Lumina Desk — display service.

Renders the screen from the MQTT order topic and gets it onto the panel.

Two transports (config.DISPLAY_TRANSPORT):
  * "wifi"   — stream frames to the battery panel over MQTT (no cable). Resends
               the current frame whenever a panel announces itself ("online").
  * "serial" — push to a USB-connected panel over the serial link.

Run:  ./venv/bin/python display_service.py
"""
import json
import time

import config
import mqtt_bus
import ui_render
from display import _pack
from session import Session


def _render_packed(data: dict, kitchen=None) -> bytes:
    session = Session.from_items(data.get("items", []))
    img = ui_render.render_order(session, table=data.get("table", "07"),
                                 status=data.get("status", "Listening"),
                                 kitchen=kitchen)
    return _pack(ui_render.to_epaper(img))


def run_wifi():
    # Coalescing + ack flow-control: the color panel takes ~15-20s per refresh,
    # so we never queue frames. While it's refreshing we just remember the latest
    # order; when it acks (or times out) we send the newest state. The panel thus
    # always converges to the current order instead of falling behind.
    st = {"pending": None, "sent": None, "busy": False, "sent_at": 0.0,
          "order": None, "kitchen": None, "pay": None, "paid": False,
          "panel_seen": 0.0}
    BUSY_TIMEOUT = 35.0

    def _rerender():
        """Pay screen wins while a bill is awaiting payment."""
        if st["pay"] and st["order"]:
            session = Session.from_items(st["order"].get("items", []))
            img = ui_render.render_payment(
                session, st["pay"]["upi_url"],
                table=st["order"].get("table", "07"),
                vpa=st["pay"].get("vpa", ""), paid=st["paid"])
            st["pending"] = _pack(ui_render.to_epaper(img))
        elif st["order"] is not None:
            st["pending"] = _render_packed(st["order"], st["kitchen"])

    def _send(client, frame):
        st["sent"] = frame
        st["busy"] = True
        st["sent_at"] = time.time()
        mqtt_bus.publish_frame(client, frame)
        print("[display-service] frame -> panel")

    def _maybe_send(client):
        if st["busy"] and time.time() - st["sent_at"] > BUSY_TIMEOUT:
            st["busy"] = False   # ack lost / panel dropped; allow retry
        if not st["busy"] and st["pending"] is not None and st["pending"] is not st["sent"]:
            _send(client, st["pending"])

    def on_message(client, userdata, msg):
        try:
            if msg.topic == mqtt_bus.T_ORDER:
                if not msg.payload.strip():        # table cleared after checkout
                    st["order"] = {"table": config.TABLE_ID, "items": []}
                    st["pay"], st["paid"], st["kitchen"] = None, False, None
                    _rerender()
                    _maybe_send(client)
                    return
                new = json.loads(msg.payload)
                if not new.get("items"):    # table turned over -> drop pay screen
                    st["pay"], st["paid"] = None, False
                st["order"] = new
                st["kitchen"] = None        # a fresh order clears old kitchen status
                _rerender()
                _maybe_send(client)
            elif msg.topic == mqtt_bus.T_PAY:
                if not msg.payload.strip():          # cleared after checkout
                    st["pay"], st["paid"] = None, False
                else:
                    st["pay"], st["paid"] = json.loads(msg.payload), False
                    print("[display-service] pay QR requested", flush=True)
                _rerender()
                _maybe_send(client)
            elif msg.topic == mqtt_bus.T_PAID:
                if msg.payload == b"paid" and st["pay"]:
                    st["paid"] = True
                    _rerender()
                    _maybe_send(client)
                    print("[display-service] payment confirmed -> thank-you screen", flush=True)
                elif not msg.payload.strip():
                    st["paid"] = False
            elif msg.topic == mqtt_bus.T_ASSISTANT:
                _rerender()                 # mute badge appears/disappears
                _maybe_send(client)
                print(f"[display-service] assistant {msg.payload.decode()}", flush=True)
            elif msg.topic == mqtt_bus.T_KITCHEN:
                st["kitchen"] = msg.payload.decode()
                _rerender()
                _maybe_send(client)
            elif msg.topic == mqtt_bus.T_PANEL:
                # "online" (retained) = the panel just joined and its screen may
                # be wrong, so push the current state. "alive" is only a presence
                # ping — answering it would redraw a correct screen every minute,
                # and a colour refresh costs ~20 s and real battery.
                if msg.payload == b"online":
                    frame = st["pending"] or st["sent"]
                    if frame is not None:
                        _send(client, frame)
                        print("[display-service] panel joined -> pushing current screen")
                elif msg.payload == b"alive":
                    st["panel_seen"] = time.time()
            elif msg.topic == mqtt_bus.T_ACK:
                st["busy"] = False
                print("[display-service] panel confirmed refresh")
                _maybe_send(client)        # send newer state if one arrived meanwhile
        except Exception as e:
            print(f"[display-service] error: {e}")

    client = mqtt_bus.make_client(
        "display-service", on_message=on_message,
        topics=(mqtt_bus.T_ORDER, mqtt_bus.T_KITCHEN, mqtt_bus.T_PAY,
                mqtt_bus.T_PAID, mqtt_bus.T_PANEL, mqtt_bus.T_ACK,
                mqtt_bus.T_ASSISTANT))
    print("[display-service] WiFi mode: streaming frames over MQTT (Ctrl-C to stop)")
    _idle(client)


def run_serial():
    import display as display_mod
    dm = None
    for attempt in range(12):
        dm = display_mod.connect()
        if dm:
            break
        print(f"[display-service] panel not ready (try {attempt + 1}); retrying in 3s")
        time.sleep(3)
    if not dm:
        print("[display-service] panel not available after retries; exiting")
        return

    def on_message(client, userdata, msg):
        try:
            data = json.loads(msg.payload)
        except Exception:
            return
        dm.request(Session.from_items(data.get("items", [])),
                   table=data.get("table", "07"), status=data.get("status", "Listening"))
        print(f"[display-service] update ({len(data.get('items', []))} items)")

    client = mqtt_bus.make_client("display-service", on_message=on_message,
                                  topics=(mqtt_bus.T_ORDER,))
    print("[display-service] serial mode: driving USB panel (Ctrl-C to stop)")
    try:
        _idle(client)
    finally:
        dm.close()


def _idle(client):
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[display-service] stopping")
    finally:
        client.loop_stop()


def main():
    if config.DISPLAY_TRANSPORT == "wifi":
        run_wifi()
    else:
        run_serial()


if __name__ == "__main__":
    main()
