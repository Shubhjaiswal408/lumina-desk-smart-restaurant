"""One keep-alive HTTPS session for every cloud call.

Speech-to-text and understanding both hit api.groq.com, twice per turn. Opening
a fresh TCP+TLS connection each time costs ~85 ms of handshake before a single
byte of useful work happens; reusing one connection removes that.

warm() exists because the connection goes cold when a table is idle. The moment
the wake word fires we know a request is coming in a second or two, so we open
the connection on a background thread while the guest is still talking.
"""
import threading

import requests

import config

_session = requests.Session()
# One connection is all we need per host, but allow a couple so a warm-up in
# flight never blocks a real request.
_session.mount("https://", requests.adapters.HTTPAdapter(
    pool_connections=2, pool_maxsize=4, max_retries=0))

_warming = threading.Lock()


def session() -> requests.Session:
    return _session


def warm():
    """Open (or refresh) the TLS connection in the background. Never raises."""
    if not _warming.acquire(blocking=False):
        return                                    # one warm-up at a time is plenty

    def _go():
        try:
            _session.head(config.GROQ_CHAT_URL, timeout=3)
        except Exception:
            pass                                  # offline is fine; we just skip it
        finally:
            _warming.release()

    threading.Thread(target=_go, daemon=True).start()
