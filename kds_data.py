"""Persistence + analytics for the Lumina admin suite (SQLite).

Keeps served orders for history/analytics, and per-dish overrides (price,
availability) that layer on top of the menu.py defaults.
"""
import json
import sqlite3
import time
from pathlib import Path

import menu

DB = str(Path(__file__).parent / "lumina.db")


def _conn():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c


def _bust_cache():
    """Reset menu.py's override/custom caches in THIS process so admin edits show
    immediately (other processes self-refresh within their 8s TTL)."""
    menu._ov_cache["t"] = 0
    menu._cd_cache["t"] = 0


def init_db():
    with _conn() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS history(
            id INTEGER PRIMARY KEY AUTOINCREMENT, tbl TEXT, items TEXT,
            total REAL, created REAL, served_at REAL)""")
        c.execute("""CREATE TABLE IF NOT EXISTS menu_override(
            name TEXT PRIMARY KEY, price REAL, available INTEGER)""")
        c.execute("""CREATE TABLE IF NOT EXISTS custom_dish(
            name TEXT PRIMARY KEY, category TEXT, price REAL, veg INTEGER,
            allergens TEXT, prep INTEGER)""")
        # ingredients added later — migrate existing DBs
        cols = [r[1] for r in c.execute("PRAGMA table_info(custom_dish)")]
        if "ingredients" not in cols:
            c.execute("ALTER TABLE custom_dish ADD COLUMN ingredients TEXT DEFAULT '[]'")
        c.execute("""CREATE TABLE IF NOT EXISTS payment(
            ref TEXT PRIMARY KEY, tbl TEXT, amount REAL, status TEXT,
            created REAL, settled_at REAL)""")
        # audit trail from the FamApp receipt (unique per real transaction)
        pcols = [r[1] for r in c.execute("PRAGMA table_info(payment)")]
        for col in ("txn", "utr", "payer"):
            if col not in pcols:
                c.execute(f"ALTER TABLE payment ADD COLUMN {col} TEXT")


def txn_already_used(txn: str) -> bool:
    """A FamApp transaction ID settles at most ONE bill, ever."""
    if not txn:
        return False
    with _conn() as c:
        return c.execute("SELECT 1 FROM payment WHERE txn=?", (txn,)).fetchone() is not None


def record_payment(table: str, amount: float, ref: str):
    """Log a QR we generated, so a webhook can match the payment later."""
    with _conn() as c:
        c.execute("""INSERT INTO payment(ref,tbl,amount,status,created)
                     VALUES(?,?,?,'pending',?) ON CONFLICT(ref) DO NOTHING""",
                  (ref, table, amount, time.time()))


def settle_payment(ref: str, ok: bool, amount=None, txn=None, utr=None, payer=None):
    """Mark a payment paid/failed and record which real transaction settled it."""
    with _conn() as c:
        row = c.execute("SELECT * FROM payment WHERE ref=?", (ref,)).fetchone()
        if not row:
            return None
        c.execute("""UPDATE payment SET status=?, settled_at=?, amount=COALESCE(?,amount),
                     txn=COALESCE(?,txn), utr=COALESCE(?,utr), payer=COALESCE(?,payer)
                     WHERE ref=?""",
                  ("paid" if ok else "failed", time.time(), amount, txn, utr, payer, ref))
        return dict(row)


def payments(limit: int = 50) -> list:
    try:
        with _conn() as c:
            rows = c.execute("SELECT * FROM payment ORDER BY created DESC LIMIT ?",
                             (limit,)).fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []


def add_custom_dish(name, category, price, veg, allergens, prep, ingredients=None):
    ing = json.dumps(ingredients or [])
    with _conn() as c:
        c.execute("""INSERT INTO custom_dish(name,category,price,veg,allergens,prep,ingredients)
                     VALUES(?,?,?,?,?,?,?) ON CONFLICT(name) DO UPDATE SET
                     category=?, price=?, veg=?, allergens=?, prep=?, ingredients=?""",
                  (name, category, price, int(bool(veg)), json.dumps(allergens), prep, ing,
                   category, price, int(bool(veg)), json.dumps(allergens), prep, ing))
    _bust_cache()


def delete_custom_dish(name):
    with _conn() as c:
        c.execute("DELETE FROM custom_dish WHERE name=?", (name,))
    _bust_cache()


def custom_dishes() -> list:
    """Admin-added dishes as menu-shaped dicts (so the voice app can order them)."""
    try:
        with _conn() as c:
            rows = c.execute("SELECT * FROM custom_dish").fetchall()
    except Exception:
        return []
    out = []
    for r in rows:
        out.append({
            "name": r["name"], "category": r["category"], "price": int(r["price"]),
            "veg": bool(r["veg"]), "vegan": False,
            "ingredients": [], "allergens": json.loads(r["allergens"] or "[]"),
            "prep": r["prep"], "aliases": [r["name"].lower()], "custom": True,
        })
    return out


def record_order(table: str, items: list, total: float, created: float, served_at: float = None):
    """Save a served order for history + analytics."""
    with _conn() as c:
        c.execute("INSERT INTO history(tbl,items,total,created,served_at) VALUES(?,?,?,?,?)",
                  (table, json.dumps(items), total, created, served_at or time.time()))


def history(limit: int = 100) -> list:
    with _conn() as c:
        rows = c.execute("SELECT * FROM history ORDER BY served_at DESC LIMIT ?", (limit,)).fetchall()
    out = []
    for r in rows:
        out.append({"id": r["id"], "table": r["tbl"], "items": json.loads(r["items"]),
                    "total": r["total"], "created": r["created"], "served_at": r["served_at"]})
    return out


def analytics() -> dict:
    rows = history(1000)
    today = time.strftime("%Y-%m-%d")
    def is_today(ts):
        return time.strftime("%Y-%m-%d", time.localtime(ts)) == today

    todays = [r for r in rows if is_today(r["served_at"])]
    revenue = sum(r["total"] for r in todays)
    orders = len(todays)
    # popular dishes (by qty, all-time)
    counts: dict[str, int] = {}
    for r in rows:
        for it in r["items"]:
            counts[it["name"]] = counts.get(it["name"], 0) + it.get("qty", 1)
    popular = sorted(counts.items(), key=lambda kv: -kv[1])[:8]
    # revenue by hour (today)
    hours = {h: 0.0 for h in range(24)}
    for r in todays:
        hours[time.localtime(r["served_at"]).tm_hour] += r["total"]
    # avg turnaround (served - created), minutes
    spans = [(r["served_at"] - r["created"]) / 60 for r in rows if r["created"]]
    avg_turn = round(sum(spans) / len(spans), 1) if spans else 0
    # Busiest tables + peak hours, across all history (needs volume to be useful).
    by_table: dict[str, dict] = {}
    for r in rows:
        t = by_table.setdefault(r["table"], {"table": r["table"], "orders": 0, "revenue": 0.0})
        t["orders"] += 1
        t["revenue"] += r["total"]
    busiest = sorted(by_table.values(), key=lambda x: -x["orders"])[:6]
    for t in busiest:
        t["revenue"] = round(t["revenue"])

    all_hours = {h: 0 for h in range(24)}
    for r in rows:
        all_hours[time.localtime(r["served_at"]).tm_hour] += 1
    peak = max(all_hours, key=lambda h: all_hours[h]) if rows else None

    return {
        "busiest_tables": busiest,
        "peak_hour": (f"{peak:02d}:00–{(peak + 1) % 24:02d}:00" if peak is not None else "—"),
        "peak_hour_orders": all_hours.get(peak, 0) if peak is not None else 0,
        "orders_by_hour": [{"hour": f"{h:02d}", "orders": all_hours[h]} for h in range(24)],
        "revenue_today": round(revenue),
        "orders_today": orders,
        "avg_ticket": round(revenue / orders) if orders else 0,
        "avg_turnaround_min": avg_turn,
        "popular": [{"name": n, "qty": q} for n, q in popular],
        "revenue_by_hour": [{"hour": f"{h:02d}", "revenue": round(v)} for h, v in hours.items()],
        "total_served": len(rows),
    }


def _overrides() -> dict:
    with _conn() as c:
        rows = c.execute("SELECT * FROM menu_override").fetchall()
    return {r["name"]: {"price": r["price"], "available": bool(r["available"])} for r in rows}


def menu_list() -> list:
    """Base + custom dishes, merged with admin price/availability overrides."""
    ov = _overrides()
    out = []
    for d in menu.all_dishes():
        o = ov.get(d["name"], {})
        out.append({
            "name": d["name"], "category": d["category"], "veg": d["veg"],
            "vegan": d.get("vegan", False), "allergens": d["allergens"],
            "prep": menu.prep_minutes(d),
            "price": o.get("price", d["price"]),
            "available": o.get("available", True),
            "custom": d.get("custom", False),
        })
    return out


def set_override(name: str, price: float | None, available: bool | None):
    cur = _overrides().get(name, {})
    price = cur.get("price") if price is None else price
    available = cur.get("available", True) if available is None else available
    base = next((d for d in menu.MENU if d["name"] == name), None)
    if base and price is None:
        price = base["price"]
    with _conn() as c:
        c.execute("""INSERT INTO menu_override(name,price,available) VALUES(?,?,?)
                     ON CONFLICT(name) DO UPDATE SET price=?, available=?""",
                  (name, price, int(bool(available)), price, int(bool(available))))
    _bust_cache()
