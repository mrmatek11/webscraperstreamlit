#!/bin/bash
set -e
echo "[setup.sh] Installing Playwright Chromium browser..."
python -m playwright install chromium
python -m playwright install-deps chromium
echo "[setup.sh] Done."
