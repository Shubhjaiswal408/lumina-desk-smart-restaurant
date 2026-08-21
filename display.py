"""Pi-side link to the E1002 ePaper display.

Renders the UI (ui_render), packs it to the panel's 2-bit format, and streams it
to the ESP32 firmware over serial. Keep one DisplayLink for the app's lifetime;
opening the port resets the board, so we open once and reuse.
"""
import threading
import time

import numpy as np
import serial

import ui_render

PORT = "/dev/ttyUSB0"
BAUD = 921600
MAGIC = b"LUMIMG"


def _pack(img_p) -> bytes:
    """Pack a P-mode image (palette 0=white,1=black,2=red) to 2 bits/pixel."""
    a = np.asarray(img_p, dtype=np.uint8).reshape(-1)      # 384000 values 0..2
    a = a.reshape(-1, 4)
    packed = (a[:, 0] << 6) | (a[:, 1] << 4) | (a[:, 2] << 2) | a[:, 3]
    return packed.astype(np.uint8).tobytes()


# Bytes are sent paced in chunks: the ESP32 USB-CDC (mono C3) has no flow
# control and overflows on a single 96 KB blast.
_CHUNK = 2048
_CHUNK_DELAY = 0.006


class DisplayLink:
    def __init__(self, port=PORT, baud=BAUD, reset_on_open=True):
        self.ser = serial.Serial(port, baud, timeout=1)
        if reset_on_open:      # CH340 boards need an EN pulse; native-USB don't
            self._reset()
        else:
            time.sleep(0.3)
        self._wait_ready()

    def _reset(self):
        # CH340 auto-reset: RTS->EN. Pulse to reset-to-run (DTR high = not boot).
        self.ser.setDTR(False)
        self.ser.setRTS(True)
        time.sleep(0.15)
        self.ser.setRTS(False)
        time.sleep(0.1)
        self.ser.reset_input_buffer()

    def _wait_ready(self, timeout=6.0):
        t0 = time.time()
        buf = b""
        while time.time() - t0 < timeout:
            buf += self.ser.read(256)
            if b"LUMINA_DISPLAY_READY" in buf:
                print("[display] ready")
                self.ser.reset_input_buffer()
                return True
        # Native-USB boards may already be running (no fresh banner); that's fine.
        print("[display] no READY banner (continuing anyway)")
        self.ser.reset_input_buffer()
        return False

    def push_image(self, img_p) -> bool:
        """Send a packed P-mode image (paced) and wait for the panel's OK."""
        data = _pack(img_p)
        self.ser.reset_input_buffer()
        self.ser.write(MAGIC)
        self.ser.flush()
        for i in range(0, len(data), _CHUNK):
            self.ser.write(data[i:i + _CHUNK])
            self.ser.flush()
            time.sleep(_CHUNK_DELAY)
        # Wait for OK (full refresh: ~4-6 s mono, ~15-20 s color).
        t0 = time.time()
        while time.time() - t0 < 40:
            line = self.ser.readline().decode(errors="replace").strip()
            if not line:
                continue
            print(f"[display] {line}")
            if line == "OK":
                return True
            if line.startswith("ERR"):
                return False
        print("[display] timed out waiting for OK")
        return False

    def show(self, session, **kw) -> bool:
        img = ui_render.to_epaper(ui_render.render_order(session, **kw))
        return self.push_image(img)

    def close(self):
        try:
            self.ser.close()
        except Exception:
            pass


class DisplayManager:
    """Non-blocking display updates for the voice app.

    render() happens on the caller's thread (fast, ~50 ms, a consistent snapshot);
    the slow ~15-20 s serial push runs on a worker thread. Rapid changes are
    coalesced — only the most recent frame is ever pushed.
    """
    def __init__(self, link: "DisplayLink"):
        self.link = link
        self._pending = None
        self._lock = threading.Lock()
        self._event = threading.Event()
        self._stop = False
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    def push(self, img):
        """Queue an already-rendered (quantised) image for the panel."""
        with self._lock:
            self._pending = img
        self._event.set()

    def request(self, session, **kw):
        """Render an order screen now and queue it for the panel."""
        self.push(ui_render.to_epaper(ui_render.render_order(session, **kw)))

    def _worker(self):
        while not self._stop:
            self._event.wait()
            if self._stop:
                return
            with self._lock:
                img = self._pending
                self._pending = None
                self._event.clear()
            if img is not None:
                try:
                    self.link.push_image(img)
                except Exception as e:
                    print(f"[display] push failed: {e}")

    def close(self):
        self._stop = True
        self._event.set()
        self.link.close()


def _detect_port():
    """Pick the connected panel. ttyACM0 = XIAO C3 (mono, native USB, no reset);
    ttyUSB0 = reTerminal E1002 (color, CH340, needs reset)."""
    import os
    if os.path.exists("/dev/ttyACM0"):
        return "/dev/ttyACM0", False   # mono C3, don't reset (native USB)
    if os.path.exists("/dev/ttyUSB0"):
        return "/dev/ttyUSB0", True    # E1002, CH340 needs EN pulse
    return PORT, True


def connect(port=None, baud=BAUD):
    """Open the panel and return a DisplayManager, or None if unavailable."""
    detected, reset = _detect_port()
    port = port or detected
    try:
        link = DisplayLink(port, baud, reset_on_open=reset)
        print(f"[display] connected on {port}")
        return DisplayManager(link)
    except Exception as e:
        print(f"[display] not available ({e}); running voice-only")
        return None


if __name__ == "__main__":
    # Standalone panel check: draw one screen of each kind on whichever panel is
    # plugged in.  ./venv/bin/python display.py
    import sys
    import time as _t

    import menu
    import payments
    from session import Session

    s = Session()
    s.add_dish(menu.find_dish("margherita"), 1, "Large")
    s.add_dish(menu.find_dish("cheese stuffed garlic bread"), 2)
    s.add_dish(menu.find_dish("cold coffee"), 2)

    port, reset = _detect_port()
    print(f"[display] {port} (auto-reset {'on' if reset else 'off'})")
    link = DisplayLink(port, reset_on_open=reset)

    url, _ = payments.upi_url(s.total(), "07")
    screens = [
        ("order",  ui_render.render_order(s, table="07")),
        ("paying", ui_render.render_payment(s, url, table="07", vpa="auntynoz@upi")),
        ("thanks", ui_render.render_payment(s, url, table="07", paid=True)),
    ]
    for name, img in screens:
        t = _t.perf_counter()
        ok = link.push_image(ui_render.to_epaper(img))
        print(f"  {name:<7} {'OK' if ok else 'FAILED'} in {_t.perf_counter() - t:.1f}s")
        if not ok:
            link.close()
            sys.exit(1)
        _t.sleep(2)
    link.close()
    print("panel drew every screen.")
