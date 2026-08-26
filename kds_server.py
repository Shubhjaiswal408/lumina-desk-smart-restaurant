"""Lumina Desk — Kitchen Display System (KDS) backend.

A real-time kitchen dashboard served over the LAN. It bridges the MQTT bus to a
web UI: guest orders (from the voice tables) appear live, the chef advances each
through New -> Preparing -> Ready -> Served, and staff-call / payment alerts pop.

Open from any device on the WiFi:  http://techiesms.local:8000
Run:  ./venv/bin/uvicorn kds_server:app --host 0.0.0.0 --port 8000
"""
import asyncio
import json
import secrets
import subprocess
import time
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

import config
import kds_data
import mqtt_bus
import menu
import panel_flash
import payments
import settings

# ---- Order state (in memory; one entry per active table) ----
ORDERS: dict[str, dict] = {}
_loop: asyncio.AbstractEventLoop | None = None
_clients: set[WebSocket] = set()
_mqtt = None   # set in _start_mqtt; used to notify tables

STATUS_FLOW = ["new", "preparing", "ready", "served"]

# --- Table lifecycle -------------------------------------------------------
# available -> occupied (guests seated / ordering) -> cleaning (after checkout)
# -> available.  "reserved" is set by staff from the console.
# Anything not listed here is available.
TABLE_STATE: dict[str, str] = {}
SERVICE: dict[str, list] = {}      # table -> pending staff requests


def _set_state(table: str, state: str):
    if state == "available":
        TABLE_STATE.pop(table, None)
    else:
        TABLE_STATE[table] = state
    if _mqtt is not None:
        _mqtt.publish(f"lumina/table/{table}/state", state, retain=True)


def table_state(table: str) -> str:
    if table in ORDERS:
        return "occupied"
    return TABLE_STATE.get(table, "available")


# Seconds the thank-you screen stays up before the table resets for the next
# party. Generous because this panel needs ~20 s just to draw it.
PAY_RESET_SEC = 45


def _bank_order(table: str):
    """Write the order to history exactly once (pay and manual bump both call this)."""
    o = ORDERS.get(table)
    if not o or o.get("banked"):
        return
    o["banked"] = True
    try:
        kds_data.record_order(
            table, [{"name": i["name"], "qty": i["qty"], "size": i.get("size", "")}
                    for i in o["items"]],
            o.get("total", 0), o.get("created", time.time()))
    except Exception as e:
        print(f"[kds] history save failed: {e}", flush=True)


def _on_paid(table: str):
    """Bill settled: bank the order, then hand the table over after a pause."""
    _bank_order(table)
    print(f"[kds] table {table} paid -> reset in {PAY_RESET_SEC}s", flush=True)
    if _loop:
        _loop.call_soon_threadsafe(_spawn_reset, table)


# asyncio only holds weak refs to tasks — keep strong ones or they can be
# garbage-collected before they ever run.
_TASKS: set = set()


def _spawn_reset(table: str):
    t = asyncio.create_task(_reset_after_pay(table))
    _TASKS.add(t)
    t.add_done_callback(_TASKS.discard)


async def _reset_after_pay(table: str):
    try:
        await asyncio.sleep(PAY_RESET_SEC)
        ORDERS.pop(table, None)
        SERVICE.pop(table, None)
        _set_state(table, "cleaning")      # staff mark it clean -> available
        _notify_table(table, "served")     # voice app starts a fresh session
        if _mqtt is not None:
            # Clear the retained pay/paid screens AND the finished order, so a
            # restart doesn't resurrect the departed party's ticket.
            for t in ("pay", "payment", "order"):
                _mqtt.publish(f"lumina/table/{table}/{t}", "", retain=True)
        print(f"[kds] table {table} reset -> cleaning", flush=True)
        _broadcast()
    except Exception as e:
        print(f"[kds] reset failed for table {table}: {e}", flush=True)


def _kitchen_status(order) -> str:
    ss = [i["status"] for i in order["items"]]
    if not ss:
        return "served"
    if all(s in ("ready", "served") for s in ss):
        return "ready"
    if any(s in ("preparing", "ready") for s in ss):
        return "preparing"
    return "new"


def _notify_table(table: str, status: str):
    """Tell the guest's table (its ePaper) the kitchen status."""
    if _mqtt is not None:
        info = _mqtt.publish(f"lumina/table/{table}/kitchen", status, retain=True)
        print(f"[kds] notify table {table}: {status} (rc={info.rc})", flush=True)
    else:
        print(f"[kds] notify skipped — mqtt not ready", flush=True)


def _dish_meta(name: str) -> dict:
    d = menu.find_dish(name)
    return {
        "allergens": d["allergens"] if d else [],
        "veg": d["veg"] if d else True,
        "category": d["category"] if d else "",
        "prep": menu.prep_minutes(d) if d else 10,
    }


def _apply_order(table: str, payload: dict):
    """Merge a cart snapshot from the bus, preserving per-item prep status."""
    now = time.time()
    order = ORDERS.get(table)
    prev_items = {i["name"]: i for i in order["items"]} if order else {}

    items = []
    for it in payload.get("items", []):
        name, qty = it["name"], it.get("qty", 1)
        size = it.get("size") or ""
        meta = _dish_meta(name)
        old = prev_items.get(name)
        items.append({
            "name": name, "qty": qty, "size": size,
            "status": old["status"] if old else "new",
            "is_new": old is None,
            "allergens": meta["allergens"], "veg": meta["veg"],
            "category": meta["category"], "prep": meta["prep"],
        })

    if order is None:
        order = {"table": table, "created": now, "staff_called": False,
                 "pay_requested": False}
        ORDERS[table] = order
    order.update({
        "items": items,
        "subtotal": payload.get("subtotal", 0), "tax": payload.get("tax", 0),
        "total": payload.get("total", 0), "eta": payload.get("eta", 0),
        "status": payload.get("status", "Listening"), "updated": now,
    })
    if not items:                       # empty cart -> drop the ticket
        ORDERS.pop(table, None)


def _snapshot() -> dict:
    tables = sorted(set(ORDERS) | set(TABLE_STATE) | set(SERVICE))
    return {
        "type": "state",
        "orders": list(ORDERS.values()),
        "now": time.time(),
        "tables": [{"table": t, "state": table_state(t),
                    "service": SERVICE.get(t, [])} for t in tables],
    }


def _broadcast():
    if _loop:
        _loop.call_soon_threadsafe(_queue.put_nowait, _snapshot())


_queue: asyncio.Queue = asyncio.Queue()


# ---- MQTT bridge (paho on its own thread) ----
def _on_mqtt(client, userdata, msg):
    try:
        parts = msg.topic.split("/")           # lumina/table/<id>/<kind>
        table, kind = parts[2], parts[3]
        if not msg.payload.strip():            # retained topic cleared — ignore
            return
        if kind == "order":
            _apply_order(table, json.loads(msg.payload))
        elif kind == "event":
            ev = json.loads(msg.payload)
            o = ORDERS.get(table)
            etype = ev.get("type")
            if o and etype == "staff_called":
                o["staff_called"] = True
            elif o and etype == "pay_requested":
                o["pay_requested"] = True
            elif etype == "service_request":
                SERVICE.setdefault(table, []).append({
                    "item": ev.get("item", "something"),
                    "qty": ev.get("quantity", 1), "at": time.time()})
        elif kind == "payment" and msg.payload == b"paid":
            _on_paid(table)
        _broadcast()
    except Exception as e:
        print(f"[kds] mqtt error: {e}")


def _start_mqtt():
    global _mqtt
    # make_client waits for the broker and re-subscribes on every reconnect —
    # without that, a mosquitto restart leaves this board silently frozen.
    _mqtt = mqtt_bus.make_client("kds-server", on_message=_on_mqtt, topics=(
        "lumina/table/+/order",
        "lumina/table/+/event",
        "lumina/table/+/payment",
    ))
    return _mqtt


# ---- FastAPI app ----
app = FastAPI(title="Lumina Kitchen Display")
_STATIC = Path(__file__).parent / "static"


@app.on_event("startup")
async def _startup():
    global _loop
    _loop = asyncio.get_running_loop()
    kds_data.init_db()
    _start_mqtt()
    asyncio.create_task(_pump())
    asyncio.create_task(_watch_delays())


async def _watch_delays():
    """Tell a table (and the board) when its food is running late, so Lumina can
    apologise before the guest has to ask. Fires once per order."""
    while True:
        await asyncio.sleep(30)
        try:
            for table, o in list(ORDERS.items()):
                if o.get("delayed") or not o.get("items"):
                    continue
                if all(i["status"] in ("ready", "served") for i in o["items"]):
                    continue
                eta_sec = max(o.get("eta", 15), 5) * 60
                if time.time() - o["created"] > eta_sec + 300:   # 5 min grace
                    o["delayed"] = True
                    _notify_table(table, "delayed")
                    print(f"[kds] table {table} order is late -> apology sent", flush=True)
                    _broadcast()
        except Exception as e:
            print(f"[kds] delay watch error: {e}", flush=True)


async def _pump():
    while True:
        snap = await _queue.get()
        dead = []
        for ws in list(_clients):
            try:
                await ws.send_json(snap)
            except Exception:
                dead.append(ws)
        for ws in dead:
            _clients.discard(ws)


# ---------------- Auth (staff PIN) ----------------
# LAN device with a shared staff PIN. Tokens live in memory, so a server restart
# logs everyone out — fine for a kitchen terminal.
_TOKENS: set[str] = set()
# /api/pay/webhook stays open — a payment gateway can't send our token.
# (Add signature verification there before exposing it to the internet.)
_OPEN_PATHS = ("/api/auth", "/api/pay/webhook")


@app.post("/api/auth")
async def api_auth(body: dict):
    if str(body.get("pin", "")) == str(settings.get("admin_pin", config.ADMIN_PIN)):
        tok = secrets.token_urlsafe(24)
        _TOKENS.add(tok)
        return {"ok": True, "token": tok}
    return JSONResponse({"ok": False, "error": "wrong PIN"}, status_code=401)


@app.middleware("http")
async def _guard(request, call_next):
    p = request.url.path
    if p.startswith("/api") and not p.startswith(_OPEN_PATHS):
        tok = (request.headers.get("x-lumina-token")
               or request.query_params.get("token", ""))
        if tok not in _TOKENS:
            return JSONResponse({"error": "unauthorised"}, status_code=401)
    return await call_next(request)


@app.get("/")
async def index():
    # New React admin suite if built; else the lightweight legacy kitchen page.
    if (_STATIC / "admin" / "index.html").exists():
        return RedirectResponse("/admin/")
    return FileResponse(_STATIC / "kitchen.html")


@app.get("/api/state")
async def state():
    return JSONResponse(_snapshot())


@app.post("/api/table/{table}/item/{name}/advance")
async def advance_item(table: str, name: str):
    o = ORDERS.get(table)
    if o:
        for it in o["items"]:
            if it["name"] == name:
                it["is_new"] = False
                cur = STATUS_FLOW.index(it["status"]) if it["status"] in STATUS_FLOW else 0
                it["status"] = STATUS_FLOW[min(cur + 1, len(STATUS_FLOW) - 1)]
        _notify_table(table, _kitchen_status(o))
        _broadcast()
    return {"ok": True}


@app.post("/api/table/{table}/all/{status}")
async def set_all(table: str, status: str):
    o = ORDERS.get(table)
    if o and status in STATUS_FLOW:
        for it in o["items"]:
            it["status"] = status
            it["is_new"] = False
        _notify_table(table, _kitchen_status(o))
        _broadcast()
    return {"ok": True}


@app.post("/api/table/{table}/bump")
async def bump(table: str):
    _bank_order(table)
    ORDERS.pop(table, None)
    SERVICE.pop(table, None)
    _set_state(table, "cleaning")     # checkout -> needs cleaning
    _notify_table(table, "served")
    _broadcast()
    return {"ok": True}


@app.get("/api/menu")
async def api_menu():
    return kds_data.menu_list()


@app.post("/api/menu/add")
async def api_menu_add(body: dict):
    kds_data.add_custom_dish(
        body["name"].strip(), body.get("category", "Main"),
        float(body.get("price", 0)), bool(body.get("veg", True)),
        body.get("allergens", []), int(body.get("prep", 15)),
        body.get("ingredients", []))
    return {"ok": True}


@app.post("/api/menu/{name}/delete")
async def api_menu_delete(name: str):
    kds_data.delete_custom_dish(name)
    return {"ok": True}


@app.post("/api/menu/{name}")
async def api_menu_update(name: str, body: dict):
    kds_data.set_override(name, body.get("price"), body.get("available"))
    return {"ok": True}


@app.get("/api/analytics")
async def api_analytics():
    return kds_data.analytics()


# ---------------- Payments (dynamic UPI QR) ----------------

@app.get("/api/pay/{table}")
async def api_pay(table: str, amount: float = None):
    """Dynamic UPI link + QR for a table's current bill (or an explicit amount)."""
    o = ORDERS.get(table)
    amt = amount if amount is not None else (o.get("total", 0) if o else 0)
    url, ref = payments.upi_url(amt, table)
    kds_data.record_payment(table, amt, ref)
    return {"table": table, "amount": round(amt, 2), "upi_url": url, "ref": ref,
            "qr": "/api/pay/{}/qr?amount={}&ref={}".format(table, amt, ref),
            "vpa": settings.get("upi_vpa", config.UPI_VPA),
            "payee": settings.get("upi_payee", config.UPI_PAYEE_NAME)}


@app.get("/api/pay/{table}/qr")
async def api_pay_qr(table: str, amount: float = 0, ref: str = None):
    url, _ = payments.upi_url(amount, table, ref)
    return Response(payments.qr_png_bytes(url), media_type="image/png")


@app.post("/api/pay/webhook")
async def api_pay_webhook(body: dict):
    """Payment gateway calls this when money lands.
    Expected: {"ref": "LUM07...", "status": "success", "amount": 123.45}"""
    ref = str(body.get("ref", ""))
    ok = str(body.get("status", "")).lower() in ("success", "paid", "captured", "completed")
    row = kds_data.settle_payment(ref, ok, body.get("amount"))
    if row and ok and _mqtt is not None:
        _mqtt.publish(f"lumina/table/{row['tbl']}/payment", "paid", retain=True)
    _broadcast()
    return {"ok": True, "matched": bool(row), "settled": ok}


# ---------------- The table panel ----------------

@app.get("/api/panel")
async def api_panel():
    return panel_flash.status()


@app.post("/api/panel/redraw")
async def api_panel_redraw():
    """Ask the display service to send the current screen again.

    This is what a panel showing something stale actually needs, and it costs
    one refresh rather than a two-minute reflash — so it's the first thing to
    reach for.
    """
    if _mqtt is None:
        return {"ok": False, "error": "no MQTT connection"}
    _mqtt.publish(f"lumina/table/{config.TABLE_ID}/panel", "online", retain=True)
    return {"ok": True}


@app.post("/api/panel/flash")
async def api_panel_flash():
    """Put the firmware back on the panel. Takes about a minute."""
    return panel_flash.start()


@app.get("/api/payments")
async def api_payments():
    return kds_data.payments(50)


@app.post("/api/payments/{ref}/mark")
async def api_mark_payment(ref: str, body: dict = None):
    """Manual settle — for when the waiter sees the money land but no
    email/webhook matched it."""
    ok = (body or {}).get("paid", True)
    row = kds_data.settle_payment(ref, bool(ok))
    if row and ok and _mqtt is not None:
        _mqtt.publish(f"lumina/table/{row['tbl']}/payment", "paid", retain=True)
    _broadcast()
    return {"ok": True, "matched": bool(row)}


# ---------------- Table control + live logs ----------------

@app.post("/api/table/{table}/reset")
async def api_table_reset(table: str):
    """Turn the table over: clear the ticket and reset the guest's voice session."""
    ORDERS.pop(table, None)
    _notify_table(table, "served")     # voice app resets its session on 'served'
    _broadcast()
    return {"ok": True}


@app.post("/api/table/{table}/state/{state}")
async def api_table_state(table: str, state: str):
    """Staff set a table Reserved / Cleaning / Available from the console."""
    if state not in ("available", "reserved", "cleaning"):
        return JSONResponse({"error": "bad state"}, status_code=400)
    _set_state(table, state)
    _broadcast()
    return {"ok": True, "state": table_state(table)}


@app.post("/api/table/{table}/service/clear")
async def api_service_clear(table: str):
    """Staff delivered the water/napkin — clear the request."""
    SERVICE.pop(table, None)
    _broadcast()
    return {"ok": True}


@app.get("/api/settings")
async def api_settings_get():
    s = settings.all_settings()
    key = s.get("groq_api_key") or ""
    # never send the whole key back to the browser
    s["groq_api_key_masked"] = (key[:6] + "…" + key[-4:]) if len(key) > 12 else ("set" if key else "")
    s.pop("groq_api_key", None)
    s["has_key"] = bool(settings.groq_key())
    s["ollama_up"] = _ollama_up()
    return s


@app.post("/api/settings")
async def api_settings_set(body: dict):
    saved = settings.save(body)
    if "assistant_state" in body and _mqtt is not None:
        # tell the panels so they can show/hide the mute badge
        _mqtt.publish("lumina/assistant", saved["assistant_state"], retain=True)
    return {"ok": True, "settings": saved}


@app.post("/api/settings/test")
async def api_settings_test(body: dict):
    """Check a Groq key works before the manager saves it, and whether the local
    (offline) brain is running."""
    key = (body.get("groq_api_key") or "").strip() or settings.groq_key()
    out = {"ollama_up": _ollama_up(), "cloud_ok": False, "detail": ""}
    if not key:
        out["detail"] = "No API key set — cloud features off."
        return out
    try:
        import requests as rq
        r = rq.post(config.GROQ_CHAT_URL,
                    headers={"Authorization": f"Bearer {key}"},
                    json={"model": config.GROQ_LLM_MODEL, "max_tokens": 5,
                          "messages": [{"role": "user", "content": "ping"}]},
                    timeout=10)
        out["cloud_ok"] = r.status_code == 200
        out["detail"] = "Key works." if r.ok else f"Groq said {r.status_code}"
    except Exception as e:
        out["detail"] = f"Could not reach Groq: {e}"
    return out


def _ollama_up() -> bool:
    try:
        import requests as rq
        return rq.get("http://localhost:11434/api/version", timeout=2).ok
    except Exception:
        return False


@app.get("/api/logs")
async def api_logs(service: str = "lumina-voice", lines: int = 120):
    """Live terminal output of a service, for the web console."""
    if service not in ("lumina-voice", "lumina-display", "lumina-kds", "mosquitto"):
        return {"error": "unknown service"}
    try:
        out = subprocess.run(
            ["journalctl", "-u", service, "-n", str(min(lines, 400)), "--no-pager", "-o", "short-iso"],
            capture_output=True, text=True, timeout=6).stdout
        keep = [l for l in out.splitlines() if "GetGpuDevices" not in l and "device_discovery" not in l]
        return {"service": service, "lines": keep[-lines:]}
    except Exception as e:
        return {"service": service, "lines": [f"(log read failed: {e})"]}


@app.get("/api/orders/history")
async def api_history():
    return kds_data.history(100)


@app.post("/api/table/{table}/ack_alert/{kind}")
async def ack_alert(table: str, kind: str):
    o = ORDERS.get(table)
    if o:
        if kind == "staff":
            o["staff_called"] = False
        elif kind == "pay":
            o["pay_requested"] = False
        _broadcast()
    return {"ok": True}


@app.websocket("/ws")
async def ws(websocket: WebSocket):
    if websocket.query_params.get("token", "") not in _TOKENS:
        await websocket.close(code=4401)
        return
    await websocket.accept()
    _clients.add(websocket)
    await websocket.send_json(_snapshot())
    try:
        while True:
            await websocket.receive_text()   # keepalive; we don't expect input
    except WebSocketDisconnect:
        _clients.discard(websocket)
    except Exception:
        _clients.discard(websocket)


app.mount("/static", StaticFiles(directory=_STATIC), name="static")

# The built React admin SPA (uses HashRouter, so one index.html covers all routes)
_ADMIN = _STATIC / "admin"
if (_ADMIN / "index.html").exists():
    app.mount("/admin", StaticFiles(directory=_ADMIN, html=True), name="admin")
