"""Confirm UPI payments by reading FamApp's "money received" emails.

Why this exists: a plain UPI QR has no webhook — FamApp won't call our server.
But it DOES email the merchant on every incoming payment. So we watch that
mailbox over IMAP, parse the amount, and settle the matching pending bill.

FamApp's mail (from no-reply@famapp.in) looks like:
    Subject: You received ₹1500.0 in your FamX account
    Body:    ... successfully received ₹1500.0 from JAISWAL URVISH at
             11:15 PM IST, 09 July 2026 with transaction id FMPIB6110481304.
             ... UTR: 619051396947. Purpose: UPI.

Matching: the email has no bill reference, so we match on AMOUNT + a recent
time window (a QR generated minutes ago for the same amount). Good enough for a
restaurant; exact-reference matching needs a real payment gateway.

Setup: Gmail needs an App Password (myaccount.google.com -> Security ->
2-Step Verification -> App passwords). Save it:
    echo 'your-16-char-app-password' > ~/lumina-desk/.gmail_key
"""
import email
import email.utils
import imaplib
import os
import re
import time
from email.header import decode_header

import config
import kds_data
import settings
import mqtt_bus

_mqtt = None


def _announce_paid(table: str):
    """Tell the table's ePaper (and anything else on the bus) the bill is paid."""
    global _mqtt
    try:
        if _mqtt is None:
            _mqtt = mqtt_bus.make_client("payment-watcher")
        info = _mqtt.publish(f"lumina/table/{table}/payment", "paid", retain=True, qos=1)
        info.wait_for_publish(5)          # make sure it actually left the process
        print(f"[pay] announced paid -> table {table}", flush=True)
    except Exception as e:
        print(f"[pay] could not announce: {e}", flush=True)

IMAP_HOST = "imap.gmail.com"
SENDER = "no-reply@famapp.in"
POLL_SEC = 20
# A payment counts for a bill generated at most this long ago.
MATCH_WINDOW_SEC = 45 * 60

_AMT = re.compile(r"received\s*₹\s*([\d,]+(?:\.\d+)?)", re.I)
_FROM = re.compile(r"from\s+(.+?)\s+at\s", re.I)
_TXN = re.compile(r"transaction id\s+(\S+?)[\.\s]", re.I)
_UTR = re.compile(r"UTR[:\s]+(\d+)", re.I)


def _creds():
    key = os.environ.get("GMAIL_APP_PASSWORD")
    if not key:
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".gmail_key")
        if os.path.exists(p):
            key = open(p).read().strip()
    return settings.get("payment_email", config.PAYMENT_EMAIL), key


def parse_receipt(text: str):
    """Pull (amount, payer, txn, utr) out of a FamApp 'received' mail."""
    m = _AMT.search(text)
    if not m:
        return None
    amount = float(m.group(1).replace(",", ""))
    payer = (_FROM.search(text).group(1).strip() if _FROM.search(text) else "")
    txn = (_TXN.search(text).group(1) if _TXN.search(text) else "")
    utr = (_UTR.search(text).group(1) if _UTR.search(text) else "")
    return {"amount": amount, "payer": re.sub(r"\s+", " ", payer), "txn": txn, "utr": utr}


def _body(msg) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                try:
                    return part.get_payload(decode=True).decode(errors="replace")
                except Exception:
                    pass
        return ""
    try:
        return msg.get_payload(decode=True).decode(errors="replace")
    except Exception:
        return ""


def settle(receipt: dict, sent_at: float = None) -> dict:
    """Match a FamApp receipt to a pending bill and settle it.

    Every FamApp mail carries a unique Transaction ID and UTR, so we use them to
    make this safe:
      1. a transaction ID may settle at most ONE bill (no double-counting, and
         re-reading the same mail is harmless),
      2. the payment must have happened AFTER the QR was generated,
      3. amount must match, and we take the OLDEST such bill (guests pay in the
         order they asked to).
    """
    if kds_data.txn_already_used(receipt.get("txn")):
        return None                       # already settled by this transaction

    now = sent_at or time.time()
    candidates = [
        p for p in kds_data.payments(120)
        if p["status"] == "pending"
        and abs(float(p["amount"]) - receipt["amount"]) < 0.01
        and p["created"] <= now + 120           # QR came before the payment
        and now - p["created"] <= MATCH_WINDOW_SEC
    ]
    if not candidates:
        print(f"[pay] received ₹{receipt['amount']} from {receipt['payer']} "
              f"(txn {receipt.get('txn')}) — no pending bill matched", flush=True)
        return None

    p = min(candidates, key=lambda x: x["created"])   # oldest waiting bill
    kds_data.settle_payment(p["ref"], True, receipt["amount"],
                            txn=receipt.get("txn"), utr=receipt.get("utr"),
                            payer=receipt.get("payer"))
    extra = f" (+{len(candidates)-1} same-amount bills waiting)" if len(candidates) > 1 else ""
    print(f"[pay] MATCHED ₹{receipt['amount']} from {receipt['payer']} -> table {p['tbl']} "
          f"[ref {p['ref']} · txn {receipt.get('txn')} · utr {receipt.get('utr')}]{extra}",
          flush=True)
    _announce_paid(p["tbl"])      # -> ePaper shows the thank-you screen
    return p


def poll_once(mail) -> int:
    """Check for new FamApp 'received' mails. Returns how many were settled."""
    mail.select("INBOX")
    # SINCE today keeps us off the rest of the mailbox entirely.
    since = time.strftime("%d-%b-%Y", time.localtime(time.time() - 86400))
    typ, data = mail.search(None, f'(UNSEEN FROM "{SENDER}" SINCE {since})')
    if typ != "OK" or not data[0]:
        return 0
    settled = 0
    for num in data[0].split():
        typ, raw = mail.fetch(num, "(RFC822)")
        if typ != "OK":
            continue
        msg = email.message_from_bytes(raw[0][1])

        # Only settle against RECENT mail. Old unread FamApp receipts sitting in
        # the inbox must never match a bill we just generated.
        try:
            sent = email.utils.parsedate_to_datetime(msg.get("Date")).timestamp()
            if time.time() - sent > MATCH_WINDOW_SEC:
                continue
        except Exception:
            continue

        subj = str(decode_header(msg.get("Subject", ""))[0][0])
        if isinstance(subj, bytes):
            subj = subj.decode(errors="replace")
        text = subj + "\n" + _body(msg)
        if "received" not in text.lower():
            continue                       # outgoing payment mail — ignore
        r = parse_receipt(text)
        if r and settle(r, sent_at=sent):
            settled += 1
    return settled


def main():
    user, pw = _creds()
    if not pw:
        print("[pay] No Gmail app password (.gmail_key) — watcher idle.", flush=True)
        return
    print(f"[pay] watching {user} for FamApp payments…", flush=True)
    while True:
        try:
            mail = imaplib.IMAP4_SSL(IMAP_HOST)
            mail.login(user, pw)
            while True:
                try:
                    poll_once(mail)
                except Exception as e:
                    print(f"[pay] poll error: {e}", flush=True)
                    break
                time.sleep(POLL_SEC)
            try:
                mail.logout()
            except Exception:
                pass
        except Exception as e:
            print(f"[pay] connect failed: {e}; retrying in 60s", flush=True)
            time.sleep(60)


if __name__ == "__main__":
    main()
