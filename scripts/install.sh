#!/usr/bin/env bash
#
# Literary Clock 2026 — one-shot installer for Raspberry Pi OS (Trixie / Debian 13).
#
#   git clone https://github.com/RFNajera/literary-clock-2026-edition.git
#   cd literary-clock-2026-edition
#   ./scripts/install.sh
#   sudo reboot
#
# What it does:
#   1. Enables SPI + I2C (needed by the Inky wHAT).
#   2. Creates a virtual environment at ~/.virtualenvs/pimoroni and installs the
#      Inky driver + Pillow into it. A venv is required on Trixie, where
#      system-wide pip is blocked by PEP 668 ("externally-managed-environment").
#      We build the venv ourselves and pip-install directly, so the install is
#      fully non-interactive (no prompts from Pimoroni's own installer).
#   3. Adds a per-minute cron job that renders the current quote to the panel.
#
# Safe to re-run: it detects an existing venv and an existing cron line and
# will not duplicate them.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${HOME}/.virtualenvs/pimoroni"
VENV_PY="${VENV_DIR}/bin/python3"
DRIVER="${REPO_DIR}/scripts/update_display.py"
CRON_LINE="* * * * * ${VENV_PY} ${DRIVER} --sleep-start 1 --sleep-end 6"

say() { printf "\n\033[1;36m==> %s\033[0m\n" "$1"; }

# ── 1. Enable SPI + I2C ─────────────────────────────────────────────────────────
say "Enabling SPI and I2C interfaces"
if command -v raspi-config >/dev/null 2>&1; then
    sudo raspi-config nonint do_spi 0 || true
    sudo raspi-config nonint do_i2c 0 || true
else
    echo "raspi-config not found — enable SPI and I2C manually if the panel does not update."
fi

# ── 2. Create the virtual environment and install Inky + Pillow ─────────────────
# We build the venv explicitly (with access to the system apt-installed GPIO/SPI
# packages) and pip-install into it directly. This avoids Pimoroni's interactive
# "create a virtual environment? [y/N]" prompt entirely, so the run is
# deterministic and unattended.
say "Installing prerequisites (git, python3-venv)"
sudo apt-get update -y
sudo apt-get install -y git python3-venv python3-full

if [ ! -x "${VENV_PY}" ]; then
    say "Creating virtual environment at ${VENV_DIR}"
    mkdir -p "$(dirname "${VENV_DIR}")"
    # --system-site-packages lets the venv see apt-provided RPi.GPIO / spidev,
    # which the Inky driver relies on for hardware access.
    python3 -m venv --system-site-packages "${VENV_DIR}"
else
    say "Virtual environment already exists at ${VENV_DIR} — reusing it"
fi

say "Installing the Inky driver and Pillow into the environment"
"${VENV_PY}" -m pip install --upgrade pip
"${VENV_PY}" -m pip install --upgrade inky Pillow

# Sanity check that the display library imports.
if "${VENV_PY}" -c "import inky" >/dev/null 2>&1; then
    echo "Inky driver installed successfully."
else
    echo "WARNING: the 'inky' package did not import cleanly. The clock will"
    echo "still render frames, but pushing to the panel may fail. Re-run this"
    echo "installer or check the pip output above."
fi

# ── 3. Install the per-minute cron job ──────────────────────────────────────────
say "Installing the per-minute refresh cron job"
CURRENT_CRON="$(crontab -l 2>/dev/null || true)"
if printf '%s\n' "${CURRENT_CRON}" | grep -Fq "${DRIVER}"; then
    echo "A cron entry for the Literary Clock already exists — leaving it as-is."
else
    printf '%s\n%s\n' "${CURRENT_CRON}" "${CRON_LINE}" | sed '/^$/d' | crontab -
    echo "Added: ${CRON_LINE}"
fi

# ── Done ────────────────────────────────────────────────────────────────────────
say "Installation complete"
cat <<EOF

The clock will refresh every minute (paused 01:00-06:00 to save the panel).

Draw a frame right now to confirm it works:
    ${VENV_PY} ${DRIVER}

Preview to a file instead of the panel:
    ${VENV_PY} ${DRIVER} --preview frame.png

Now reboot to finish enabling SPI/I2C:
    sudo reboot
EOF
