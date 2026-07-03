#!/usr/bin/env python3
"""Literary Clock 2026 Edition — rendering engine.

Renders a 400x300 frame for a black & white Pimoroni Inky wHAT e-ink display.

Layout
------
  +--------------------------+---------------+
  |  QUOTE (2/3 of width)    |  analog clock |
  |  time phrase in BOLD     |   (2 hands)   |
  |                          |               |
  |  Book - Author           |   Weekday     |
  |  (different font)        |   Mon DD, YYYY|
  +--------------------------+---------------+

Fonts (bundled in ./fonts):
  - Playfair Display  -> quote body (regular) and time phrase (bold 900)
  - Courier Prime     -> attribution, weekday, and date (a distinct typeface)

The quote CSV is pipe-delimited:  HH:MM|time phrase|quote|book|author
"""

import csv
import math
import os
import random
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont

# ── Canvas (Inky wHAT native resolution) ───────────────────────────────────────
W, H = 400, 300
BLACK, WHITE = 0, 255
MARGIN = 10

# Panel split: quote on the left 2/3, clock on the right 1/3.
LEFT_W = int(W * 2 / 3)          # ~266 px
RIGHT_X = LEFT_W

# ── Font locations ─────────────────────────────────────────────────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(_HERE, "fonts")
F_QUOTE = os.path.join(FONT_DIR, "PlayfairDisplay.ttf")   # variable weight axis
F_ATTRIB = os.path.join(FONT_DIR, "CourierPrime.ttf")
F_ATTRIB_BOLD = os.path.join(FONT_DIR, "CourierPrime-Bold.ttf")


def _font(path, size, weight=None):
    """Load a font; if it is a variable font, set the Weight axis."""
    fo = ImageFont.truetype(path, size)
    if weight is not None:
        try:
            fo.set_variation_by_axes([weight])
        except Exception:
            pass  # static font — ignore
    return fo


def load_quote(csv_path, hhmm):
    """Return a random (phrase, quote, book, author) tuple for HH:MM, or None."""
    rows = []
    with open(csv_path, encoding="utf-8") as f:
        for parts in csv.reader(f, delimiter="|"):
            if len(parts) < 5:
                continue
            if parts[0] == hhmm:
                rows.append((parts[1], parts[2], parts[3], parts[4]))
    return random.choice(rows) if rows else None


def _wrap_rich(draw, quote, phrase, fnt, fnt_bold, max_w):
    """Split the quote into words, marking those inside the time phrase as bold,
    and wrap the words to fit within max_w. Returns list of lines; each line is a
    list of (word, is_bold, word_width)."""
    lower_q, lower_p = quote.lower(), phrase.lower()
    idx = lower_q.find(lower_p)
    bold_span = (idx, idx + len(phrase)) if idx != -1 else (-1, -1)

    tokens, pos = [], 0
    for word in quote.split(" "):
        start = quote.find(word, pos)
        end = start + len(word)
        pos = end
        tokens.append((word, bold_span[0] <= start < bold_span[1]))

    space_w = draw.textlength(" ", font=fnt)
    lines, line, line_w = [], [], 0
    for word, is_bold in tokens:
        f = fnt_bold if is_bold else fnt
        w = draw.textlength(word, font=f)
        add = w if not line else space_w + w
        if line and line_w + add > max_w:
            lines.append(line)
            line, line_w = [], 0
            add = w
        line.append((word, is_bold, w))
        line_w += add
    if line:
        lines.append(line)
    return lines


def _wrap_attrib(draw, text, fnt, max_w):
    """Word-wrap the attribution to at most two lines, adding an ellipsis if it
    still overflows."""
    words = text.split(" ")
    lines, line = [], ""
    for w in words:
        trial = w if not line else f"{line} {w}"
        if draw.textlength(trial, font=fnt) <= max_w:
            line = trial
        else:
            if line:
                lines.append(line)
            line = w
            if len(lines) == 2:
                break
    if line and len(lines) < 2:
        lines.append(line)
    # If content remains beyond two lines, ellipsize the last one.
    if len(lines) == 2 and draw.textlength(" ".join(words), font=fnt) > 0:
        joined_two = " ".join(lines)
        if joined_two.rstrip() != text.rstrip():
            last = lines[1]
            while draw.textlength(last + "\u2026", font=fnt) > max_w and len(last) > 1:
                last = last[:-1]
            lines[1] = last.rstrip() + "\u2026"
    return lines


def _draw_quote_panel(draw, phrase, quote, book, author):
    max_w = LEFT_W - 2 * MARGIN
    # Auto-fit: shrink font until the quote + attribution fit vertically.
    lines = None
    attrib_lines = []
    for size in (22, 20, 18, 17, 16, 15, 14, 13, 12, 11, 10):
        fq = _font(F_QUOTE, size, 400)
        fb = _font(F_QUOTE, size, 900)
        attrib_size = max(size - 4, 9)
        fa = _font(F_ATTRIB_BOLD, attrib_size)
        line_h = int(size * 1.3)
        lines = _wrap_rich(draw, quote, phrase, fq, fb, max_w)
        attrib_lines = _wrap_attrib(draw, f"{book} - {author}", fa, max_w)
        attrib_h = len(attrib_lines) * int(attrib_size * 1.35) + 10
        if len(lines) * line_h + attrib_h <= H - 2 * MARGIN:
            break

    y = MARGIN
    space_w = draw.textlength(" ", font=fq)
    for line in lines:
        x = MARGIN
        for word, is_bold, w in line:
            draw.text((x, y), word, font=(fb if is_bold else fq), fill=BLACK)
            x += w + space_w
        y += line_h

    # Attribution in a distinct typeface (Courier Prime); wraps up to 2 lines.
    y += 10
    attrib_line_h = int((max(size - 4, 9)) * 1.35)
    for aline in attrib_lines[:2]:
        draw.text((MARGIN, y), aline, font=fa, fill=BLACK)
        y += attrib_line_h


def _draw_clock_panel(draw, now):
    # Divider between the two panels.
    draw.line([(RIGHT_X, MARGIN), (RIGHT_X, H - MARGIN)], fill=BLACK, width=1)

    cx = RIGHT_X + (W - RIGHT_X) // 2
    cy = 95
    r = 52

    # Clean face: circle + tick marks only (no numbers).
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=BLACK, width=2)
    for i in range(12):
        a = math.radians(i * 30)
        x1 = cx + (r - 7) * math.sin(a)
        y1 = cy - (r - 7) * math.cos(a)
        x2 = cx + r * math.sin(a)
        y2 = cy - r * math.cos(a)
        draw.line([(x1, y1), (x2, y2)], fill=BLACK, width=2)

    h = now.hour % 12
    m = now.minute
    # Hour hand.
    ha = math.radians((h + m / 60) * 30)
    hr = r * 0.5
    draw.line([(cx, cy), (cx + hr * math.sin(ha), cy - hr * math.cos(ha))],
              fill=BLACK, width=4)
    # Minute hand.
    ma = math.radians(m * 6)
    mr = r * 0.82
    draw.line([(cx, cy), (cx + mr * math.sin(ma), cy - mr * math.cos(ma))],
              fill=BLACK, width=2)
    draw.ellipse([cx - 3, cy - 3, cx + 3, cy + 3], fill=BLACK)

    # Weekday (bold) + date, in the attribution typeface.
    fday = _font(F_ATTRIB_BOLD, 18)
    fdate = _font(F_ATTRIB, 13)
    day = now.strftime("%A")
    date = now.strftime("%b %d, %Y")
    dy = cy + r + 18
    dw = draw.textlength(day, font=fday)
    draw.text((cx - dw / 2, dy), day, font=fday, fill=BLACK)
    dtw = draw.textlength(date, font=fdate)
    draw.text((cx - dtw / 2, dy + 24), date, font=fdate, fill=BLACK)


def render(csv_path, when=None, out=None):
    """Render a frame. Returns a PIL Image (and saves to `out` if given)."""
    now = when or datetime.now()
    hhmm = now.strftime("%H:%M")
    row = load_quote(csv_path, hhmm)
    if row is None:
        # Fallback so the display is never blank.
        row = ("", f"The time is {now.strftime('%-I:%M')}.", "Literary Clock", "2026 Edition")
    phrase, quote, book, author = row

    img = Image.new("L", (W, H), WHITE)
    draw = ImageDraw.Draw(img)
    _draw_quote_panel(draw, phrase, quote, book, author)
    _draw_clock_panel(draw, now)

    if out:
        img.save(out)
    return img


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="Render a literary-clock frame.")
    p.add_argument("--csv", default=os.path.join(_HERE, "litclock_annotated_improved.csv"))
    p.add_argument("--time", help="Override time as HH:MM (for previews).")
    p.add_argument("--out", default="frame.png", help="Output PNG path.")
    args = p.parse_args()

    when = None
    if args.time:
        hh, mm = args.time.split(":")
        when = datetime.now().replace(hour=int(hh), minute=int(mm), second=0)
    render(args.csv, when=when, out=args.out)
    print(f"Wrote {args.out}")
