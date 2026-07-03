#!/usr/bin/env python3
"""Render the current minute's literary-clock frame and push it to the display.

Designed to run once per minute from cron or a systemd timer on a Raspberry Pi
driving a Pimoroni Inky wHAT (black & white). It renders live (no pre-generated
image library needed) and updates the e-ink panel.

Usage (on the Pi):
    python3 scripts/update_display.py

Options:
    --preview PATH   Save the frame to PATH instead of drawing to the panel
                     (useful on a machine without an Inky attached).
    --sleep-start H  Hour (0-23) to stop refreshing to save wear/power.
    --sleep-end   H  Hour (0-23) to resume refreshing.
"""

import argparse
import os
import sys
from datetime import datetime

# Make the package importable whether run from repo root or scripts/.
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _ROOT)

from literary_clock import render  # noqa: E402

CSV = os.path.join(_ROOT, "litclock_annotated_improved.csv")


def push_to_inky(img):
    """Send the rendered image to the Inky wHAT (black & white).

    render() returns an 8-bit grayscale ("L") image where 0 = black ink and
    255 = white background. The Inky library does not interpret raw grayscale
    or a generic palette correctly for e-ink; it expects a mode "P" image whose
    pixels are the display's own palette indices (display.BLACK / display.WHITE).
    So we build a "P" image sized to the panel and map every pixel accordingly.
    """
    from PIL import Image
    from inky.auto import auto

    # ask_user=False so it runs unattended under cron (no terminal to prompt).
    display = auto(ask_user=False, verbose=False)

    # Match the panel's resolution and orientation exactly.
    src = img.convert("L").resize(display.resolution)
    # Threshold to pure black/white, then map to the Inky palette indices.
    bw = src.point(lambda p: 255 if p >= 128 else 0, mode="1")

    out = Image.new("P", display.resolution, display.WHITE)
    black_mask = bw.point(lambda p: 255 if p == 0 else 0, mode="1")
    # Paint black ink where the source was dark.
    black_layer = Image.new("P", display.resolution, display.BLACK)
    out.paste(black_layer, (0, 0), black_mask)

    try:
        display.set_border(display.WHITE)
    except (NotImplementedError, AttributeError):
        pass

    display.set_image(out)
    display.show()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--preview", help="Save frame to this path instead of the panel.")
    p.add_argument("--sleep-start", type=int, default=None,
                   help="Hour to stop refreshing (inclusive).")
    p.add_argument("--sleep-end", type=int, default=None,
                   help="Hour to resume refreshing (exclusive).")
    args = p.parse_args()

    now = datetime.now()

    # Optional quiet hours to reduce refresh wear overnight.
    if args.sleep_start is not None and args.sleep_end is not None:
        if args.sleep_start <= now.hour < args.sleep_end:
            return

    img = render(CSV, when=now)

    if args.preview:
        img.save(args.preview)
        print(f"Preview written to {args.preview}")
        return

    push_to_inky(img)


if __name__ == "__main__":
    main()
