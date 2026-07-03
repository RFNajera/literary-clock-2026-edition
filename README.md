# Literary Clock — 2026 Edition

A literary clock for the [Pimoroni Inky wHAT](https://shop.pimoroni.com/products/inky-what)
(400 × 300, black & white e-ink) that tells the time using passages from
books — elevated with a split-panel layout, high-contrast typography, and a
live analog clock.

Every minute, the display shows a book quote that contains the current time.
The **time phrase within the quote is bolded** so you can read the time at a
glance, the **book and author** appear below in a contrasting typeface, and a
**two-hand analog clock** with the **weekday and date** fills the right panel.

```
+-----------------------------------+-----------------+
|  Three twenty-three! Is that      |      __         |
|  all? Doesn't time - no, I've     |    /  |  \      |
|  already said that, thought       |   |   +-->|     |   <- analog clock
|  that. I sit and watch the        |   |  /     |    |      (2 hands, no numbers)
|  seconds change on the watch...   |    \____/       |
|                                   |                 |
|  Espedair Street - Iain Banks     |     Friday      |   <- weekday (bold)
|                                   |   Jul 03, 2026  |   <- date
+-----------------------------------+-----------------+
   quote panel (left 2/3)              clock panel (right 1/3)
```

This project takes the idea from
[zenbuffy/LiteraryClock](https://github.com/zenbuffy/LiteraryClock) and
[the original Literary Clock](https://www.instructables.com/Literary-Clock-Made-From-E-reader/)
and rebuilds the presentation layer:

- **Split layout** — the quote occupies the left 2/3; a clock + date occupies the right 1/3.
- **Live rendering** — frames are drawn on the fly each minute (no pre-generated image library to build or store).
- **Bolded time phrase** — the words that spell out the current time stand out in heavy weight.
- **Typographic contrast** — quote set in **Playfair Display**, attribution/date set in **Courier Prime**.
- **Two-hand analog clock** — a clean face (tick marks, no numbers) showing the current time, with the weekday and full date beneath it.
- **Auto-fit** — quote text scales to fit; long attributions wrap to a second line.

## Hardware

- Raspberry Pi (any model with the 40-pin GPIO header — Zero W, 3, 4, etc.)
- Pimoroni Inky wHAT, **black & white** (400 × 300)

## Repository layout

```
literary-clock-2026-edition/
├── literary_clock.py                 # rendering engine (produces a 400x300 PIL image)
├── litclock_annotated_improved.csv   # quotes: HH:MM|time phrase|quote|book|author
├── fonts/
│   ├── PlayfairDisplay.ttf           # quote body + bold time phrase (variable weight)
│   ├── CourierPrime.ttf              # attribution / date
│   ├── CourierPrime-Bold.ttf         # weekday
│   └── *-OFL.txt                     # font licenses (SIL OFL 1.1)
├── scripts/
│   ├── update_display.py             # renders the current minute and pushes to the panel
│   ├── install.sh                    # installs deps + systemd timer on the Pi
│   ├── literary-clock.service        # systemd oneshot unit
│   └── literary-clock.timer          # fires every minute
├── requirements.txt
├── LICENSE
└── README.md
```

## Quick start (on the Raspberry Pi)

```bash
git clone https://github.com/<your-username>/literary-clock-2026-edition.git
cd literary-clock-2026-edition
bash scripts/install.sh
```

The installer will:

1. `pip3 install Pillow inky`
2. Install and enable a systemd timer that refreshes the display every minute.

Draw a single frame immediately to test:

```bash
python3 scripts/update_display.py
```

### Quiet hours (optional)

The bundled service pauses refreshes overnight (01:00–06:00) to reduce e-ink
wear. Adjust the `--sleep-start` / `--sleep-end` flags in
`scripts/literary-clock.service`, then:

```bash
sudo systemctl daemon-reload
sudo systemctl restart literary-clock.timer
```

### Cron alternative

If you prefer cron over systemd:

```cron
* * * * * /usr/bin/python3 /home/pi/literary-clock-2026-edition/scripts/update_display.py --sleep-start 1 --sleep-end 6
```

## Previewing without a display

You can render frames on any computer (no Inky required) to preview the layout:

```bash
pip3 install Pillow

# Render the current time to frame.png
python3 literary_clock.py --out frame.png

# Preview a specific time
python3 literary_clock.py --time 15:23 --out preview.png

# Same, through the driver (identical output, minus the panel push)
python3 scripts/update_display.py --preview preview.png
```

## Customizing

- **Quotes** — edit `litclock_annotated_improved.csv`. Each row is
  `HH:MM|time phrase|quote|book|author` (pipe-delimited). The `time phrase`
  must appear verbatim inside `quote`; that substring is what gets bolded.
- **Fonts** — swap the files in `fonts/` and update the `F_QUOTE` /
  `F_ATTRIB` paths at the top of `literary_clock.py`. If your quote font is a
  variable font with a Weight axis, the bolding uses weight 900 automatically.
- **Layout / clock** — the panel split, clock size, and margins are constants
  near the top of `literary_clock.py`.

## Credits & licensing

- Code: MIT (see [LICENSE](LICENSE)).
- Fonts: [Playfair Display](https://fonts.google.com/specimen/Playfair+Display)
  and [Courier Prime](https://fonts.google.com/specimen/Courier+Prime), SIL OFL 1.1.
- Quote dataset from [zenbuffy/LiteraryClock](https://github.com/zenbuffy/LiteraryClock).
  Individual quotes belong to their respective authors and publishers and are
  used here for a non-commercial, personal project.
