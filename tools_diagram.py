"""Render the README's diagrams to PNG (light + dark).

The ASCII art the README shipped with is fine in a terminal and unreadable on
GitHub on a phone. These draw the same three things properly: what talks to
what, what happens between the guest speaking and the reply, and which wire
goes where.

Everything here is derived from the code — service names match the systemd
units, topics match mqtt_bus.py, ports match config.py. If you rename a
service, rename it here too.

Usage:  ./venv/bin/python tools_diagram.py
"""
import os
import subprocess
import tempfile

OUT_DIR = "docs/images"

LIGHT = dict(surface="#fcfcfb", ink="#0b0b0b", ink2="#52514e", muted="#898781",
             line="#c3c2b7", card="#ffffff", ring="rgba(11,11,11,0.12)",
             pi="#2a78d6", cloud="#4a3aa7", edge="#1baf7a", warn="#eb6834",
             band="#f2f1ec")
DARK = dict(surface="#1a1a19", ink="#ffffff", ink2="#c3c2b7", muted="#898781",
            line="#383835", card="#232322", ring="rgba(255,255,255,0.12)",
            pi="#3987e5", cloud="#9085e9", edge="#199e70", warn="#d95926",
            band="#232322")

FONT = "system-ui,-apple-system,Segoe UI,sans-serif"


def _open(w, h, c):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}" font-family="{FONT}">'
            f'<rect width="{w}" height="{h}" fill="{c["surface"]}"/>'
            f'<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" '
            f'markerWidth="6" markerHeight="6" orient="auto-start-reverse">'
            f'<path d="M0,0 L10,5 L0,10 z" fill="{c["line"]}"/></marker>'
            f'<marker id="ac" viewBox="0 0 10 10" refX="9" refY="5" '
            f'markerWidth="6" markerHeight="6" orient="auto-start-reverse">'
            f'<path d="M0,0 L10,5 L0,10 z" fill="{c["cloud"]}"/></marker></defs>')


def _card(x, y, w, h, c, fill=None, stroke=None, dash=""):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" '
            f'fill="{fill or c["card"]}" stroke="{stroke or c["ring"]}" '
            f'stroke-width="1"{f" stroke-dasharray=\"{dash}\"" if dash else ""}/>')


def _t(x, y, s, size=13, c="#000", weight="400", anchor="start"):
    return (f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" '
            f'text-anchor="{anchor}" fill="{c}">{s}</text>')


def _arrow(x1, y1, x2, y2, c, marker="a", dash=""):
    return (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{c}" '
            f'stroke-width="1.6" marker-end="url(#{marker})"'
            f'{f" stroke-dasharray=\"{dash}\"" if dash else ""}/>')


# --------------------------------------------------------------------------
def architecture(c):
    W, H = 1100, 620
    p = [_open(W, H, c)]
    a = p.append
    a(_t(32, 40, "How the pieces fit together", 21, c["ink"], "600"))
    a(_t(32, 64, "One Raspberry Pi 5 runs everything. The cloud is optional — "
                 "lose the internet and it keeps taking orders.", 13.5, c["ink2"]))

    # --- cloud (optional) ---
    a(_card(660, 92, 408, 96, c, stroke=c["cloud"], dash="5 4"))
    a(_t(676, 116, "Cloud — optional", 13, c["cloud"], "600"))
    a(_t(676, 138, "Groq Whisper (speech → text) · Groq LLM (understanding)",
         11.5, c["ink2"]))
    a(_t(676, 157, "Edge neural voice — Indian English, Hindi, Gujarati",
         11.5, c["ink2"]))
    a(_t(676, 178, "Offline fallback: Vosk · LFM2 via Ollama · Piper", 11.5, c["muted"]))

    # --- the table (guest side) ---
    a(_card(32, 212, 246, 300, c, fill=c["band"], stroke=c["line"], dash="5 4"))
    a(_t(48, 238, "AT THE TABLE", 11.5, c["muted"], "600"))
    for i, (name, sub) in enumerate([
            ("reSpeaker XVF3800", "4-mic array, USB"),
            ("Speaker", "3.5 mm or USB"),
            ("ePaper panel 800×480", "reTerminal E1002")]):
        y = 256 + i * 84
        a(_card(48, y, 214, 66, c))
        a(_t(64, y + 27, name, 13, c["ink"], "600"))
        a(_t(64, y + 46, sub, 11.5, c["muted"]))

    # --- the Pi ---
    a(_card(330, 212, 318, 300, c, stroke=c["pi"]))
    a(_t(346, 238, "RASPBERRY PI 5", 11.5, c["pi"], "600"))
    for i, (name, sub) in enumerate([
            ("lumina-voice", "wake word, STT, dialog, TTS"),
            ("mosquitto", "MQTT bus — everything talks here"),
            ("lumina-display", "renders 800×480, drives the panel"),
            ("lumina-kds", "FastAPI + web console, :8000")]):
        y = 254 + i * 62
        a(_card(346, y, 286, 50, c))
        a(_t(362, y + 21, name, 12.5, c["ink"], "600"))
        a(_t(362, y + 38, sub, 11, c["muted"]))
    a(_t(346, 500, "SQLite (lumina.db) — orders, payments, menu overrides",
         11, c["muted"]))

    # --- staff ---
    a(_card(700, 212, 368, 300, c, fill=c["band"], stroke=c["line"], dash="5 4"))
    a(_t(716, 238, "STAFF — ANY BROWSER ON THE WIFI", 11.5, c["muted"], "600"))
    for i, (name, sub) in enumerate([
            ("Kitchen board", "tickets arrive live, tap Start / Ready / Served"),
            ("Menu", "prices, allergens, mark a dish sold out"),
            ("Payments", "dynamic UPI QR per bill + webhook"),
            ("Analytics · Orders · Terminal", "revenue, history, live logs")]):
        y = 254 + i * 62
        a(_card(716, y, 336, 50, c))
        a(_t(732, y + 21, name, 12.5, c["ink"], "600"))
        a(_t(732, y + 38, sub, 11, c["muted"]))

    # --- arrows ---
    a(_arrow(266, 292, 342, 292, c["line"]))          # mic -> Pi
    a(_arrow(342, 376, 266, 376, c["line"]))          # Pi -> speaker
    a(_arrow(342, 460, 266, 460, c["line"]))          # Pi -> panel
    a(_arrow(648, 300, 712, 300, c["line"]))          # Pi -> staff
    a(_arrow(712, 340, 648, 340, c["line"]))          # staff -> Pi
    a(_arrow(576, 208, 656, 172, c["cloud"], "ac", "5 4"))
    a(_t(468, 198, "when online", 11, c["cloud"]))
    a(_t(272, 284, "voice", 10.5, c["muted"], anchor="start"))
    a(_t(272, 368, "reply", 10.5, c["muted"], anchor="start"))
    a(_t(272, 452, "screen", 10.5, c["muted"], anchor="start"))
    a(_t(654, 292, "orders", 10.5, c["muted"]))
    a(_t(654, 356, "status", 10.5, c["muted"]))

    a(_t(32, H - 20, "Add a second table and nothing changes: it is one more "
                     "publisher on the same bus.", 11.5, c["muted"]))
    a("</svg>")
    return W, H, "".join(p)


# --------------------------------------------------------------------------
def pipeline(c):
    W, H = 1100, 418
    p = [_open(W, H, c)]
    a = p.append
    a(_t(32, 40, "What happens when a guest speaks", 21, c["ink"], "600"))
    a(_t(32, 64, "“Hey Lumina, one large Margherita” — every stage, in order, "
                 "with what it costs.", 13.5, c["ink2"]))

    steps = [
        ("1", "Wake word", "openWakeWord runs\nhey_lumina.onnx\non-device", "~0 ms"),
        ("2", "Capture", "VAD records exactly\none sentence, drops\nnoise", "0.6 s pause"),
        ("3", "Speech → text", "Groq Whisper, primed\nwith the live menu.\nVosk offline", "264 ms"),
        ("4", "Understand", "Rules first (<5 ms).\nCloud LLM only for\nreal conversation", "5–500 ms"),
        ("5", "Compute", "menu.py + session.py\ndo the money, time\nand allergens", "<1 ms"),
        ("6", "Speak + show", "Neural voice replies;\nthe panel redraws\nfrom the same state", "250–700 ms"),
    ]
    x0, bw, gap = 32, 158, 12
    for i, (n, title, body, cost) in enumerate(steps):
        x = x0 + i * (bw + gap)
        a(_card(x, 104, bw, 190, c))
        a(f'<circle cx="{x + 22}" cy="{128}" r="12" fill="{c["pi"]}"/>')
        a(_t(x + 22, 132, n, 12, "#ffffff", "700", "middle"))
        a(_t(x + 42, 132, title, 13, c["ink"], "600"))
        for j, line in enumerate(body.split("\n")):
            a(_t(x + 16, 166 + j * 17, line, 11.2, c["ink2"]))
        a(_t(x + 16, 278, cost, 12, c["edge"], "600"))
        if i < len(steps) - 1:
            a(_arrow(x + bw + 1, 199, x + bw + gap - 2, 199, c["line"]))

    # The lead sentence gets its own line. Setting it inline and starting the
    # body at a guessed x overlapped it — SVG text has no width to measure.
    a(_card(32, 316, 1036, 76, c, fill=c["band"], stroke=c["line"]))
    a(_t(48, 340, "Facts never go to the cloud.", 12.5, c["ink"], "600"))
    a(_t(48, 360, "“What’s my bill”, “how much is a paneer momo”, “what’s in "
                  "this” — the answer is computed from the menu either way, so "
                  "the rule parser answers", 11.5, c["ink2"]))
    a(_t(48, 378, "them in under 5 ms and the model is never asked. That is the "
                  "difference between a 0.5 s reply and a 1.5 s one.",
         11.5, c["ink2"]))
    a("</svg>")
    return W, H, "".join(p)


# --------------------------------------------------------------------------
def wiring(c):
    W, H = 1100, 520
    p = [_open(W, H, c)]
    a = p.append
    a(_t(32, 40, "What plugs into what", 21, c["ink"], "600"))
    a(_t(32, 64, "Four cables. No soldering, no GPIO wiring, no level shifters.",
         13.5, c["ink2"]))

    a(_card(400, 130, 300, 220, c, stroke=c["pi"]))
    a(_t(550, 162, "Raspberry Pi 5", 15, c["ink"], "600", anchor="middle"))
    a(_t(550, 186, "4 GB is enough · 32 GB card", 11.5, c["muted"], anchor="middle"))
    for i, line in enumerate(("Raspberry Pi OS (64-bit)", "USB-C power, 5 V 5 A",
                              "Wi-Fi or Ethernet", "console served on :8000")):
        a(_t(550, 224 + i * 24, line, 12, c["ink2"], anchor="middle"))

    items = [
        (32, 120, "reSpeaker XVF3800", "USB-A",
         "4-mic array with echo\ncancellation. Shows up as\nan ALSA capture card.", True),
        (32, 282, "Speaker", "3.5 mm jack",
         "Any powered speaker.\nUSB works too — set it in\nconfig.PLAYBACK_DEVICE.", True),
        (768, 120, "reTerminal E1002", "USB-C (CH340)",
         "800×480 colour ePaper.\nAppears as /dev/ttyUSB*.\nHolds its image unpowered.", False),
        (768, 282, "Your phone / laptop", "same Wi-Fi",
         "Open http://<pi>:8000\nfor the staff console.\nNothing to install.", False),
    ]
    for x, y, name, how, body, left in items:
        a(_card(x, y, 300, 122, c))
        a(_t(x + 16, y + 26, name, 13.5, c["ink"], "600"))
        a(_t(x + 16, y + 46, how, 11.5, c["edge"], "600"))
        for j, line in enumerate(body.split("\n")):
            a(_t(x + 16, y + 68 + j * 16, line, 11.2, c["ink2"]))
        ey = 200 if y < 200 else 290
        if left:
            a(_arrow(x + 302, y + 60, 396, ey, c["line"]))
        else:
            a(_arrow(x - 2, y + 60, 704, ey, c["line"]))

    a(_card(32, 428, 1036, 74, c, fill=c["band"], stroke=c["line"]))
    a(_t(48, 452, "If you only have the Pi and a speaker, it still works.",
         12, c["ink"], "600"))
    a(_t(48, 472, "The panel is optional — the console shows everything the "
                  "table screen would.", 11.5, c["ink2"]))
    a(_t(48, 490, "It is the part guests notice, though: no glare, no backlight, "
                  "and it keeps the bill on screen with the power off.",
         11.5, c["ink2"]))
    a("</svg>")
    return W, H, "".join(p)


def render(fn, name):
    for mode, c in (("light", LIGHT), ("dark", DARK)):
        w, h, svg = fn(c)
        out = os.path.join(OUT_DIR, f"{name}.png" if mode == "light"
                           else f"{name}-dark.png")
        html = (f'<!doctype html><meta charset="utf-8"><style>html,body'
                f'{{margin:0;padding:0;background:{c["surface"]}}}</style>{svg}')
        with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as f:
            f.write(html)
            path = f.name
        try:
            subprocess.run(
                ["chromium", "--headless=new", "--disable-gpu", "--no-sandbox",
                 "--hide-scrollbars", "--force-device-scale-factor=2",
                 f"--screenshot={out}", f"--window-size={w},{h}", f"file://{path}"],
                check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        finally:
            os.unlink(path)
        print("  " + out)


if __name__ == "__main__":
    os.makedirs(OUT_DIR, exist_ok=True)
    render(architecture, "diagram-architecture")
    render(pipeline, "diagram-pipeline")
    render(wiring, "diagram-wiring")
