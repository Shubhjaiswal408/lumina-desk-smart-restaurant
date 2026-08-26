"""Runtime settings for Lumina Desk — editable from the web console.

`config.py` holds the defaults (and machine-specific things like audio device
ids). Anything a manager might reasonably change lives here instead, in
`settings.json`, so it can be edited from the Settings page without SSH.

Every reader calls get() which re-reads the file when it changes (cheap mtime
check), so all four services pick up a change within a second — no restart.
"""
import json
import os
import threading
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import config

_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")
_lock = threading.Lock()
_cache: dict = {}
_mtime = 0.0

DEFAULTS = {
    # --- brains ---
    # "auto"    : cloud when reachable, local as fallback (recommended)
    # "online"  : force cloud (Groq Whisper + Groq LLM) — fastest, most accurate
    # "offline" : force local (Vosk + LFM2) — no internet needed at all
    "mode": "auto",
    "groq_api_key": "",            # blank -> falls back to the .groq_key file

    # --- assistant state (controlled from the console / panel buttons) ---
    # "active" : listens and speaks
    # "muted"  : microphone CLOSED (device released). Screen + panel buttons
    #            still work, and the panel's mute button turns it back on.
    # "off"    : as muted, but the panel's mute button won't undo it — staff
    #            have to switch it back on from the console.
    "assistant_state": "active",

    # --- restaurant ---
    "restaurant_name": "Lumina",
    "table_id": config.TABLE_ID,

    # --- private to this deployment (never committed; lives in settings.json) ---
    "admin_pin": config.ADMIN_PIN,
    "payment_email": config.PAYMENT_EMAIL,

    # --- billing ---
    "tax_mode": "inclusive",       # inclusive | exclusive | none
    "tax_rate": 5.0,               # percent
    "upi_vpa": config.UPI_VPA,
    "upi_payee": config.UPI_PAYEE_NAME,
    "feedback_url": "",

    # --- voice ---
    # "natural" : online neural voices (Indian English, Hindi, Gujarati).
    #             Warmer, but ~600 ms slower to start; falls back to Piper.
    # "local"   : Piper only. Faster and works with no internet at all.
    "tts_engine": "natural",
    # Neerja's default pace is unhurried for a counter. A nudge shortens every
    # reply without sounding rushed. Edge syntax, e.g. "+0%", "+12%", "-5%".
    "tts_rate": "+20%",
    # Seconds of near-silent lead-in before each reply. The reSpeaker's DSP eats
    # the start of every line; this gives it something to eat that isn't speech.
    # Raise it if the first word still gets clipped, lower it for less delay.
    "tts_lead_in": 0.6,

    # --- voice tuning ---
    "wake_threshold": config.OWW_THRESHOLD,
    "vad_silence_sec": config.VAD_SILENCE_SEC,
    "reply_language": "auto",      # auto | en | hi ...
}


def _load() -> dict:
    global _cache, _mtime
    try:
        m = os.path.getmtime(_PATH)
    except OSError:
        return {**DEFAULTS}
    if m != _mtime or not _cache:
        with _lock:
            try:
                with open(_PATH) as f:
                    _cache = {**DEFAULTS, **json.load(f)}
                _mtime = m
            except Exception:
                _cache = {**DEFAULTS}
    return _cache


def all_settings() -> dict:
    return {**_load()}


def get(key: str, default=None):
    return _load().get(key, DEFAULTS.get(key, default))


def save(patch: dict) -> dict:
    """Merge `patch` into settings.json and return the full settings."""
    global _mtime
    cur = {**_load(), **{k: v for k, v in patch.items() if k in DEFAULTS}}
    with _lock:
        with open(_PATH, "w") as f:
            json.dump(cur, f, indent=2)
        _mtime = 0.0          # force re-read next get()
    return cur


# ---- convenience for the services ----

def groq_key() -> str:
    """Key from settings, else the .groq_key file. Empty in offline mode."""
    if get("mode") == "offline":
        return ""
    return (get("groq_api_key") or config.GROQ_API_KEY or "").strip()


def use_cloud() -> bool:
    return get("mode") != "offline" and bool(groq_key())


def force_local() -> bool:
    return get("mode") == "offline"


def feedback_url(table: str = "") -> str:
    """The feedback form link, with the guest's table already filled in.

    Google Forms will hand you a "pre-filled link" containing sample answers.
    Put the literal word TABLE in the table question, paste the resulting link
    into Settings, and every response arrives tagged with the table it came
    from — the guest never has to know their table number, let alone type it.

    Any other link is returned untouched, so a plain form URL still works.
    """
    url = (get("feedback_url", "") or "").strip()
    if not url or not table:
        return url
    parts = urlsplit(url)
    if not parts.query:
        return url
    pairs = parse_qsl(parts.query, keep_blank_values=True)
    # Only swap a value that is exactly our placeholder — never touch the form
    # id or Google's own parameters.
    filled = [(k, table if v == "TABLE" else v) for k, v in pairs]
    if filled == pairs:
        return url
    return urlunsplit(parts._replace(query=urlencode(filled)))
