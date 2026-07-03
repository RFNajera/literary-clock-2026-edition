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
#   2. Installs the Pimoroni Inky driver into a virtual environment
#      (~/.virtualenvs/pimoroni) — required on Trixie, where system-wide pip is
#      blocked by PEP 668 ("externally-managed-environment").
#   3. Installs Pillow into that same environment.
#   4. Adds a per-minute cron job that renders the current quote to the panel.
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

# ── 2. Install the Pimoroni Inky driver into a virtualenv ───────────────────────
if [ -x "${VENV_PY}" ] && "${VENV_PY}" -c "import inky" >/dev/null 2>&1; then
    say "Pimoroni Inky driver already present in ${VENV_DIR} — skipping"
else
    say "Installing the Pimoroni Inky driver (creates ${VENV_DIR})"
    sudo apt-get update -y
    sudo apt-get install -y git python3-venv
    TMP_INKY="$(mktemp -d)"
    git clone --depth=1 https://github.com/pimoroni/inky "${TMP_INKY}/inky"
    # Pimoroni's installer creates and populates ~/.virtualenvs/pimoroni.
    # Answer prompts non-interactively where possible.
    ( cd "${TMP_INKY}/inky" && yes | ./install.sh ) || \
      ( cd "${TMP_INKY}/inky" && ./install.sh )
    rm -rf "${TMP_INKY}"
fi

# Fallback: if the venv still doesn't exist (installer layout changed), build a
# minimal one so the clock can still run.
if [ ! -x "${VENV_PY}" ]; then
    say "Creating a fallback virtual environment at ${VENV_DIR}"
    mkdir -p "$(dirname "${VENV_DIR}")"
    python3 -m venv --system-site-packages "${VENV_DIR}"
    "${VENV_PY}" -m pip install --upgrade pip
    "${VENV_PY}" -m pip install inky
fi

# ── 3. Install Pillow into the same environment ─────────────────────────────────
say "Installing Pillow into the environment"
"${VENV_PY}" -m pip install --upgrade Pillow

# ── 4. Install the per-minute cron job ──────────────────────────────────────────
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
