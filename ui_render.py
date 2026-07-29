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


def _fit(draw, s, fnt, width):
    """Trim `s` to `width` px, breaking on a space so it never reads like a typo
    ("Cheese Stuffed Garlic Br"). Falls back to a hard cut for one long word."""
    if draw.textlength(s, font=fnt) <= width:
        return s
    ell = "…"
    words = s.split()
    while len(words) > 1:
        words.pop()
        cut = " ".join(words) + ell
        if draw.textlength(cut, font=fnt) <= width:
            return cut
    while s and draw.textlength(s + ell, font=fnt) > width:
        s = s[:-1]
    return s + ell


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


def _assistant_state():
    try:
        import settings
        return settings.get("assistant_state", "active")
    except Exception:
        return "active"


def _mute_glyph(d, cx, cy, color):
    """A small speaker with a slash — reads as 'muted' at a glance."""
    d.polygon([(cx - 7, cy - 3), (cx - 3, cy - 3), (cx + 1, cy - 8),
               (cx + 1, cy + 8), (cx - 3, cy + 3), (cx - 7, cy + 3)], fill=color)
    d.line([cx + 4, cy - 7, cx + 12, cy + 7], fill=color, width=2)
    d.line([cx + 12, cy - 7, cx + 4, cy + 7], fill=color, width=2)


def _header(d, table, status, listening):
    _brandmark(d, MARGIN + 8, 52)
    _tracked(d, (MARGIN + 28, 30), _brand().upper(), font("serif_bold", 44), BLACK, 3)
    _tracked(d, (MARGIN + 30, 82), "PURE VEG  ·  PIZZA & MORE", font("sans", 12), BLACK, 4)

    # Right: table (bold) centred against the wordmark, status aligned with the
    # tagline row beneath it.
    tf = font("sans_bold", 18)
    _right(d, W - MARGIN, 43, f"Table {table}", tf, BLACK)

    # When the mic is closed, say so plainly — otherwise a guest would talk to a
    # screen that has quietly stopped listening.
    state = _assistant_state()
    if state in ("muted", "off"):
        label = "Mic off" if state == "muted" else "Voice off"
        sf = font("sans_bold", 15)
        sw = d.textlength(label, font=sf)
        bx0 = W - MARGIN - sw - 56
        d.rounded_rectangle([bx0, 76, W - MARGIN, 104], radius=14, outline=RED, width=2)
        _mute_glyph(d, bx0 + 20, 90, RED)
        d.text((bx0 + 42, 80), label, font=sf, fill=RED)
    else:
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


def render_order(session, table="07", status="Listening", hint=None, kitchen=None):
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
            price = _money(session.line_price(line) * qty)
            # keep the name clear of the price so the dotted leader always shows
            room = price_rail - (MARGIN + 36) - d.textlength(price, font=pf) - 24
            name = _fit(d, session.line_label(line), nf, room)
            d.text((MARGIN + 36, y + 1), name, font=nf, fill=BLACK)
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
        _footer(d, hint or ("Say “Hey Lumina” to add more, or to pay."
                            if _assistant_state() == "active" else
                            "Mic off · middle button shows your bill, left calls a server"))
    else:
        _render_welcome(d)
        _footer(d, hint or "Pure veg  ·  Pizzas, burgers, momos, shakes  ·  Table service by voice")

    return img


def _seal(d, cx, cy, r=34):
    """A struck-seal motif: double ring + tick. Reads as 'settled' instantly and
    gives the screen a centre of gravity the old left-aligned layout lacked."""
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=RED, width=3)
    d.ellipse([cx - r + 7, cy - r + 7, cx + r - 7, cy + r - 7], outline=RED, width=1)
    d.line([cx - 15, cy + 1, cx - 5, cy + 12], fill=RED, width=4)
    d.line([cx - 5, cy + 12, cx + 16, cy - 13], fill=RED, width=4)


def _render_thanks(session, table, rupee):
    """Closing screen. Centred and calm — the meal is done, so this is the one
    screen that gets to be quiet: seal, thanks, what was paid, and a small
    invitation to leave feedback."""
    img = Image.new("RGB", (W, H), WHITE)
    d = ImageDraw.Draw(img)
    _header(d, table, "Paid", listening=False)

    import settings as _st
    fb = _st.get("feedback_url", "")
    cx = W // 2 if not fb else 300          # shift left to make room for the QR

    _seal(d, cx, 222)

    tf = font("serif", 40)
    tw = d.textlength("Thank you", font=tf)
    d.text((cx - tw / 2, 276), "Thank you", font=tf, fill=BLACK)

    sf = font("sans", 17)
    line = f"{rupee}{_money(session.total())} paid in full"   # table is in the header
    lw = d.textlength(line, font=sf)
    d.text((cx - lw / 2, 334), line, font=sf, fill=BLACK)

    # A hairline rule under the block ties it to the rest of the design system.
    d.line([cx - 110, 372, cx + 110, 372], fill=BLACK, width=1)
    cf = font("sans", 15)
    cl = "Come back soon"
    cw = d.textlength(cl, font=cf)
    d.text((cx - cw / 2, 384), cl, font=cf, fill=BLACK)

    if fb:
        import payments as _p
        q = _p.qr_image(fb, box_size=5, border=1)
        q = q.resize((150, 150), Image.NEAREST).convert("L").point(
            lambda v: 255 if v > 128 else 0).convert("RGB")
        qx, qy = W - MARGIN - 176, 186
        d.rounded_rectangle([qx - 13, qy - 13, qx + 163, qy + 205], radius=12,
                            outline=BLACK, width=2)
        img.paste(q, (qx, qy))
        _tracked(d, (qx + 2, qy + 168), "HOW DID WE DO?", font("sans_bold", 13), BLACK, 1)
        d.text((qx + 2, qy + 186), "Scan to tell us", font=font("sans", 13), fill=BLACK)

    return img


def render_payment(session, upi_url, table="07", vpa="", paid=False):
    """Pay screen: big scannable QR + what the guest is paying for."""
    img = Image.new("RGB", (W, H), WHITE)
    d = ImageDraw.Draw(img)
    rupee = _rupee(font("sans_bold", 20))
    _header(d, table, "Paid · thank you" if paid else "Ready to pay", listening=False)

    if paid:
        return _render_thanks(session, table, rupee)

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
        nf, pf = font("sans", 19), font("sans_bold", 18)
        total = _money(session.line_price(line) * qty)
        # leave room for the price on the right, then trim the name to what's left
        room = (W - MARGIN) - (rx + 28) - d.textlength(total, font=pf) - 16
        d.text((rx + 28, y), _fit(d, session.line_label(line), nf, room), font=nf, fill=BLACK)
        _right(d, W - MARGIN, y + 1, total, pf, BLACK)
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

    _footer(d, f"Paying {vpa or 'the restaurant'} · "
            + ("say “Hey Lumina” if you need help" if _assistant_state() == "active"
               else "press the left button if you need help"))
    return img


def _render_welcome(d):
    """Empty-cart state. The printed menu is already on the table, so this screen
    doesn't repeat it — it teaches the one thing a new guest needs to know: the
    wake word, and the three things worth asking for.

    When the mic is closed it must not invite anyone to talk to it. A guest who
    speaks to a dead screen and gets nothing back blames the restaurant."""
    state = _assistant_state()
    if state != "active":
        d.text((MARGIN, 156), "The microphone is", font=font("sans", 20), fill=BLACK)
        d.text((MARGIN, 186), "switched off", font=font("serif_bold", 46), fill=RED)
        d.text((MARGIN, 258),
               "Press the right-hand button to turn it back on."
               if state == "muted" else "Please order with a member of staff.",
               font=font("sans", 18), fill=BLACK)
        y = 300
        for line in ("Left button  ·  call a server",
                     "Middle button  ·  show your bill"):
            d.ellipse([MARGIN + 2, y + 7, MARGIN + 8, y + 13], fill=RED)
            d.text((MARGIN + 22, y), line, font=font("sans", 17), fill=BLACK)
            y += 28
        return

    d.text((MARGIN, 156), "Just say", font=font("sans", 20), fill=BLACK)
    d.text((MARGIN, 186), "“Hey Lumina”", font=font("serif_bold", 46), fill=RED)

    d.text((MARGIN, 258), "…and order without waiting for anyone.",
           font=font("sans", 18), fill=BLACK)

    # Three concrete openers, so nobody has to guess what it understands.
    y = 300
    for line in ('"One large Margherita"',
                 '"What\'s in the Paneer Tikka?"',
                 '"What\'s my bill?"'):
        d.ellipse([MARGIN + 2, y + 7, MARGIN + 8, y + 13], fill=RED)
        d.text((MARGIN + 22, y), line, font=font("sans", 17), fill=BLACK)
        y += 28


# --- ePaper 3-color quantization ---
_PALETTE = Image.new("P", (1, 1))
_PALETTE.putpalette([255, 255, 255, 0, 0, 0, 210, 25, 25] + [0, 0, 0] * 253)


def to_epaper(img):
    return img.convert("RGB").quantize(palette=_PALETTE, dither=Image.NONE)


if __name__ == "__main__":
    # Renders every panel state to docs/images/ — exactly what the ePaper shows,
    # so the screenshots in the README can never drift from the real code.
    #   ./venv/bin/python ui_render.py
    import pathlib

    import payments
    import settings
    from session import Session

    # Render the docs against a demo venue, so nobody's real UPI ID or feedback
    # form ends up in a public screenshot.
    _real = settings.get
    _demo = {"upi_vpa": "auntynoz@upi", "upi_payee": "Auntyno-Z Pizza",
             "feedback_url": "https://forms.gle/luminadesk"}
    settings.get = lambda k, d=None: _demo.get(k, _real(k, d))

    out = pathlib.Path(__file__).parent / "docs" / "images"
    out.mkdir(parents=True, exist_ok=True)

    def save(img, name):
        to_epaper(img).convert("RGB").save(out / f"epaper-{name}.png")

    def order():
        s = Session()
        s.add_dish(menu.find_dish("margherita"), 1, "Large")
        s.add_dish(menu.find_dish("cheese stuffed garlic bread"), 2)
        s.add_dish(menu.find_dish("cold coffee"), 2)
        return s

    save(render_order(Session()), "welcome")
    save(render_order(order()), "order")
    save(render_order(order(), kitchen="preparing"), "preparing")

    _demo["assistant_state"] = "muted"      # the badge reads Settings, not `status`
    save(render_order(order()), "muted")
    del _demo["assistant_state"]

    url, _ = payments.upi_url(order().total(), "07")
    save(render_payment(order(), url, vpa="auntynoz@upi"), "pay")
    save(render_payment(order(), url, paid=True), "thanks")
    print(f"saved 6 panel states to {out}")
