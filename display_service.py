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


TOPICS = ("order", "kitchen", "pay", "payment", "assistant")


class Screen:
    """What the table should be showing right now.

    Both transports need the same answer to that question — the only difference
    is how the picture reaches the panel. Keeping it here means the USB panel
    gets the pay QR, the thank-you and the kitchen banner too, instead of the
    order screen and nothing else.
    """

    def __init__(self):
        self.order = None
        self.kitchen = None
        self.pay = None
        self.paid = False

    def apply(self, topic: str, payload: bytes) -> bool:
        """Fold one bus message in. Returns True if the picture may have changed."""
        blank = not payload.strip()
        if topic == mqtt_bus.T_ORDER:
            if blank:                       # table cleared after checkout
                self.order = {"table": config.TABLE_ID, "items": []}
                self.pay, self.paid, self.kitchen = None, False, None
                return True
            new = json.loads(payload)
            if not new.get("items"):        # table turned over -> drop pay screen
                self.pay, self.paid = None, False
            self.order = new
            self.kitchen = None             # a fresh order clears old status
            return True
        if topic == mqtt_bus.T_PAY:
            if blank:
                self.pay, self.paid = None, False
            else:
                self.pay, self.paid = json.loads(payload), False
                print("[display-service] pay QR requested", flush=True)
            return True
        if topic == mqtt_bus.T_PAID:
            if payload == b"paid" and self.pay:
                self.paid = True
                print("[display-service] payment confirmed -> thank-you", flush=True)
                return True
            if blank:
                self.paid = False
            return False
        if topic == mqtt_bus.T_KITCHEN:
            self.kitchen = payload.decode()
            return True
        if topic == mqtt_bus.T_ASSISTANT:   # mute badge appears/disappears
            print(f"[display-service] assistant {payload.decode()}", flush=True)
            return True
        return False

    def image(self):
        """The quantised 800x480 image for the current state, or None."""
        if self.order is None:
            return None
        session = Session.from_items(self.order.get("items", []))
        table = self.order.get("table", config.TABLE_ID)
        if self.pay:                        # a bill on screen wins until it's paid
            img = ui_render.render_payment(
                session, self.pay["upi_url"], table=table,
                vpa=self.pay.get("vpa", ""), paid=self.paid)
        else:
            img = ui_render.render_order(
                session, table=table,
                status=self.order.get("status", "Listening"),
                kitchen=self.kitchen)
        return ui_render.to_epaper(img)


def run_wifi():
    # Coalescing + ack flow-control: the color panel takes ~15-20s per refresh,
    # so we never queue frames. While it's refreshing we just remember the latest
    # order; when it acks (or times out) we send the newest state. The panel thus
    # always converges to the current order instead of falling behind.
    screen = Screen()
    st = {"pending": None, "sent": None, "busy": False, "sent_at": 0.0}
    BUSY_TIMEOUT = 35.0

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
            if msg.topic == mqtt_bus.T_PANEL:
                # "online" (retained) = the panel just joined and its screen may
                # be wrong, so push the current state. "alive" is only a presence
                # ping — answering it would redraw a correct screen every minute,
                # and a colour refresh costs ~20 s and real battery.
                if msg.payload == b"online":
                    frame = st["pending"] or st["sent"]
                    if frame is not None:
                        _send(client, frame)
                        print("[display-service] panel joined -> pushing current screen")
                return
            if msg.topic == mqtt_bus.T_ACK:
                st["busy"] = False
                print("[display-service] panel confirmed refresh")
                _maybe_send(client)        # send newer state if one arrived meanwhile
                return

            if screen.apply(msg.topic, msg.payload):
                img = screen.image()
                if img is not None:
                    st["pending"] = _pack(img)
            _maybe_send(client)
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

    screen = Screen()

    def on_message(client, userdata, msg):
        try:
            if screen.apply(msg.topic, msg.payload):
                img = screen.image()
                if img is not None:
                    dm.push(img)      # coalesced + pushed on a worker thread
        except Exception as e:
            print(f"[display-service] error: {e}")

    client = mqtt_bus.make_client(
        "display-service", on_message=on_message,
        topics=(mqtt_bus.T_ORDER, mqtt_bus.T_KITCHEN, mqtt_bus.T_PAY,
                mqtt_bus.T_PAID, mqtt_bus.T_ASSISTANT))
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
