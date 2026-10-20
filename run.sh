#!/usr/bin/env bash
# WinQRReader - zero-config Linux (Ubuntu) launcher
# Creates a local virtual environment on first run, since Ubuntu 23.04+ forbids
# installing pip packages into the system Python (PEP 668).
set -u
cd "$(dirname "$0")"

echo "======================================================="
echo "        WinQRReader - WiFi QR Scanner (Linux)"
echo "======================================================="
echo

if ! command -v python3 >/dev/null 2>&1; then
    echo "[ERROR] python3 not found. Install it with: sudo apt install python3 python3-venv"
    exit 1
fi

if ! command -v nmcli >/dev/null 2>&1; then
    echo "[WARNING] nmcli not found. WiFi connections need NetworkManager:"
    echo "          sudo apt install network-manager"
fi

# Qt 6.5+ needs libxcb-cursor0 for its X11 (xcb) platform plugin
if ! ldconfig -p 2>/dev/null | grep -q "libxcb-cursor.so.0"; then
    echo "[WARNING] libxcb-cursor0 not found. The window may fail to open on X11:"
    echo "          sudo apt install libxcb-cursor0"
fi

VENV_DIR=".venv"
if [ ! -x "$VENV_DIR/bin/python" ]; then
    echo "Creating virtual environment in $VENV_DIR..."
    if ! python3 -m venv "$VENV_DIR"; then
        echo "[ERROR] Could not create virtual environment. Install it with: sudo apt install python3-venv"
        exit 1
    fi
fi

echo "Checking dependencies..."
if ! "$VENV_DIR/bin/python" -m pip install -r requirements.txt --quiet; then
    echo "[WARNING] Dependency check encountered an issue. Attempting to start app anyway..."
fi

echo "Starting WinQRReader..."
exec "$VENV_DIR/bin/python" main.py "$@"
