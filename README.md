# WinQRReader

Desktop application for QR code scanning and automatic WiFi profile provisioning on Windows and Ubuntu.

<p align="center">
  <img src="assets/screenshot.png" alt="WinQRReader Screenshot" width="800">
</p>

## Requirements

- **OS**: Windows 10 / 11 (x64), or Ubuntu 22.04+ (x64) with NetworkManager
- **Python**: 3.10+
- **Hardware**: Integrated or USB webcam, 802.11 WLAN adapter

| | Windows | Ubuntu / Linux |
| :--- | :--- | :--- |
| WiFi backend | `netsh wlan` + WLANProfile XML | NetworkManager (`nmcli`) |
| Camera backend | DirectShow → Media Foundation | V4L2 |
| Launcher | `run.bat` | `run.sh` |
| Logs (standalone build) | `%LOCALAPPDATA%\WinQRReader\logs` | `~/.local/state/WinQRReader/logs` |

## Installation & Execution

### Windows

Run from source:
```powershell
pip install -r requirements.txt
python main.py
```

Or double-click `run.bat`.

### Ubuntu

Install the system packages (Ubuntu Desktop already ships NetworkManager):
```bash
sudo apt install python3-venv libxcb-cursor0 network-manager
```

Then launch with the helper script, which creates a `.venv` on first run
(Ubuntu 23.04+ refuses system-wide `pip install`, see PEP 668):
```bash
./run.sh
```

Or manually:
```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python main.py
```

Your user needs access to the webcam (`/dev/video*`) and permission to manage
NetworkManager connections. Both are granted by default to the logged-in user of
an Ubuntu Desktop session; over SSH or on minimal installs, add the user to the
`video` group and/or check the PolicyKit rules.

### Build Standalone Executable
```bash
python build_exe.py
```
Output artifact: `dist/WinQRReader/WinQRReader.exe` (Windows) or `dist/WinQRReader/WinQRReader` (Linux).

## Architecture

For architecture specifications, component breakdowns, and threading models, refer to [AGENTS.md](AGENTS.md).

## Testing

Run unit and integration test suite:
```bash
python -m pytest tests -v
```

On a headless Linux machine, set `QT_QPA_PLATFORM=offscreen` first:
```bash
QT_QPA_PLATFORM=offscreen python -m pytest tests -v
```
