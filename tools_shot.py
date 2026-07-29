"""Screenshot the admin console for the docs.

chromium's --screenshot fires under "virtual time", which starves the app's
fetch/WebSocket and captures an empty board. So we drive a real headless
browser over the DevTools protocol instead: navigate, wait in REAL time for the
data to arrive, then capture.

Usage:  ./venv/bin/python tools_shot.py <route> <out.png> [height] [js]

`js` is optional JavaScript run once the page has settled — use it to click into
the state you want to photograph (e.g. press "Generate" so the QR is on screen).
"""
import base64
import json
import subprocess
import sys
import time
import urllib.request

import websockets.sync.client as wsc

PORT = 9333


def _targets():
    with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json") as r:
        return json.load(r)


def shoot(route: str, out: str, height: int = 900, wait: float = 6.0, js: str = ""):
    chrome = subprocess.Popen(
        ["chromium", "--headless=new", "--disable-gpu", "--no-sandbox",
         "--hide-scrollbars", f"--remote-debugging-port={PORT}",
         f"--window-size=1400,{height}", "about:blank"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(40):                      # wait for devtools to come up
            try:
                page = [t for t in _targets() if t["type"] == "page"][0]
                break
            except Exception:
                time.sleep(0.5)
        else:
            raise RuntimeError("devtools never became ready")

        with wsc.connect(page["webSocketDebuggerUrl"], max_size=64 * 1024 * 1024) as ws:
            def cmd(i, method, **params):
                ws.send(json.dumps({"id": i, "method": method, "params": params}))
                while True:
                    msg = json.loads(ws.recv())
                    if msg.get("id") == i:
                        return msg.get("result", {})

            cmd(1, "Page.enable")
            cmd(2, "Page.navigate",
                url=f"http://localhost:8000/static/_shot.html#{route}")
            time.sleep(wait)                     # real seconds: fetch + socket land
            if js:
                cmd(3, "Runtime.evaluate", expression=js, awaitPromise=True)
                time.sleep(3)                    # let the result render
            shot = cmd(4, "Page.captureScreenshot", format="png")
            open(out, "wb").write(base64.b64decode(shot["data"]))
        print(f"saved {out}")
    finally:
        chrome.terminate()


if __name__ == "__main__":
    route, out = sys.argv[1], sys.argv[2]
    h = int(sys.argv[3]) if len(sys.argv) > 3 else 900
    shoot(route, out, h, js=sys.argv[4] if len(sys.argv) > 4 else "")
