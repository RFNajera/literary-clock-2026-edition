#!/usr/bin/env bash
# Install the Literary Clock on a Raspberry Pi driving a Pimoroni Inky wHAT.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "==> Installing Python dependencies"
pip3 install --upgrade Pillow inky

echo "==> Installing systemd service + timer"
# Rewrite the WorkingDirectory/ExecStart paths to match this clone location.
sudo sed "s#/home/pi/literary-clock-2026-edition#${REPO_DIR}#g" \
    "${REPO_DIR}/scripts/literary-clock.service" \
    | sudo tee /etc/systemd/system/literary-clock.service >/dev/null
sudo cp "${REPO_DIR}/scripts/literary-clock.timer" /etc/systemd/system/literary-clock.timer

echo "==> Enabling timer"
sudo systemctl daemon-reload
sudo systemctl enable --now literary-clock.timer

echo
echo "Done. The clock will refresh every minute."
echo "Test a single update now with:"
echo "    python3 ${REPO_DIR}/scripts/update_display.py"
echo "Preview a frame without the panel:"
echo "    python3 ${REPO_DIR}/scripts/update_display.py --preview frame.png"
