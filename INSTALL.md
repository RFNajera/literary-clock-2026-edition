# Installing on a Raspberry Pi

Tested on **Raspberry Pi OS 13 "Trixie"** (Debian 13, Python 3.13) with a
**Pimoroni Inky wHAT** (400 × 300, black & white).

## TL;DR — clone, run, reboot, go

On a fresh Pi (SSH in first):

```bash
git clone https://github.com/RFNajera/literary-clock-2026-edition.git
cd literary-clock-2026-edition
./scripts/install.sh
sudo reboot
```

That's it. After the reboot the panel updates every minute on its own.

## What the installer does

`scripts/install.sh` is safe to re-run and handles everything:

1. **Enables SPI and I2C** (the Inky wHAT needs both).
2. **Installs the Pimoroni Inky driver** into a virtual environment at
   `~/.virtualenvs/pimoroni`.
3. **Installs Pillow** into that same environment.
4. **Adds a cron job** that renders the current minute's quote to the panel
   every minute (paused 01:00–06:00 to reduce e-ink wear).

## Why a virtual environment (Trixie / PEP 668)

On Raspberry Pi OS Trixie, the system Python is "externally managed"
([PEP 668](https://peps.python.org/pep-0668/)). A plain `pip install` fails with:

```
error: externally-managed-environment
```

So the display libraries live in a virtual environment instead of the system
Python. Pimoroni's own installer creates one at `~/.virtualenvs/pimoroni`, and
this project reuses it. Every command below and the cron job call that
environment's Python explicitly:

```
/home/pi/.virtualenvs/pimoroni/bin/python3
```

You do **not** need to activate the environment for the clock to run — cron uses
the full path. Activate it only if you want to run commands by hand:

```bash
source ~/.virtualenvs/pimoroni/bin/activate
```

## Verify it works

Draw one frame immediately:

```bash
~/.virtualenvs/pimoroni/bin/python3 ~/literary-clock-2026-edition/scripts/update_display.py
```

Preview to a PNG instead of the panel (no Inky required):

```bash
~/.virtualenvs/pimoroni/bin/python3 ~/literary-clock-2026-edition/scripts/update_display.py --preview frame.png
```

## Managing the schedule

The refresh is a cron job. View or edit it with:

```bash
crontab -l      # show
crontab -e      # edit
```

The installed line:

```cron
* * * * * /home/pi/.virtualenvs/pimoroni/bin/python3 /home/pi/literary-clock-2026-edition/scripts/update_display.py --sleep-start 1 --sleep-end 6
```

Change `--sleep-start` / `--sleep-end` (24-hour clock) to adjust the overnight
quiet window, or remove them to keep refreshing 24/7.

## systemd alternative (optional)

If you prefer a systemd timer over cron, the units in this folder point at the
venv Python. Install them with:

```bash
sudo cp scripts/literary-clock.service /etc/systemd/system/
sudo cp scripts/literary-clock.timer   /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now literary-clock.timer
```

Make sure the paths and `User=` in `literary-clock.service` match your setup,
and remove the cron line first so the clock isn't driven twice.

## Troubleshooting

- **Panel doesn't update / SPI errors** — confirm SPI is on
  (`ls /dev/spidev*` should list a device). If you see a chip-select error, add
  `dtoverlay=spi0-0cs` to `/boot/firmware/config.txt` and reboot.
- **`externally-managed-environment` when installing by hand** — you're using
  the system Python. Use the venv path shown above, or
  `source ~/.virtualenvs/pimoroni/bin/activate` first.
- **Wrong username** — these docs assume the `pi` user. If your username
  differs, the installer still works (it uses `$HOME`); just substitute your
  home path anywhere you copy a command manually.
- **Nothing at a given minute** — not every minute has a quote in the CSV; the
  display shows a simple time fallback for those. This is expected.
