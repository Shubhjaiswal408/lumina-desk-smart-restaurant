"""Re-flash the table panel from the console.

Occasionally a panel needs its firmware put back — you changed the WiFi, the
board came back from a bench, or it's showing something from a previous life.
Doing that from the web page means nobody has to find a laptop and remember an
arduino-cli invocation while the restaurant is open.

Which sketch to send is decided by which board answered, not by asking:
  /dev/ttyUSB0  CH340       reTerminal E1002, colour  -> firmware/display_wifi
  /dev/ttyACM0  native USB  XIAO ESP32-C3, mono       -> firmware/display_mono
"""
import os
import subprocess
import threading
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_CLI = os.path.join(_HERE, "tools", "arduino-cli")
_CFG = os.path.join(_HERE, "tools", "arduino-cli.yaml")

# The port says which board it is; config.DISPLAY_TRANSPORT says how this
# deployment talks to it. Both matter — flashing the WiFi firmware onto a panel
# the Pi drives over USB would leave a screen that boots fine and never updates.
BOARDS = {
    "/dev/ttyUSB0": {
        "name": "reTerminal E1002 (colour)",
        "fqbn": "esp32:esp32:XIAO_ESP32S3:PSRAM=opi,CDCOnBoot=cdc",
        "sketch": {"serial": "firmware/display", "wifi": "firmware/display_wifi"},
    },
    "/dev/ttyACM0": {
        "name": "XIAO ESP32-C3 (mono)",
        "fqbn": "esp32:esp32:XIAO_ESP32C3",
        # No WiFi build for the mono panel; it is driven over USB either way.
        "sketch": {"serial": "firmware/display_mono", "wifi": "firmware/display_mono"},
    },
}


def _sketch_for(board: dict) -> str:
    import config
    return board["sketch"].get(config.DISPLAY_TRANSPORT, board["sketch"]["serial"])

# One flash at a time, and never two at once — an interrupted upload leaves a
# panel that won't boot, which is a far worse afternoon than a stale screen.
_lock = threading.Lock()
_state = {"running": False, "started": 0.0, "log": [], "ok": None, "board": ""}


def detect():
    """Which panel is plugged in, if any — at whatever port number it landed on.

    Replugging a cable moves it to ttyUSB1, so match on the family rather than
    the exact path.
    """
    import glob
    for pattern, key in (("/dev/ttyACM*", "/dev/ttyACM0"),
                         ("/dev/ttyUSB*", "/dev/ttyUSB0")):
        found = sorted(glob.glob(pattern))
        if found:
            return found[0], BOARDS[key]
    return None, None


def status() -> dict:
    port, board = detect()
    import config
    return {
        "port": port,
        "board": board["name"] if board else None,
        "sketch": _sketch_for(board) if board else None,
        "transport": config.DISPLAY_TRANSPORT,
        "toolchain": os.path.exists(_CLI),
        "running": _state["running"],
        "ok": _state["ok"],
        "log": _state["log"][-40:],
        "elapsed": round(time.time() - _state["started"], 1) if _state["running"] else 0,
    }


def _run(port: str, board: dict):
    _state.update(running=True, started=time.time(), log=[], ok=None,
                  board=board["name"])
    sketch = _sketch_for(board)
    _state["log"].append(f"flashing {sketch} -> {board['name']} on {port}")
    cmd = [_CLI, "--config-file", _CFG, "compile", "--upload", "-p", port,
           "--fqbn", board["fqbn"], sketch]
    try:
        proc = subprocess.Popen(cmd, cwd=_HERE, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True)
        for line in proc.stdout:
            line = line.rstrip()
            # The upload prints a progress bar per block; keep the meaning, drop
            # the noise, or the log is 200 lines of equals signs.
            if line and "Writing at 0x" not in line:
                _state["log"].append(line[:200])
        _state["ok"] = proc.wait() == 0
    except Exception as e:
        _state["log"].append(f"failed to run arduino-cli: {e}")
        _state["ok"] = False
    finally:
        _state["running"] = False
        _lock.release()


def start() -> dict:
    """Kick off a flash. Returns immediately; poll status() for progress."""
    if not _lock.acquire(blocking=False):
        return {"ok": False, "error": "a flash is already running"}
    port, board = detect()
    if not port:
        _lock.release()
        return {"ok": False, "error": "no panel found on USB — check the cable"}
    if not os.path.exists(_CLI):
        _lock.release()
        return {"ok": False, "error": "arduino-cli isn't installed on this Pi"}
    threading.Thread(target=_run, args=(port, board), daemon=True).start()
    return {"ok": True, "board": board["name"], "port": port,
            "sketch": _sketch_for(board)}
