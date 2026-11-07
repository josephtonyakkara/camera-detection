#!/usr/bin/env bash
# One-time machine setup for Linux / Raspberry Pi OS: venv + pinned deps.
set -euo pipefail
cd "$(dirname "$0")/.."

PYTHON="${PYTHON:-python3}"

if ! command -v "$PYTHON" >/dev/null 2>&1; then
    echo "ERROR: $PYTHON not found. Install with: sudo apt install python3" >&2
    exit 1
fi

if ! "$PYTHON" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)'; then
    echo "ERROR: Python >= 3.11 required, found $("$PYTHON" -V 2>&1)." >&2
    echo "Set PYTHON=python3.11 (or newer) and re-run." >&2
    exit 1
fi

if [ ! -d .venv ]; then
    if ! "$PYTHON" -m venv .venv; then
        echo "ERROR: venv creation failed. On Debian/Pi: sudo apt install python3-venv" >&2
        exit 1
    fi
fi

.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.lock

mkdir -p config/local logs

# opencv needs system GL/X11 libs on minimal Debian installs
if ! .venv/bin/python -c 'import cv2' 2>/dev/null; then
    echo "ERROR: OpenCV import failed. On Debian/Pi try: sudo apt install libgl1 libglib2.0-0" >&2
    exit 1
fi
.venv/bin/python -c 'import numpy, fastapi, asyncua, yaml'

echo
echo "Setup complete."
echo "  Run:          .venv/bin/python main.py"
echo "  Tests:        .venv/bin/python -m pytest -m 'not hardware'"
echo "  Camera probe: .venv/bin/python scripts/camera_check.py --list"
echo
echo "Per-machine settings go in config/local/<name>.yaml (gitignored);"
echo "see docs_camera/DEPLOYMENT.md."
