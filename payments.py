"""UPI dynamic QR generation for Lumina Desk.

The QR encodes a standard NPCI deep link. Only the `am` (amount) field changes
per bill — that's what makes it "dynamic": the guest scans and their UPI app is
pre-filled with the exact total, so no typing and no wrong amounts.

    upi://pay?pa=<vpa>&pn=<payee>&am=<AMOUNT>&cu=INR&tn=<note>&tr=<ref>

`tr` (transaction reference) is unique per bill so an incoming payment webhook
can be matched back to the table that owes it.
"""
import io
import time
from urllib.parse import quote

import qrcode

import config
import settings


def txn_ref(table: str) -> str:
    """Unique, readable reference: LUM<table><epoch>. Matched by the webhook."""
    return f"LUM{table}{int(time.time())}"


def upi_url(amount: float, table: str, ref: str = None) -> tuple[str, str]:
    """Build the UPI deep link for `amount`. Returns (url, txn_ref)."""
    ref = ref or txn_ref(table)
    url = config.UPI_URL_TEMPLATE.format(
        pa=settings.get("upi_vpa", config.UPI_VPA),
        pn=quote(settings.get("upi_payee", config.UPI_PAYEE_NAME)),
        am=f"{float(amount):.2f}",          # <-- the dynamic part
        cu=config.UPI_CURRENCY,
        tn=quote(f"Table {table} bill"),
        tr=ref,
    )
    return url, ref


def qr_image(data: str, box_size: int = 8, border: int = 2):
    """Render `data` to a PIL image (1-bit, ideal for ePaper)."""
    qr = qrcode.QRCode(
        version=None, error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=box_size, border=border,
    )
    qr.add_data(data)
    qr.make(fit=True)
    return qr.make_image(fill_color="black", back_color="white").convert("RGB")


def qr_png_bytes(data: str, box_size: int = 8) -> bytes:
    buf = io.BytesIO()
    qr_image(data, box_size=box_size).save(buf, format="PNG")
    return buf.getvalue()


if __name__ == "__main__":
    url, ref = upi_url(1234.50, "07")
    print("UPI URL:", url)
    print("ref:", ref)
    qr_image(url).save("/tmp/upi_test.png")
    print("QR saved to /tmp/upi_test.png")
