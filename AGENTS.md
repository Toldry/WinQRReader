# AGENTS.md - Architecture & Developer Reference

This document details the internal architecture, design decisions, threading models, and extension points of the **WinQRReader** project for developer and agentic maintenance.

---

## 1. System Architecture

WinQRReader is architected as an asynchronous, event-driven desktop application combining high-performance optical computer vision with native WiFi subsystem controls on Windows 11 (`netsh wlan`) and Ubuntu / Linux (NetworkManager `nmcli`). Platform-specific code is confined to `src/wifi/` (backend chosen by `create_wifi_manager()`) and `camera_backends()` in `src/camera/capture_thread.py`.

```
+-------------------------------------------------------------------------------+
|                               PyQt6 Main Thread                               |
|  +------------------------+  +------------------------+  +-----------------+  |
|  |    CameraViewWidget    |  |    ResultCardWidget    |  | StatusBanner    |  |
|  |  - QPainter Viewport   |  |  - Credential Card     |  | - Notification  |  |
|  |  - Reticle & HUD       |  |  - Password Reveal     |  | - Progress      |  |
|  |  - Tracked Polygon     |  |  - Action Buttons      |  |                 |  |
|  +------------------------+  +------------------------+  +-----------------+  |
+-------------------------------------------------------------------------------+
           ▲                                  ▲                       ▲
           | pyqtSignal(frame, detection)     | pyqtSignal(creds)     | pyqtSignal(msg)
           |                                  |                       |
+-------------------------+      +-------------------------+  +-----------------+
|   CameraCaptureThread   |      |   WiFiConnectWorker     |  | Windows/LinuxMgr|
| - DSHOW/MSMF or V4L2    |      | - Background QThread    |  | - netsh + XML   |
| - SuperReliableDetector |      | - Non-blocking netsh/nm |  | - or nmcli      |
|   * zxing-cpp           |      | - Status Poller         |  | - Interface Chk |
|   * CLAHE / Zoom 2x     |      +-------------------------+  +-----------------+
|   * OpenCV Fallback     |
+-------------------------+
```

---

## 2. Component Directory Breakdown

```
WinQRReader/
├── .github/
│   └── workflows/
│       └── release.yml       # GitHub Actions automated test, build, and release pipeline
├── assets/
│   ├── logo.png              # Application logo icon
│   ├── logo.ico              # Multi-resolution Windows executable icon
│   └── screenshot.png        # Application UI screenshot
├── src/
│   ├── config.py             # Global constants, paths, Fluent UI palette
│   ├── logger.py             # Unified rotating file logger, exception hooks, Qt handler, & diagnostics
│   ├── qr/
│   │   ├── detector.py       # SuperReliableQRDetector (zxing-cpp + multi-stage optical enhancement)
│   │   └── parser.py         # WiFi MeCard format parser & unescaper
│   ├── camera/
│   │   └── capture_thread.py # DirectShow / MSMF / V4L2 QThread camera pipeline & discovery worker
│   ├── wifi/
│   │   ├── manager.py        # Windows WiFi connection runner, ConnectionResult, create_wifi_manager()
│   │   ├── linux_manager.py  # Linux NetworkManager (nmcli) connection runner & interface monitor
│   │   └── profile_builder.py# Windows WLANProfile XML schema generator
│   └── ui/
│       ├── main_window.py    # Main window orchestrator & thread manager
│       ├── styles.py         # Windows 11 Fluent dark theme QSS
│       └── components/
│           ├── camera_view.py# High-DPI QPainter camera viewfinder with HUD & recovery
│           ├── result_card.py# Interactive credential card with copy/reveal actions
│           └── status_banner.py # Toast / banner notification widget
├── tests/
│   ├── test_camera_activation.py # Manual camera activation & session lifecycle tests
│   ├── test_detector.py      # QR detection accuracy & synthetic noise tests
│   ├── test_linux_wifi.py    # nmcli backend tests (mocked subprocess, runs on any OS)
│   ├── test_logger.py        # Logging setup, file creation, & exception hook tests
│   ├── test_parser.py        # WiFi schema & escape character parsing tests
│   ├── test_real_images.py   # Real-world webcam photo test suite
│   ├── test_wifi_profile.py  # WLAN XML validity & encryption schema tests
│   └── test_window_opacity.py # Main window renders fully opaque (Wayland smearing regression)
├── build_exe.py              # PyInstaller bundle script with bytecode optimization (-O2)
├── package_release.py        # Packs dist/WinQRReader into the release .zip (Windows) / .tar.gz (Linux)
├── pyproject.toml            # uv project: runtime deps + `dev` group (pytest, qrcode, pyinstaller)
├── uv.lock                   # Locked, cross-platform dependency pins (commit after `uv lock`)
├── run.bat                   # Zero-config Windows launcher (`uv run --no-dev main.py`)
├── run.py                    # Zero-config Linux launcher, stdlib only (`uv run --no-dev main.py` + system checks)
└── main.py                   # App bootstrap, single-instance IPC, DPI setup
```

---

## 3. QR Detection Pipeline (`src/qr/detector.py`)

Laptop webcams scanning smartphone screens present specific optical challenges:
1. Fixed-focus or soft-focus optics
2. Intense specular glare from phone glass
3. Screen refresh scanlines / moiré patterns
4. Dark-mode inverted QR patterns
5. Perspective distortion from holding angles

To guarantee super-reliable recognition with zero external model weight dependencies, `SuperReliableQRDetector` executes a multi-tiered pipeline:

| Tier | Engine / Transformation | Purpose |
| :--- | :--- | :--- |
| **1** | **zxing-cpp (Native Pass)** | Primary engine. High-speed C++ engine providing sub-millisecond barcode decoding. |
| **2** | **CLAHE Adaptive Histogram** | Normalizes extreme glare hot-spots and low contrast on screen glass. |
| **3** | **Polarity Inversion** | Decodes dark-mode / white-on-black QR codes. |
| **4** | **Center Multi-Scale Crop & 2x Upsampling** | Digital zoom targeting the center 75%, 60%, and 50% with cubic upscaling for distant phone holds. |
| **5** | **OpenCV Standard QRCodeDetector** | Secondary fallback pass. |

---

## 4. WiFi Schema & Profile Generation

### WiFi QR Schema (`src/qr/parser.py`)
Parses `WIFI:T:<auth>;S:<ssid>;P:<password>;H:<hidden>;;` with full support for:
- Escaped characters: `\;`, `\:`, `\,`, `\\`
- Varied key orders (e.g., `S` preceding `T`)
- Auth types: `WPA` / `WPA2` (AES), `WPA3` / `SAE`, `WEP`, `nopass` / `open`

### Windows Native WLAN Profile Schema (`src/wifi/profile_builder.py`)
Generates Microsoft WLANProfile Schema `v1` XML:
- Converts SSIDs to uppercase hexadecimal strings (`<hex>...</hex>`) for robust non-ASCII / special-character support.
- Configures `<authEncryption>` and `<sharedKey>` according to the security type (`WPA2PSK`/`AES`, `WPA3SAE`/`AES`, `open`/`none`, `open`/`WEP`).
- Flags `<nonBroadcast>` when `is_hidden` is true.

### Linux NetworkManager Backend (`src/wifi/linux_manager.py`)
`LinuxWiFiManager` exposes the same interface as `WindowsWiFiManager` (`get_current_connection`, `connect_network`, `delete_profile`):
- Picks the first managed `wifi` device from `nmcli -t -f DEVICE,TYPE,STATE device`.
- Replaces any existing connection with the same name, then runs `nmcli connection add type wifi ...` with `wifi-sec.key-mgmt` `wpa-psk` (WPA/WPA2), `sae` (WPA3), `none` + `wep-key0` (WEP), or no security block (open); sets `wifi.hidden` for hidden networks.
- Activates with `nmcli --wait <timeout> connection up id <ssid>`, which blocks until success or failure, and maps nmcli errors to friendly messages.
- Runs nmcli with `LC_ALL=C` so error strings are matchable; parses terse (`-t`) output with `split_terse_fields`, which unescapes `\:` and `\\`.
- Requires `opencv-python-headless` on Linux: the GUI `opencv-python` wheel bundles Qt plugins that clash with PyQt6.
- `main.py` sets `desktopFileName("winqrreader")` (the Wayland app ID) so the dock matches the window to `winqrreader.desktop`; on X11 the window class is `WinQRReader`. The README documents the desktop entry.
- Top-level windows must paint an opaque background: Wayland surfaces have an alpha channel, so a see-through window smears when dragged. In `styles.py`, keep the `QMainWindow` rule after the global `QWidget { background: transparent }` rule (equal QSS specificity, last wins); `tests/test_window_opacity.py` guards this.

---

## 5. Threading & Concurrency Model

1. **GUI Thread (PyQt6)**:
   - Manages UI events, animations (reticle sweeps), and rendering.
   - Never blocks on camera I/O or WiFi subprocess commands.
2. **CameraCaptureThread & CameraDiscoveryWorker (`QThread`)**:
   - Captures frames from webcam using DirectShow / MSMF (Windows) or V4L2 with MJPG (Linux), with multi-backend fallback.
   - Discovers available webcam hardware asynchronously without delaying initial window display.
   - Streams live feed at 30 FPS. Emits `frame_ready(frame, detection)` and `qr_detected(detection)`.
   - Supports `pause_detection()` and `resume_detection()` with buffer flushing.
3. **WiFiConnectWorker (`QThread`)**:
   - Executes profile registration and `netsh wlan connect` (Windows) or `nmcli connection up` (Linux) asynchronously.
   - Windows polls interface state every 1.0s up to a configurable timeout (default 15s); nmcli waits up to the same timeout itself.
   - Emits `progress(str)` and `finished(ConnectionResult)`.

---

## 6. Extension Points

- **OCR Fallback**: If a printed WiFi card has plain text SSID & Password instead of a QR code, an OCR detector (e.g., Tesseract / Windows.Media.Ocr) can be integrated as an additional detection tier.
- **Enterprise 802.1X Profiles**: Expand `src/wifi/profile_builder.py` to support EAP-TLS / PEAP enterprise networks.
- **System Tray Mode**: Add `QSystemTrayIcon` to `MainWindow` for background quick-scanning directly from the Windows taskbar.

---

## 7. CI/CD & Automated GitHub Releases

Automated build and release pipeline configured in `.github/workflows/release.yml`:
- **Scripting**: write helper and CI scripts in Python (stdlib only where they must run before uv), not shell.
- **Dependency management**: uv only. Never add a `requirements.txt`; use `uv add` / `uv add --dev` and commit `uv.lock`.
- **Trigger**: Pushing a version tag matching `v*` (e.g., `git tag v1.0.0` and `git push origin v1.0.0`).
- **Runners**: `windows-latest` and `ubuntu-22.04` (oldest supported glibc, so Linux binaries also run on newer Ubuntu releases).
- **Pipeline Stages**:
  1. Installs uv (`astral-sh/setup-uv`) and the locked dependencies with `uv sync --locked`.
  2. Runs the pytest suite (parser, detector, camera activation, WLAN profile, nmcli backend) with `QT_QPA_PLATFORM=offscreen`.
  3. Executes `python build_exe.py` with bytecode optimization (`--optimize=2`).
  4. `package_release.py` packages the compiled distribution into `WinQRReader-<tag>-windows-x64.zip` and `WinQRReader-<tag>-linux-x64.tar.gz`.
  5. On tag pushes only, a final job publishes a GitHub Release with auto-generated changelog and both archives attached.
