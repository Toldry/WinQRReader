#!/usr/bin/env bash
# WinQRReader - zero-config Linux (Ubuntu) launcher
# uv creates the .venv and installs the locked dependencies on first run.
set -u
cd "$(dirname "$0")"

echo "======================================================="
echo "        WinQRReader - WiFi QR Scanner (Linux)"
echo "======================================================="
echo

if ! command -v uv >/dev/null 2>&1; then
    echo "[ERROR] uv not found. Install it with:"
    echo "        curl -LsSf https://astral.sh/uv/install.sh | sh"
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

echo "Starting WinQRReader..."
exec uv run --locked --no-dev main.py "$@"
