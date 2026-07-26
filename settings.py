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
    # "muted"  : still listens and updates the screen, but stays silent
    # "off"    : ignores the wake word entirely
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
