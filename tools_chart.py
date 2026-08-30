"""Render the README's latency chart to PNG (light + dark).

The numbers are the ones `tools_bench.py` measured on this Pi and that the
README already publishes as a table — this draws the same figures, it does not
re-measure them. Keep the two in step: if the table changes, change STAGES.

Usage:  ./venv/bin/python tools_chart.py
"""
import os
import subprocess
import tempfile

OUT_DIR = "docs/images"

# Stage order matches the order time is actually spent, left to right.
# "Compute the reply" is under 1 ms — a segment for it would be a third of a
# pixel, so it lives in the footnote instead of pretending to be a band.
STAGES = ["Speech → text", "Understanding", "First word out"]

ROWS = [
    ("Fact question", "offline voice (Piper)", [264, 5, 250]),
    ("Fact question", "natural voice (online)", [264, 5, 700]),
    ("Ordering", "offline voice (Piper)", [264, 500, 250]),
    ("Ordering", "natural voice (online)", [264, 500, 700]),
]

# Validated with the skill's validate_palette.js: light and dark both pass the
# lightness band, chroma floor and CVD separation. Light warns on contrast for
# aqua and yellow, which is why every bar carries visible direct labels.
LIGHT = dict(surface="#fcfcfb", ink="#0b0b0b", ink2="#52514e", muted="#898781",
             grid="#e1e0d9", axis="#c3c2b7",
             series=["#2a78d6", "#1baf7a", "#eda100"], on_fill="#ffffff")
DARK = dict(surface="#1a1a19", ink="#ffffff", ink2="#c3c2b7", muted="#898781",
            grid="#2c2c2a", axis="#383835",
            series=["#3987e5", "#199e70", "#c98500"], on_fill="#0b0b0b")

W, H = 1040, 430
PAD_L, PAD_R, PAD_T = 268, 96, 96
AXIS_MAX = 1500                      # ms
BAR_H, GAP = 34, 22
PLOT_W = W - PAD_L - PAD_R
SCALE = PLOT_W / AXIS_MAX


def _svg(c):
    p = []
    add = p.append
    add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}" font-family="system-ui,-apple-system,Segoe UI,sans-serif">')
    add(f'<rect width="{W}" height="{H}" fill="{c["surface"]}"/>')

    add(f'<text x="32" y="42" font-size="21" font-weight="600" fill="{c["ink"]}">'
        f'Where a reply&#8217;s time goes</text>')
    add(f'<text x="32" y="66" font-size="13.5" fill="{c["ink2"]}">'
        f'Median on a Raspberry Pi 5, wake word to first word out of the speaker</text>')

    # Legend — always present for 3 series, and the identity anchor for the
    # light-mode contrast relief.
    lx = 32
    for i, name in enumerate(STAGES):
        add(f'<rect x="{lx}" y="{PAD_T - 26}" width="11" height="11" rx="2.5" '
            f'fill="{c["series"][i]}"/>')
        add(f'<text x="{lx + 17}" y="{PAD_T - 16}" font-size="12.5" '
            f'fill="{c["ink2"]}">{name}</text>')
        lx += 22 + len(name) * 7.1

    # Gridlines every 250 ms, behind the bars.
    for ms in range(0, AXIS_MAX + 1, 250):
        x = PAD_L + ms * SCALE
        add(f'<line x1="{x:.1f}" y1="{PAD_T}" x2="{x:.1f}" y2="{PAD_T + len(ROWS)*(BAR_H+GAP)}" '
            f'stroke="{c["grid"]}" stroke-width="1"/>')
        add(f'<text x="{x:.1f}" y="{PAD_T + len(ROWS)*(BAR_H+GAP) + 20}" font-size="11.5" '
            f'text-anchor="middle" fill="{c["muted"]}">'
            f'{"0" if ms == 0 else f"{ms/1000:.2f}".rstrip("0").rstrip(".") + "s"}</text>')

    for r, (title, sub, vals) in enumerate(ROWS):
        y = PAD_T + r * (BAR_H + GAP)
        add(f'<text x="{PAD_L - 18}" y="{y + 15}" font-size="13.5" font-weight="600" '
            f'text-anchor="end" fill="{c["ink"]}">{title}</text>')
        add(f'<text x="{PAD_L - 18}" y="{y + 31}" font-size="11.5" '
            f'text-anchor="end" fill="{c["muted"]}">{sub}</text>')

        x = PAD_L
        for i, v in enumerate(vals):
            w = v * SCALE
            first, last = i == 0, i == len(vals) - 1
            # 4px rounded data-end on the outer edges only; inner joins stay
            # square so the segments read as one bar.
            r_l, r_r = (4 if first else 0), (4 if last else 0)
            add(f'<path d="{_rounded(x, y, max(w - 2, 1), BAR_H, r_l, r_r)}" '
                f'fill="{c["series"][i]}"/>')
            if w > 46:
                add(f'<text x="{x + w/2 - 1:.1f}" y="{y + BAR_H/2 + 4.5:.1f}" '
                    f'font-size="12" font-weight="600" text-anchor="middle" '
                    f'fill="{c["on_fill"]}">{v}</text>')
            x += w

        total = sum(vals)
        add(f'<text x="{x + 12:.1f}" y="{y + BAR_H/2 + 5:.1f}" font-size="14" '
            f'font-weight="600" fill="{c["ink"]}">{total/1000:.2f}s</text>')

    add(f'<line x1="{PAD_L}" y1="{PAD_T + len(ROWS)*(BAR_H+GAP)}" x2="{PAD_L + PLOT_W}" '
        f'y2="{PAD_T + len(ROWS)*(BAR_H+GAP)}" stroke="{c["axis"]}" stroke-width="1"/>')
    # Two lines: SVG text doesn't wrap, and one line of this ran off the edge.
    for i, line in enumerate((
            "Computing the reply — menu lookup, totals, allergens — is under 1 ms "
            "and too small to draw.",
            "Understanding is ~5 ms when the rule parser handles the turn, "
            "~500 ms when it goes to the cloud model.")):
        add(f'<text x="32" y="{H - 30 + i * 17}" font-size="11.5" '
            f'fill="{c["muted"]}">{line}</text>')
    add("</svg>")
    return "\n".join(p)


def _rounded(x, y, w, h, rl, rr):
    """A bar path with independent left/right corner radii."""
    return (f"M{x + rl:.1f},{y} H{x + w - rr:.1f} "
            f"{f'a{rr},{rr} 0 0 1 {rr},{rr}' if rr else ''} V{y + h - rr:.1f} "
            f"{f'a{rr},{rr} 0 0 1 -{rr},{rr}' if rr else ''} H{x + rl:.1f} "
            f"{f'a{rl},{rl} 0 0 1 -{rl},-{rl}' if rl else ''} V{y + rl:.1f} "
            f"{f'a{rl},{rl} 0 0 1 {rl},-{rl}' if rl else ''} Z")


def render(mode, colours, out):
    html = (f'<!doctype html><meta charset="utf-8">'
            f'<style>html,body{{margin:0;padding:0;background:{colours["surface"]}}}</style>'
            f'{_svg(colours)}')
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as f:
        f.write(html)
        path = f.name
    try:
        subprocess.run(
            ["chromium", "--headless=new", "--disable-gpu", "--no-sandbox",
             "--hide-scrollbars", "--force-device-scale-factor=2",
             f"--screenshot={out}", f"--window-size={W},{H}", f"file://{path}"],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    finally:
        os.unlink(path)
    print("  %s  (%s)" % (out, mode))


if __name__ == "__main__":
    os.makedirs(OUT_DIR, exist_ok=True)
    render("light", LIGHT, os.path.join(OUT_DIR, "chart-latency.png"))
    render("dark", DARK, os.path.join(OUT_DIR, "chart-latency-dark.png"))
