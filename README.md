# Lumina Desk

**A voice-first smart table for restaurants.** Guests say *"Hey Lumina"* and speak
naturally — order food, ask what's in a dish, check the bill, call a waiter, pay
by UPI. Their order appears live on an ePaper screen at the table and on a
kitchen dashboard, and the whole thing runs from a single Raspberry Pi.

Built to work in a real restaurant: it keeps working when the internet drops,
never invents a dish or an allergen, and the staff can run it from a phone.

```
   Guest speaks                Raspberry Pi 5                     Staff
  ┌──────────────┐      ┌───────────────────────────┐      ┌────────────────┐
  │ "Hey Lumina, │─────▶│  wake word → STT → LLM    │─────▶│ Kitchen board  │
  │  one biryani"│      │  ↓ grounded in menu.py    │      │ (any browser)  │
  └──────────────┘      │  MQTT bus (mosquitto)     │      └────────────────┘
         ▲              └───────────┬───────────────┘               │
         │  spoken reply            │ frames over WiFi              │ "Ready"
         │  (Piper TTS)             ▼                               ▼
         └──────────────────  ePaper panel  ◀───────────  status back to table
```

---

## What it does

**For the guest**
- Wake word **"Hey Lumina"** (custom-trained, fully offline)
- Order, remove, correct — *"no, I said pepperoni"*, *"remove one naan"*, *"add it"*
- Ingredient & allergen answers that come **only from the menu database**
- **Any language** — speaks back in the same one (natural voice for English/Hindi)
- Live ePaper: order, allergens, bill, ready-time, kitchen status, UPI QR
- Pay by scanning a dynamic UPI QR; the screen says thank you when it clears

**For the kitchen & manager** (`http://<pi>.local:8000`, PIN-locked)
- **Kitchen** — live tickets, wait timers, allergen flags, New→Preparing→Ready→Served
- **Table board** — Available / Reserved / Occupied / Cleaning
- **Staff requests** — "bring water" pops a banner until someone hits *Delivered*
- **Broadcast** — push *Today's Special* / *Happy Hour* / *Kitchen Closed* to every table
- **Menu** — add dishes, edit prices, 86 items; changes are live for the voice too
- **Payments** — generate QR, webhook URL, payment log
- **Analytics** — revenue, avg ticket, turnaround, peak hours, busiest tables, popular dishes
- **Terminal** — live service logs in the browser
- **Settings** — online/offline mode, API key, tax, UPI, voice tuning

---

## Hardware

| Part | Used here | Notes |
|---|---|---|
| Compute | Raspberry Pi 5 (8 GB) | Runs everything; one Pi per table |
| Mic | reSpeaker XVF3800 4-Mic Array (USB) | Beamforming + AEC; card 2, 16 kHz |
| Speaker | Powered speaker on the reSpeaker out | `plughw:2,0` |
| Display | Seeed reTerminal E1002 — ESP32-S3 + 7.5" 800×480 colour ePaper | WiFi + battery |
| *(alt)* | XIAO 7.5" ePaper (ESP32-C3, mono, UC8179) | Faster refresh, no colour |

The panel talks to the Pi over **WiFi + MQTT** (battery powered, no cable). It
finds the Pi by **mDNS**, so a DHCP address change doesn't break it.

---

## How it works

### The pipeline
1. **Wake word** — openWakeWord runs a custom `hey_lumina.onnx` on-device.
2. **Capture** — a background thread drains the mic so ALSA never overflows;
   energy-based VAD records one sentence and rejects noise.
3. **Speech-to-text** — Groq Whisper (primed with the live menu so dish names
   transcribe correctly), or Vosk offline.
4. **Understanding** — an LLM sees the conversation, the cart and the real menu.
   It handles corrections, negation, pronouns, multi-item orders and off-menu
   requests. Groq `llama-3.3-70b` online; LFM2-700M via Ollama offline.
5. **Facts stay deterministic** — the model classifies and phrases, but **prices,
   totals and allergens are computed in code** (`menu.py` / `session.py`). Dish
   names are grounded against the menu, so it cannot invent one.
6. **Reply** — Piper neural TTS (resident process, streams audio as it generates).
7. **Publish** — order/status go on MQTT; the display service renders an 800×480
   image with Pillow and streams it to the panel.

### Why an MQTT bus
Everything is decoupled: the voice app publishes, the display service and kitchen
dashboard subscribe. Adding a second table, a kitchen screen or a dashboard is
just another subscriber — no changes to existing code.

```
lumina/table/<id>/order      full order + bill snapshot (retained)
lumina/table/<id>/kitchen    preparing | ready | delayed | served
lumina/table/<id>/pay        UPI link for the ePaper QR
lumina/table/<id>/payment    "paid"
lumina/table/<id>/event      staff_called | service_request | pay_requested
lumina/table/<id>/state      available | reserved | occupied | cleaning
lumina/table/<id>/frame      packed 800×480 image chunks → panel
lumina/broadcast             house announcement to every table
```

---

## Repository layout

```
wake_listen.py      main voice loop: wake → listen → understand → reply
audio.py            background mic capture (kills ALSA overflow)
stt.py              VAD recording + Groq Whisper / Vosk
llm.py              LLM understanding, grounding + safety guards
dialog.py           intent → spoken reply, updates the session
menu.py             menu database, prices, allergens, tax, admin overrides
session.py          per-table cart, bill maths, ETA
tts.py              Piper (resident) + espeak fallback
lang.py             language detection → voice/espeak codes
mqtt_bus.py         topics + publish/subscribe helpers

kds_server.py       FastAPI: dashboard API, WebSocket, table lifecycle, auth
kds_data.py         SQLite: order history, analytics, menu overrides, payments
payments.py         dynamic UPI deep link + QR
payment_watcher.py  settles bills by reading FamApp payment emails (IMAP)
display_service.py  renders + streams frames to the panel
ui_render.py        the 800×480 ePaper design system (Pillow)
settings.py         runtime settings overlay (settings.json)

admin/              React + TypeScript + Tailwind + shadcn/ui console
firmware/           ESP32 sketches (WiFi panel, USB panel, tests)
systemd/            service units — everything auto-starts on boot
training/           notebook to train your own "Hey Lumina" wake word
```

---

## Setup

### 1. System packages
```bash
sudo apt install -y python3-venv python3-scipy python3-sklearn \
    espeak-ng libportaudio2 mosquitto mosquitto-clients avahi-daemon
```

Allow LAN devices to reach the broker — `/etc/mosquitto/conf.d/lumina.conf`:
```
listener 1883 0.0.0.0
allow_anonymous true
persistence true
```

### 2. Python
```bash
python3 -m venv --system-site-packages venv
./venv/bin/pip install sounddevice openwakeword vosk requests paho-mqtt \
    fastapi "uvicorn[standard]" pillow qrcode pyserial
```

### 3. Models (all offline, one-time)
- **Wake word** — train `hey_lumina.onnx` with `training/hey_lumina_advanced.ipynb`
  (Google Colab, free, ~45 min, no voice recording needed) → drop into `models/`.
  Until then it falls back to the built-in `hey_jarvis`.
- **Vosk** (offline STT) — `vosk-model-small-en-us-0.15/` in the project root.
- **Piper** (voice) — binary in `piper/`, voices in `voices/`
  (`en_US-amy-medium`, optional `hi_IN-priyamvada-medium`).
- **Ollama + LFM2** (offline brain) —
  `ollama pull hf.co/LiquidAI/LFM2-700M-GGUF`

### 4. Frontend
```bash
cd admin && npm install && npm run build     # outputs to static/admin/
```

### 5. Services
```bash
sudo cp systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now lumina-voice lumina-display lumina-kds lumina-payments
```

Power on the Pi → everything starts → say **"Hey Lumina"**.
Console: `http://<pi-hostname>.local:8000` (default PIN `0000` — change it).

### 6. The panel
```bash
cp firmware/display_wifi/wifi_secrets.h.example firmware/display_wifi/wifi_secrets.h
# fill in WiFi + your Pi's hostname, then:
arduino-cli compile --upload -p /dev/ttyUSB0 \
  --fqbn 'esp32:esp32:XIAO_ESP32S3:PSRAM=opi,CDCOnBoot=cdc' firmware/display_wifi
```
Unplug USB — it runs on battery over WiFi.

---

## Online vs offline

Set in **Settings → Brain mode**. Applies within a second, no restart.

| Mode | STT | Understanding | Speed | Internet |
|---|---|---|---|---|
| **auto** *(default)* | Groq Whisper → Vosk | Groq 70B → LFM2 | ~0.4 s | not required |
| **online** | Groq Whisper | Groq 70B | ~0.4 s | required |
| **offline** | Vosk | LFM2-700M | ~9 s | **none at all** |

Offline genuinely makes **zero network calls** — wake word, STT, LLM, TTS and the
display all run on the Pi. It is slower and less accurate; that's the honest
trade. `auto` is recommended: cloud speed, local resilience.

---

## Payments

The QR encodes a standard NPCI deep link where **only the amount changes**:

```
upi://pay?pa=<vpa>&pn=<payee>&am=<AMOUNT>&cu=INR&tn=<note>&tr=<ref>
```

A plain UPI QR has **no webhook**, so confirmation works one of three ways:

1. **FamApp email** (`payment_watcher.py`) — FamApp emails the merchant on every
   incoming payment; the watcher reads that mailbox over IMAP and settles the
   matching bill. Needs a Gmail **App Password** in `.gmail_key`.
   Matching is by **amount + recency**, deduplicated by the FamApp
   **transaction ID**, oldest bill first.
2. **A real gateway** — `POST /api/pay/webhook` with
   `{"ref":"LUM07…","status":"success","amount":1250}` is already implemented.
   *Note: that endpoint is LAN-only; an internet PSP needs a public URL (tunnel).*
3. **Manual** — every pending row on the Payments page has a **Mark paid** button.

**Limitation:** two tables owing the exact same amount at the same moment could
mismatch under (1). A real gateway with per-bill references removes that.

---

## Table lifecycle

```
available → occupied → (paid) → cleaning → available
                ↑                              ↓
             reserved  ←──── staff set from console
```

On payment the order is banked to history, then after 45 s (long enough for the
slow colour panel to draw the thank-you) the ticket clears, the voice session
resets so the next party starts fresh, and the table drops to **cleaning**.

---

## Security notes

- The console is behind a **staff PIN**; tokens are in memory and die on restart.
- `/api/pay/webhook` is deliberately unauthenticated so a gateway can reach it —
  **add signature verification before exposing it to the internet.**
- Secrets are gitignored and never committed: `.groq_key`, `.gmail_key`,
  `settings.json`, `firmware/*/wifi_secrets.h`, `lumina.db`.
- `config.py` ships **placeholders only**. Real values (PIN, UPI ID, email) live
  in `settings.json` on the device.

---

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| Panel stuck on an old screen | Pi's IP changed. The firmware resolves mDNS, but check `journalctl -u lumina-display -f` |
| `[pay] no pending bill matched` | Payment arrived with no matching open bill, or older than the 45-min window |
| Wake word too eager / too deaf | Settings → wake sensitivity (0.3–0.7) |
| Guest gets cut off mid-sentence | Settings → end-of-speech pause (raise to 0.8–1.0) |
| Console won't load after restart | Tokens are in-memory — log in again |
| Two dashboards fighting | Fixed: MQTT client ids are randomised per process |

Logs: `journalctl -u lumina-voice -f` (or the **Terminal** page in the console).

---

## Honest limitations

- **Colour ePaper refresh is ~15–20 s.** That's the hardware. A mono UC8179 panel
  refreshes in ~4–6 s and supports partial refresh.
- **One Pi per table.** The dashboard aggregates any number of tables, but each
  needs its own Pi + mic + panel.
- **Offline mode is noticeably slower and less accurate** than cloud.
- **Free-tier Groq has rate limits**; normal conversation is fine.

---

## Licence

MIT
