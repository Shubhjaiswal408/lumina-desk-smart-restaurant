"""Local MQTT bus for Lumina Desk.

One broker on the Pi ties the pieces together and makes the system extensible:
the voice app publishes order/status/events; the display service (and, later, a
kitchen screen, staff dashboard, WiFi ePaper panels, or more tables) subscribe.

Topic layout (per table):
  lumina/table/<id>/order    retained JSON  — full order + bill snapshot
  lumina/table/<id>/status   retained str   — listening | thinking | idle
  lumina/table/<id>/event    JSON           — item_added, staff_called, pay_requested…
"""
import json
import os
import random
import struct

import paho.mqtt.client as mqtt

import config

BASE = f"lumina/table/{config.TABLE_ID}"
T_ORDER = f"{BASE}/order"
T_STATUS = f"{BASE}/status"
T_EVENT = f"{BASE}/event"
T_FRAME = f"{BASE}/frame"          # packed 800x480 image chunks -> WiFi panel
T_ACK = f"{BASE}/frame/ack"        # panel confirms a rendered frame
T_PANEL = f"{BASE}/panel"          # panel presence ("online")
T_KITCHEN = f"{BASE}/kitchen"      # kitchen -> table status (preparing/ready/served)
T_BUTTON = f"{BASE}/button"        # front panel keys: "0" waiter, "1" bill, "2" mute
T_PAY = f"{BASE}/pay"              # show the UPI QR on the table's ePaper
T_PAID = f"{BASE}/payment"         # "paid" once the money is confirmed

_COMMIT = 0xFFFFFFFF


def make_client(name: str, on_message=None) -> mqtt.Client:
    """Create + connect a background-looping client. Works on paho-mqtt 1.x/2.x.

    The client id gets a random suffix: MQTT kicks off any existing client with
    the same id, so two copies of a service (e.g. a dev instance next to the
    systemd one) would silently disconnect each other.
    """
    cid = f"{name}-{os.getpid()}-{random.randint(1000, 9999)}"
    try:  # paho-mqtt 2.x requires an explicit callback API version
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=cid)
    except (AttributeError, TypeError):
        client = mqtt.Client(client_id=cid)
    if on_message:
        client.on_message = on_message
    client.connect(config.MQTT_HOST, config.MQTT_PORT, keepalive=60)
    client.loop_start()
    return client


def order_payload(session, status: str = "Listening") -> dict:
    return {
        "table": config.TABLE_ID,
        "status": status,
        "items": [{"name": l["dish"]["name"], "qty": l["qty"]} for l in session.cart],
        "subtotal": session.subtotal(),
        "tax": session.tax(),
        "total": session.total(),
        "eta": session.est_prep_time(),
    }


def publish_order(client, session, status: str = "Listening"):
    client.publish(T_ORDER, json.dumps(order_payload(session, status)), retain=True)


def publish_status(client, status: str):
    client.publish(T_STATUS, status, retain=True)


def publish_event(client, etype: str, **data):
    client.publish(T_EVENT, json.dumps({"type": etype, **data}))


def publish_frame(client, packed: bytes, chunk: int = 1024):
    """Stream a packed 800x480 frame to the WiFi panel as offset+data chunks,
    then a commit message telling it to render."""
    for off in range(0, len(packed), chunk):
        client.publish(T_FRAME, struct.pack("<I", off) + packed[off:off + chunk], qos=1)
    client.publish(T_FRAME, struct.pack("<I", _COMMIT) + struct.pack("<I", len(packed)), qos=1)
