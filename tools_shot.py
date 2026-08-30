"""Screenshot the admin console for the docs.

chromium's --screenshot fires under "virtual time", which starves the app's
fetch/WebSocket and captures an empty board. So we drive a real headless
browser over the DevTools protocol instead: navigate, log in the way a human
does, wait in REAL time for the data to arrive, then capture.

Earlier versions loaded a `static/_shot.html` shim that no longer exists and
skipped the PIN entirely, so every shot came back as the lock screen. This
walks the keypad instead — one click per digit, same as a member of staff.

Usage:
  ./venv/bin/python tools_shot.py                 # all seven pages -> docs/images
  ./venv/bin/python tools_shot.py /menu out.png   # one route
"""
import base64
import json
import os
import subprocess
import sys
import time
import urllib.request

import websockets.sync.client as wsc

PORT = 9333
W, H = 1400, 900
BASE = "http://localhost:8000/admin"

# route -> (filename, javascript to run once the page has settled)
PAGES = {
    "/kitchen":   ("console-kitchen.png", ""),
    "/analytics": ("console-analytics.png", ""),
    "/menu":      ("console-menu.png", ""),
    "/payments":  ("console-payments.png", _GEN := (
        "(()=>{const b=[...document.querySelectorAll('button')]"
        ".find(e=>e.textContent.trim()==='Generate'); if(b) b.click();})()")),
    "/orders":    ("console-orders.png", ""),
    "/terminal":  ("console-terminal.png", ""),
    "/settings":  ("console-settings.png", ""),
}


def _targets():
    with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json") as r:
        return json.load(r)


def _pin_digit(d):
    return (f"(()=>{{const b=[...document.querySelectorAll('button')]"
            f".find(e=>e.textContent.trim()==='{d}'); if(b) b.click();"
            f" return !!b;}})()")


def shoot_all(pages=None, out_dir="docs/images", pin=None):
    import config
    import settings
    pin = pin or str(settings.get("admin_pin", config.ADMIN_PIN))
    pages = pages or PAGES

    chrome = subprocess.Popen(
        ["chromium", "--headless=new", "--disable-gpu", "--no-sandbox",
         "--hide-scrollbars", "--force-device-scale-factor=1",
         f"--remote-debugging-port={PORT}", f"--window-size={W},{H}", "about:blank"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(60):
            try:
                page = [t for t in _targets() if t["type"] == "page"][0]
                break
            except Exception:
                time.sleep(0.5)
        else:
            raise RuntimeError("devtools never became ready")

        with wsc.connect(page["webSocketDebuggerUrl"], max_size=64 * 1024 * 1024) as ws:
            n = [0]

            def cmd(method, **params):
                n[0] += 1
                i = n[0]
                ws.send(json.dumps({"id": i, "method": method, "params": params}))
                while True:
                    msg = json.loads(ws.recv())
                    if msg.get("id") == i:
                        return msg.get("result", {})

            def js(expr):
                return cmd("Runtime.evaluate", expression=expr,
                           returnByValue=True).get("result", {}).get("value")

            cmd("Page.enable")
            cmd("Runtime.enable")
            cmd("Emulation.setDeviceMetricsOverride",
                width=W, height=H, deviceScaleFactor=2, mobile=False)
            cmd("Page.navigate", url=BASE)
            time.sleep(6)                       # bundle + first fetch

            for d in pin:                       # the keypad auto-submits at 4
                js(_pin_digit(d))
                time.sleep(0.4)
            time.sleep(3)

            os.makedirs(out_dir, exist_ok=True)
            for route, (name, extra) in pages.items():
                js(f"location.hash = '#{route}'")
                time.sleep(5)                   # real seconds: fetch + socket land
                if extra:
                    js(extra)
                    time.sleep(3)
                shot = cmd("Page.captureScreenshot", format="png")
                path = os.path.join(out_dir, name)
                with open(path, "wb") as f:
                    f.write(base64.b64decode(shot["data"]))
                print("  " + path)
    finally:
        chrome.terminate()


if __name__ == "__main__":
    if len(sys.argv) > 2:
        route, out = sys.argv[1], sys.argv[2]
        shoot_all({route: (os.path.basename(out), "")},
                  out_dir=os.path.dirname(out) or ".")
    else:
        shoot_all()
