"""Lumina Desk — 800x480 ePaper UI renderer (Pillow).

Renders the table screen in the panel's 3-color palette (white / black / red).
All layout and typography live here on the Pi; the ESP32 just displays the image.

Design system
  * Canvas 800x480, 40px outer margin, elements on a calm baseline grid.
  * Palette: paper white, ink black, one RED accent used only for meaning —
    the brand mark, the live status dot, item quantities, allergen warnings,
    and the amount due.
  * Type: serif wordmark (fine-dining), sans for all UI/data.
  * A single hairline system; the bill lives in its own bordered card; prices
    right-align to a rail.
"""
from PIL import Image, ImageDraw, ImageFont

import menu

W, H = 800, 480
MARGIN = 40

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (210, 25, 25)

_FONTS = "/usr/share/fonts/truetype/dejavu/"
_PATHS = {
    "serif_bold": _FONTS + "DejaVuSerif-Bold.ttf",
    "serif": _FONTS + "DejaVuSerif.ttf",
    "sans": _FONTS + "DejaVuSans.ttf",
    "sans_bold": _FONTS + "DejaVuSans-Bold.ttf",
    "sans_light": _FONTS + "DejaVuSans-ExtraLight.ttf",
}
_cache = {}


def font(kind, size):
    key = (kind, size)
    if key not in _cache:
        _cache[key] = ImageFont.truetype(_PATHS[kind], size)
    return _cache[key]


def _rupee(fnt):
    try:
        return "₹" if fnt.getmask("₹").getbbox() else "Rs "
    except Exception:
        return "Rs "


def _tw(draw, s, fnt, tracking=0):
    w = draw.textlength(s, font=fnt)
    return w + tracking * max(0, len(s) - 1) if tracking else w


def _tracked(draw, xy, s, fnt, fill, tracking):
    x, y = xy
    for ch in s:
        draw.text((x, y), ch, font=fnt, fill=fill)
        x += draw.textlength(ch, font=fnt) + tracking


def _right(draw, xr, y, s, fnt, fill):
    draw.text((xr - draw.textlength(s, font=fnt), y), s, font=fnt, fill=fill)


def _money(n):
    return f"{int(round(n)):,}"


def _brandmark(d, cx, cy, r=8):
    # A small red diamond — a quiet, premium brand accent.
    d.polygon([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)], fill=RED)


def _brand():
    """Restaurant name from Settings, so the panel matches the outlet."""
    try:
        import settings
        return settings.get("restaurant_name", "Lumina")
    except Exception:
        return "Lumina"


def _header(d, table, status, listening):
    _brandmark(d, MARGIN + 8, 52)
    _tracked(d, (MARGIN + 28, 30), _brand().upper(), font("serif_bold", 44), BLACK, 3)
    _tracked(d, (MARGIN + 30, 82), "PURE VEG  ·  PIZZA & MORE", font("sans", 12), BLACK, 4)

    # Right: table (bold) centred against the wordmark, status aligned with the
    # tagline row beneath it.
    tf = font("sans_bold", 18)
    _right(d, W - MARGIN, 43, f"Table {table}", tf, BLACK)
    sf = font("sans", 15)
    sw = d.textlength(status, font=sf)
    sx = W - MARGIN - sw
    if listening:
        d.ellipse([sx - 20, 84, sx - 8, 96], fill=RED)
    d.text((sx, 80), status, font=sf, fill=BLACK)

    d.line([MARGIN, 112, W - MARGIN, 112], fill=BLACK, width=2)


def _section_label(d, x, y, text):
    _tracked(d, (x, y), text, font("sans_bold", 15), BLACK, 3)
    w = _tw(d, text, font("sans_bold", 15), 3)
    d.line([x, y + 24, x + w, y + 24], fill=RED, width=2)   # short red underline


def _footer(d, hint):
    y = H - 44
    d.line([MARGIN, y, W - MARGIN, y], fill=BLACK, width=1)
    d.ellipse([MARGIN, y + 15, MARGIN + 9, y + 24], fill=RED)
    d.text((MARGIN + 20, y + 12), hint, font=font("sans", 15), fill=BLACK)


# --- bill card (right column) ---
CARD_X0, CARD_X1 = 486, W - MARGIN
CARD_Y0, CARD_Y1 = 128, 356
PAD = 20


def _bill_card(d, session, rupee):
    d.rounded_rectangle([CARD_X0, CARD_Y0, CARD_X1, CARD_Y1], radius=12,
                        outline=BLACK, width=2)
    xl, xr = CARD_X0 + PAD, CARD_X1 - PAD
    _tracked(d, (xl, CARD_Y0 + PAD), "TO PAY", font("sans_bold", 15), BLACK, 3)

    y = CARD_Y0 + PAD + 40
    d.text((xl, y), "Items", font=font("sans", 17), fill=BLACK)
    _right(d, xr, y, str(sum(l["qty"] for l in session.cart)), font("sans", 17), BLACK)
    y += 30
    _mode, _rate = menu.tax_config()
    d.text((xl, y), "incl. GST" if _mode == "inclusive" else f"GST {_rate * 100:.0f}%",
           font=font("sans", 17), fill=BLACK)
    _right(d, xr, y, _money(session.tax()), font("sans", 17), BLACK)
    y += 34
    d.line([xl, y, xr, y], fill=BLACK, width=1)
    y += 16
    _tracked(d, (xl, y + 12), "TOTAL", font("sans_bold", 15), BLACK, 3)
    _right(d, xr, y + 2, f"{rupee}{_money(session.total())}", font("sans_bold", 40), RED)

    # Ready-in strip at the foot of the card.
    ry = CARD_Y1 - 40
    d.line([xl, ry, xr, ry], fill=BLACK, width=1)
    d.text((xl, ry + 12), "Ready in", font=font("sans", 16), fill=BLACK)
    _right(d, xr, ry + 8, f"~{session.est_prep_time()} min", font("sans_bold", 20), BLACK)


_KITCHEN_MSG = {
    "preparing": ("The kitchen is preparing your order", False),
    "ready": ("Your order is ready — on its way!", True),
    "delayed": ("Sorry — your order is taking a little longer", True),
}


def _kitchen_banner(d, kitchen):
    """A slim status strip in the left column when the kitchen reports progress.
    Kept left of the bill card so nothing overlaps."""
    msg = _KITCHEN_MSG.get(kitchen)
    if not msg:
        return 0
    text, urgent = msg
    color = RED if urgent else BLACK
    right = CARD_X0 - 30
    d.rounded_rectangle([MARGIN, 120, right, 152], radius=8, outline=color, width=2)
    d.ellipse([MARGIN + 13, 130, MARGIN + 23, 140], fill=color)
    d.text((MARGIN + 36, 127), text, font=font("sans_bold", 16), fill=color)
    return 44   # vertical space consumed by the banner


def _broadcast_strip(d, message):
    """House announcement from the manager, across the foot of the screen."""
    if not message:
        return
    y = H - 92
    d.rounded_rectangle([MARGIN, y, W - MARGIN, y + 36], radius=8, fill=RED)
    f = font("sans_bold", 17)
    w = d.textlength(message, font=f)
    d.text(((W - w) / 2, y + 8), message, font=f, fill=WHITE)


def render_order(session, table="07", status="Listening", hint=None, kitchen=None,
                 broadcast=None):
    img = Image.new("RGB", (W, H), WHITE)
    d = ImageDraw.Draw(img)
    rupee = _rupee(font("sans_bold", 20))
    _header(d, table, status, listening=True)

    price_rail = CARD_X0 - 30      # right edge for left-column line totals
    dy = _kitchen_banner(d, kitchen)   # push content down if a banner shows

    if session.cart:
        _section_label(d, MARGIN, 132 + dy, "YOUR ORDER")
        y = 176 + dy
        for i, line in enumerate(session.cart):
            dish, qty = line["dish"], line["qty"]
            qf, nf, pf = font("sans_bold", 24), font("sans", 23), font("sans_bold", 21)
            d.text((MARGIN, y), str(qty), font=qf, fill=RED)
            name = session.line_label(line)
            d.text((MARGIN + 36, y + 1), name, font=nf, fill=BLACK)
            price = _money(session.line_price(line) * qty)
            name_end = MARGIN + 36 + d.textlength(name, font=nf)
            price_left = price_rail - d.textlength(price, font=pf)
            lx = name_end + 14                      # dotted leader ties name -> price
            while lx < price_left - 14:
                d.ellipse([lx, y + 16, lx + 2, y + 18], fill=BLACK)
                lx += 11
            d.text((price_left, y + 3), price, font=pf, fill=BLACK)
            if dish["allergens"]:
                d.text((MARGIN + 36, y + 30), "contains " + ", ".join(dish["allergens"]),
                       font=font("sans", 13), fill=RED)
                y += 56
            else:
                y += 46
        _bill_card(d, session, rupee)
        _footer(d, hint or "Say “Hey Lumina” to add more, or to pay.")
    else:
        _render_welcome(d)
        _footer(d, hint or "Say “Hey Lumina” to begin your order.")

    _broadcast_strip(d, broadcast)
    return img


def render_payment(session, upi_url, table="07", vpa="", paid=False):
    """Pay screen: big scannable QR + what the guest is paying for."""
    img = Image.new("RGB", (W, H), WHITE)
    d = ImageDraw.Draw(img)
    rupee = _rupee(font("sans_bold", 20))
    _header(d, table, "Paid · thank you" if paid else "Ready to pay", listening=False)

    if paid:                       # confirmation screen after the money lands
        d.text((MARGIN, 175), "Payment received —", font=font("serif", 38), fill=BLACK)
        d.text((MARGIN, 227), "thank you!", font=font("serif", 38), fill=RED)
        d.text((MARGIN, 296), f"{rupee}{_money(session.total())} paid in full.",
               font=font("sans", 20), fill=BLACK)

        import settings as _st
        _fb = _st.get("feedback_url", "")
        if _fb:
            import payments as _p
            fq = _p.qr_image(_fb, box_size=5, border=1)
            fq = fq.resize((150, 150), Image.NEAREST).convert("L").point(
                lambda v: 255 if v > 128 else 0).convert("RGB")
            fx, fy = W - MARGIN - 150, 170
            img.paste(fq, (fx, fy))
            d.text((fx - 4, fy + 158), "How did we do?", font=font("sans_bold", 14), fill=BLACK)
            d.text((fx - 4, fy + 178), "Scan to tell us", font=font("sans", 13), fill=BLACK)

        _footer(d, "We hope to see you again soon.")
        return img

    # --- QR (left) ---
    # NEAREST resampling keeps the QR strictly black/white; any smoothing would
    # create greys that quantise to RED on this panel and break scanning.
    import payments as _pay
    qr = _pay.qr_image(upi_url, box_size=6, border=1)
    side = 244
    qr = qr.resize((side, side), Image.NEAREST).convert("L").point(
        lambda v: 255 if v > 128 else 0).convert("RGB")
    qx, qy = MARGIN + 10, 146
    d.rounded_rectangle([qx - 12, qy - 12, qx + side + 12, qy + side + 12],
                        radius=10, outline=BLACK, width=2)
    img.paste(qr, (qx, qy))
    _tracked(d, (qx + 2, qy + side + 26), "SCAN WITH ANY UPI APP",
             font("sans_bold", 13), BLACK, 2)

    # --- Details (right) ---
    rx = 360
    _section_label(d, rx, 132, "YOUR BILL")
    y = 176
    for line in session.cart[:5]:
        dish, qty = line["dish"], line["qty"]
        d.text((rx, y), f"{qty}", font=font("sans_bold", 19), fill=RED)
        d.text((rx + 28, y), session.line_label(line)[:24], font=font("sans", 19), fill=BLACK)
        _right(d, W - MARGIN, y + 1, _money(session.line_price(line) * qty),
               font("sans_bold", 18), BLACK)
        y += 30
    if len(session.cart) > 5:
        d.text((rx + 28, y), f"+{len(session.cart) - 5} more", font=font("sans", 15), fill=BLACK)
        y += 26

    y = max(y + 8, 330)
    d.line([rx, y, W - MARGIN, y], fill=BLACK, width=1)
    _tax_note = (f"incl. GST {session.tax():.0f}" if menu.tax_config()[0] == "inclusive"
                 else f"Subtotal {int(session.subtotal())}  ·  GST {session.tax():.0f}")
    d.text((rx, y + 10), _tax_note, font=font("sans", 15), fill=BLACK)
    _tracked(d, (rx, y + 46), "TOTAL DUE", font("sans_bold", 15), BLACK, 3)
    _right(d, W - MARGIN, y + 34, f"{rupee}{_money(session.total())}",
           font("sans_bold", 40), RED)

    _footer(d, f"Paying {vpa or 'the restaurant'} · say “Hey Lumina” if you need help")
    return img


def _render_welcome(d):
    """Empty-cart state: a calm welcome. The menu is on the table already, so we
    don't repeat it here — just invite the guest to speak."""
    d.text((MARGIN, 176), "Welcome to your table.", font=font("serif", 34), fill=BLACK)
    d.text((MARGIN, 236), "I’m Lumina, your dining assistant. Just say",
           font=font("sans", 18), fill=BLACK)
    d.text((MARGIN, 262), "“Hey Lumina” and I’ll take your order, answer",
           font=font("sans", 18), fill=BLACK)
    d.text((MARGIN, 288), "questions about any dish, and settle the bill.",
           font=font("sans", 18), fill=BLACK)


# --- ePaper 3-color quantization ---
_PALETTE = Image.new("P", (1, 1))
_PALETTE.putpalette([255, 255, 255, 0, 0, 0, 210, 25, 25] + [0, 0, 0] * 253)


def to_epaper(img):
    return img.convert("RGB").quantize(palette=_PALETTE, dither=Image.NONE)


if __name__ == "__main__":
    from session import Session
    # With an order
    s = Session()
    s.add_dish(menu.find_dish("butter chicken"), 2)
    s.add_dish(menu.find_dish("butter naan"), 2)
    s.add_dish(menu.find_dish("masala chai"), 1)
    to_epaper(render_order(s)).convert("RGB").save("/home/techiesms/lumina-desk/ui_order.png")
    # Empty / welcome
    to_epaper(render_order(Session())).convert("RGB").save("/home/techiesms/lumina-desk/ui_welcome.png")
    print("saved ui_order.png and ui_welcome.png")
