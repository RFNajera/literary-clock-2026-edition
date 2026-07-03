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

import calendar
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
# Bitter (slab serif) is used for the quote: its even, sturdy stroke weight
# stays crisp on the 1-bit (pure black/white, no anti-aliasing) e-ink panel,
# unlike a high-contrast serif whose hairline strokes fragment. Courier Prime
# (a distinct typewriter face) is kept for the attribution, weekday, and date.
F_QUOTE = os.path.join(FONT_DIR, "Bitter.ttf")            # variable weight axis
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


def _draw_analog_clock(draw, cx, cy, r, now):
    """Draw a clean two-hand clock (tick marks, no numbers) centered at cx,cy."""
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=BLACK, width=2)
    for i in range(12):
        a = math.radians(i * 30)
        x1 = cx + (r - 6) * math.sin(a)
        y1 = cy - (r - 6) * math.cos(a)
        x2 = cx + r * math.sin(a)
        y2 = cy - r * math.cos(a)
        draw.line([(x1, y1), (x2, y2)], fill=BLACK, width=2)

    h = now.hour % 12
    m = now.minute
    ha = math.radians((h + m / 60) * 30)
    hr = r * 0.5
    draw.line([(cx, cy), (cx + hr * math.sin(ha), cy - hr * math.cos(ha))],
              fill=BLACK, width=4)
    ma = math.radians(m * 6)
    mr = r * 0.82
    draw.line([(cx, cy), (cx + mr * math.sin(ma), cy - mr * math.cos(ma))],
              fill=BLACK, width=2)
    draw.ellipse([cx - 3, cy - 3, cx + 3, cy + 3], fill=BLACK)


def _draw_month_calendar(draw, panel_x, panel_w, top_y, now):
    """Draw a compact month grid with weekday headers and today's date bolded
    and boxed. Sunday-first columns."""
    # Title: e.g. "July 2026"
    ftitle = _font(F_ATTRIB_BOLD, 13)
    title = now.strftime("%B %Y")
    # Trim if it somehow exceeds the panel width.
    while draw.textlength(title, font=ftitle) > panel_w - 6 and len(title) > 4:
        ftitle = _font(F_ATTRIB_BOLD, 11)
        break
    tw = draw.textlength(title, font=ftitle)
    cx = panel_x + panel_w / 2
    draw.text((cx - tw / 2, top_y), title, font=ftitle, fill=BLACK)

    # Grid geometry: 7 columns fit in the panel with small side padding.
    pad = 6
    grid_x = panel_x + pad
    grid_w = panel_w - 2 * pad
    col_w = grid_w / 7.0
    row_h = 13
    header_y = top_y + 20

    fhdr = _font(F_ATTRIB_BOLD, 9)
    fnum = _font(F_ATTRIB, 10)
    fnum_b = _font(F_ATTRIB_BOLD, 10)

    # Weekday headers (single letters), Sunday first.
    headers = ["S", "M", "T", "W", "T", "F", "S"]
    for i, hd in enumerate(headers):
        hx = grid_x + i * col_w + col_w / 2
        hw = draw.textlength(hd, font=fhdr)
        draw.text((hx - hw / 2, header_y), hd, font=fhdr, fill=BLACK)

    # Month matrix, Sunday-first weeks.
    cal = calendar.Calendar(firstweekday=6)  # 6 = Sunday
    weeks = cal.monthdayscalendar(now.year, now.month)
    first_row_y = header_y + 14
    for wk, week in enumerate(weeks):
        for i, day in enumerate(week):
            if day == 0:
                continue
            s = str(day)
            is_today = (day == now.day)
            f = fnum_b if is_today else fnum
            cell_cx = grid_x + i * col_w + col_w / 2
            cell_cy = first_row_y + wk * row_h + row_h / 2
            sw = draw.textlength(s, font=f)
            # Vertically center the digit within its row/box.
            draw.text((cell_cx - sw / 2, cell_cy - 5), s, font=f, fill=BLACK)
            if is_today:
                # Box today's date for a clear highlight on 1-bit e-ink.
                bx0 = grid_x + i * col_w + 1
                bx1 = grid_x + (i + 1) * col_w - 1
                by0 = first_row_y + wk * row_h + 0
                by1 = first_row_y + (wk + 1) * row_h - 1
                draw.rectangle([bx0, by0, bx1, by1], outline=BLACK, width=2)


def _draw_clock_panel(draw, now):
    # Divider between the two panels.
    draw.line([(RIGHT_X, MARGIN), (RIGHT_X, H - MARGIN)], fill=BLACK, width=1)

    panel_x = RIGHT_X
    panel_w = W - RIGHT_X

    # Analog clock: pushed to the TOP of the right panel.
    cx = panel_x + panel_w // 2
    r = 46
    cy = MARGIN + r + 4
    _draw_analog_clock(draw, cx, cy, r, now)

    # Month calendar fills the BOTTOM of the right panel.
    cal_top = cy + r + 12
    _draw_month_calendar(draw, panel_x, panel_w, cal_top, now)


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
