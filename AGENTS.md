# AGENTS.md - Architecture & Developer Reference

This document details the internal architecture, design decisions, threading models, and extension points of the **WinQRReader** project for developer and agentic maintenance.

---

## 1. System Architecture

WinQRReader is architected as an asynchronous, event-driven desktop application combining high-performance optical computer vision with Windows 11 Native WLAN subsystem controls.

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
|   CameraCaptureThread   |      |   WiFiConnectWorker     |  | WindowsWiFiMgr  |
| - OpenCV DirectShow/MSMF|      | - Background QThread    |  | - XML Generator |
| - SuperReliableDetector |      | - Non-blocking netsh    |  | - netsh wlan    |
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
│   ├── qr/
│   │   ├── detector.py       # SuperReliableQRDetector (zxing-cpp + multi-stage optical enhancement)
│   │   └── parser.py         # WiFi MeCard format parser & unescaper
│   ├── camera/
│   │   └── capture_thread.py # DirectShow / MSMF QThread camera pipeline & discovery worker
│   ├── wifi/
│   │   ├── manager.py        # Windows WiFi connection runner & interface monitor
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
│   ├── test_parser.py        # WiFi schema & escape character parsing tests
│   ├── test_real_images.py   # Real-world webcam photo test suite
│   └── test_wifi_profile.py  # WLAN XML validity & encryption schema tests
├── build_exe.py              # PyInstaller bundle script with bytecode optimization (-O2)
├── run.bat                   # Zero-config Windows execution launcher
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

---

## 5. Threading & Concurrency Model

1. **GUI Thread (PyQt6)**:
   - Manages UI events, animations (reticle sweeps), and rendering.
   - Never blocks on camera I/O or WiFi subprocess commands.
2. **CameraCaptureThread & CameraDiscoveryWorker (`QThread`)**:
   - Captures frames from webcam using DirectShow / MSMF with multi-backend fallback.
   - Discovers available webcam hardware asynchronously without delaying initial window display.
   - Streams live feed at 30 FPS. Emits `frame_ready(frame, detection)` and `qr_detected(detection)`.
   - Supports `pause_detection()` and `resume_detection()` with buffer flushing.
3. **WiFiConnectWorker (`QThread`)**:
   - Executes profile registration and `netsh wlan connect` asynchronously.
   - Polls interface state every 1.0s up to a configurable timeout (default 15s).
   - Emits `progress(str)` and `finished(ConnectionResult)`.

---

## 6. Extension Points

- **OCR Fallback**: If a printed WiFi card has plain text SSID & Password instead of a QR code, an OCR detector (e.g., Tesseract / Windows.Media.Ocr) can be integrated as an additional detection tier.
- **Enterprise 802.1X Profiles**: Expand `src/wifi/profile_builder.py` to support EAP-TLS / PEAP enterprise networks.
- **System Tray Mode**: Add `QSystemTrayIcon` to `MainWindow` for background quick-scanning directly from the Windows taskbar.

---

## 7. CI/CD & Automated GitHub Releases

Automated build and release pipeline configured in `.github/workflows/release.yml`:
- **Trigger**: Pushing a version tag matching `v*` (e.g., `git tag v1.0.0` and `git push origin v1.0.0`).
- **Runner**: `windows-latest`.
- **Pipeline Stages**:
  1. Installs dependencies from `requirements.txt`.
  2. Runs 26 unit tests across parser, detector, camera activation, and WLAN profile generation.
  3. Executes `python build_exe.py` with bytecode optimization (`--optimize=2`).
  4. Packages the compiled distribution into `WinQRReader-<tag>-windows-x64.zip`.
  5. Publishes a GitHub Release with auto-generated changelog and attached `.zip` asset.
