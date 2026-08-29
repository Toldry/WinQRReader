"""
Main Application Window for WinQRReader
Integrates Camera View, QR Detection Pipeline, Fluent Styling, and WiFi Connection Engine
"""
import logging
from typing import Optional

from PyQt6.QtCore import QObject, QThread, Qt, pyqtSignal
from PyQt6.QtGui import QFont, QIcon, QPixmap
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from ..camera.capture_thread import CameraCaptureThread, CameraDiscoveryWorker
from ..config import DEFAULT_CAMERA_INDEX, LOGO_PATH, THEME
from ..qr.detector import DetectionResult, SuperReliableQRDetector
from ..qr.parser import WiFiCredentials, is_wifi_qr, parse_wifi_qr
from ..wifi.manager import ConnectionResult, WindowsWiFiManager
from .components.camera_view import CameraViewWidget
from .components.result_card import ResultCardWidget
from .components.status_banner import StatusBannerWidget
from .styles import FLUENT_DARK_STYLESHEET

logger = logging.getLogger(__name__)


class WiFiConnectWorker(QThread):
    """Background worker for non-blocking WiFi connection on Windows."""

    progress = pyqtSignal(str)
    finished = pyqtSignal(object)  # ConnectionResult

    def __init__(self, wifi_manager: WindowsWiFiManager, creds: WiFiCredentials):
        super().__init__()
        self.wifi_manager = wifi_manager
        self.creds = creds

    def run(self):
        result = self.wifi_manager.connect_network(
            ssid=self.creds.ssid,
            password=self.creds.password,
            auth_type=self.creds.auth_type,
            is_hidden=self.creds.is_hidden,
            status_callback=lambda msg: self.progress.emit(msg),
        )
        self.finished.emit(result)


class MainWindow(QMainWindow):
    """Main Application Window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("WinQRReader")
        self.resize(1060, 680)
        self.setMinimumSize(850, 540)
        self.setStyleSheet(FLUENT_DARK_STYLESHEET)

        if LOGO_PATH.exists():
            self.setWindowIcon(QIcon(str(LOGO_PATH)))

        # Core Engines
        self.detector = SuperReliableQRDetector()
        self.wifi_manager = WindowsWiFiManager()
        self.camera_thread: Optional[CameraCaptureThread] = None
        self.discovery_worker: Optional[CameraDiscoveryWorker] = None
        self.connect_worker: Optional[WiFiConnectWorker] = None

        self._init_ui()

        # Connect camera view signals
        self.camera_view.activate_camera_requested.connect(self._on_activate_camera)
        self.camera_view.retry_camera_requested.connect(self._on_retry_camera)

        # Defer non-critical hardware queries so UI renders instantly (<150ms)
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(100, self._check_initial_wifi_state)
        QTimer.singleShot(200, self._refresh_cameras_async)

    def _init_ui(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Header Bar
        header_bar = self._create_header_bar()
        root_layout.addWidget(header_bar)

        # Main Content Layout
        content_container = QWidget(self)
        content_layout = QHBoxLayout(content_container)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(20)

        # Left: Camera Viewport Frame
        camera_frame = QFrame(self)
        camera_frame.setProperty("class", "cameraFrame")
        cam_frame_layout = QVBoxLayout(camera_frame)
        cam_frame_layout.setContentsMargins(0, 0, 0, 0)

        self.camera_view = CameraViewWidget(camera_frame)
        cam_frame_layout.addWidget(self.camera_view)

        # Right: Control and Result Panel
        right_panel = QWidget(self)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(14)

        # Status Banner
        self.status_banner = StatusBannerWidget(right_panel)
        right_layout.addWidget(self.status_banner)

        # Result Card
        self.result_card = ResultCardWidget(right_panel)
        self.result_card.connect_requested.connect(self._on_connect_wifi_requested)
        self.result_card.scan_another_requested.connect(self._on_resume_scanning_requested)
        self.result_card.status_message.connect(self._on_status_message)
        right_layout.addWidget(self.result_card, 1)

        # Footer Quick Status Bar
        footer = self._create_footer_status()
        right_layout.addWidget(footer)

        content_layout.addWidget(camera_frame, 3)
        content_layout.addWidget(right_panel, 2)

        root_layout.addWidget(content_container, 1)

    def _create_header_bar(self) -> QWidget:
        header = QFrame(self)
        header.setObjectName("headerBar")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(20, 12, 20, 12)
        layout.setSpacing(16)

        # Logo and Title
        title_row = QHBoxLayout()
        title_row.setSpacing(10)

        logo_label = QLabel(header)
        if LOGO_PATH.exists():
            pix = QPixmap(str(LOGO_PATH)).scaled(
                26, 26, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            )
            logo_label.setPixmap(pix)
        else:
            logo_label.setText("⚡")
            logo_label.setFont(QFont(THEME["font_family"], 16))

        title_lbl = QLabel("WinQRReader", header)
        title_lbl.setObjectName("appTitle")

        title_row.addWidget(logo_label)
        title_row.addWidget(title_lbl)
        title_row.addStretch()

        layout.addLayout(title_row, 1)

        # Camera Selector
        cam_selector_layout = QHBoxLayout()
        cam_selector_layout.setSpacing(8)

        cam_lbl = QLabel("Camera:", header)
        cam_lbl.setStyleSheet(f"color: {THEME['text_secondary']}; font-weight: 500;")

        self.cam_combo = QComboBox(header)
        self.cam_combo.addItem("Default Camera (0)", 0)
        self.cam_combo.currentIndexChanged.connect(self._on_camera_changed)

        self.btn_refresh_cam = QPushButton("🔄", header)
        self.btn_refresh_cam.setProperty("class", "iconBtn")
        self.btn_refresh_cam.setToolTip("Refresh Camera Devices")
        self.btn_refresh_cam.clicked.connect(self._refresh_cameras_async)

        cam_selector_layout.addWidget(cam_lbl)
        cam_selector_layout.addWidget(self.cam_combo)
        cam_selector_layout.addWidget(self.btn_refresh_cam)
        layout.addLayout(cam_selector_layout)

        return header

    def _create_footer_status(self) -> QWidget:
        footer = QFrame(self)
        layout = QHBoxLayout(footer)
        layout.setContentsMargins(8, 4, 8, 4)

        self.lbl_wifi_state = QLabel("⚪ Checking WiFi status...", footer)
        self.lbl_wifi_state.setFont(QFont(THEME["font_family"], 11))
        self.lbl_wifi_state.setStyleSheet(f"color: {THEME['text_secondary']};")

        layout.addWidget(self.lbl_wifi_state)
        layout.addStretch()
        return footer

    def _check_initial_wifi_state(self):
        """Asynchronously check current connection on startup without blocking window render."""
        try:
            connected, ssid = self.wifi_manager.get_current_connection()
            if connected:
                self.lbl_wifi_state.setText(f"🟢 Connected to: {ssid}")
            else:
                self.lbl_wifi_state.setText("⚪ WiFi: Not connected")
        except Exception:
            self.lbl_wifi_state.setText("⚪ WiFi: Ready")

    def _refresh_cameras_async(self):
        """Non-blocking camera discovery in background."""
        self.btn_refresh_cam.setEnabled(False)
        self.discovery_worker = CameraDiscoveryWorker(max_tested=4)
        self.discovery_worker.cameras_discovered.connect(self._on_cameras_discovered)
        self.discovery_worker.start()

    def _on_cameras_discovered(self, available_indices: list):
        self.btn_refresh_cam.setEnabled(True)
        curr_selected = self.cam_combo.currentData()
        if curr_selected is None:
            curr_selected = 0

        self.cam_combo.blockSignals(True)
        self.cam_combo.clear()
        for idx in available_indices:
            name = f"Webcam {idx}" if idx > 0 else "Default Camera (0)"
            self.cam_combo.addItem(name, idx)

        # Restore previous selection if still available
        found_idx = self.cam_combo.findData(curr_selected)
        if found_idx >= 0:
            self.cam_combo.setCurrentIndex(found_idx)
        self.cam_combo.blockSignals(False)

    def _init_camera(self):
        """Instantiate and launch camera capture thread."""
        if self.camera_thread is not None and self.camera_thread.isRunning():
            return

        curr_idx = self.cam_combo.currentData()
        if curr_idx is None:
            curr_idx = DEFAULT_CAMERA_INDEX

        self.camera_thread = CameraCaptureThread(camera_index=curr_idx, detector=self.detector)
        self.camera_thread.frame_ready.connect(self.camera_view.update_frame)
        self.camera_thread.qr_detected.connect(self._on_qr_code_detected)
        self.camera_thread.error_occurred.connect(self._on_camera_error)
        self.camera_thread.start()

    def _on_activate_camera(self):
        """Handler when user clicks Activate Camera button."""
        self.status_banner.show_info("Starting camera...", 2000)
        self._init_camera()

    def _on_retry_camera(self):
        """Handler when user clicks Retry Camera button."""
        self.status_banner.show_info("Retrying camera...", 2000)
        if self.camera_thread:
            self.camera_thread.retry_camera()
        else:
            self._init_camera()

    def bring_to_foreground(self):
        """Bring application window to top if another instance is launched."""
        self.setWindowState(self.windowState() & ~Qt.WindowState.WindowMinimized | Qt.WindowState.WindowActive)
        self.showNormal()
        self.raise_()
        self.activateWindow()
        self.status_banner.show_info("WinQRReader is already running and active.", 4000)

    def _on_camera_changed(self, index: int):
        cam_id = self.cam_combo.currentData()
        if cam_id is not None and self.camera_thread is not None and self.camera_thread.isRunning():
            self.camera_thread.set_camera_index(cam_id)
            self.status_banner.show_info(f"Switched to Camera {cam_id}", 3000)

    def _on_qr_code_detected(self, detection: DetectionResult):
        """Called when a valid QR code is recognized by the detector."""
        raw_text = detection.text
        logger.info(f"QR Code Recognized via {detection.engine}: {raw_text}")

        # Pause camera capture according to manual action workflow
        if self.camera_thread:
            self.camera_thread.pause_detection()
        self.camera_view.set_paused(True, "QR Code Recognized")

        if is_wifi_qr(raw_text):
            creds = parse_wifi_qr(raw_text)
            if creds:
                self.result_card.display_wifi_credentials(creds)
                self.status_banner.show_success(f"WiFi QR code found: '{creds.ssid}'")
            else:
                self.result_card.display_generic_payload(raw_text)
        else:
            self.result_card.display_generic_payload(raw_text)
            self.status_banner.show_info("Scanned QR code content")

    def _on_resume_scanning_requested(self):
        """Resume active camera stream and scanning HUD."""
        self.camera_view.set_paused(False)
        if self.camera_thread:
            self.camera_thread.resume_detection()
        self.status_banner.hide_banner()

    def _on_connect_wifi_requested(self, creds: WiFiCredentials):
        """Connect to WiFi using Windows Native WLAN in background worker."""
        self.result_card.set_connecting_state(True, "Connecting...")
        self.status_banner.show_info(f"Connecting to '{creds.ssid}'...")

        self.connect_worker = WiFiConnectWorker(self.wifi_manager, creds)
        self.connect_worker.progress.connect(lambda msg: self.status_banner.show_info(msg, 0))
        self.connect_worker.finished.connect(self._on_wifi_connect_finished)
        self.connect_worker.start()

    def _on_wifi_connect_finished(self, result: ConnectionResult):
        self.result_card.set_connecting_state(False)
        if result.success:
            self.status_banner.show_success(result.message, 10000)
            self.lbl_wifi_state.setText(f"🟢 Connected to: {result.ssid}")
        else:
            self.status_banner.show_error(result.message, 10000)

    def _on_status_message(self, message: str, msg_type: str):
        if msg_type == "success":
            self.status_banner.show_success(message)
        elif msg_type == "error":
            self.status_banner.show_error(message)
        else:
            self.status_banner.show_info(message)

    def _on_camera_error(self, err_msg: str):
        self.status_banner.show_error(err_msg, 0)
        self.camera_view.set_error(err_msg)

    def closeEvent(self, event):
        """Clean up background threads on exit."""
        if self.camera_thread and self.camera_thread.isRunning():
            self.camera_thread.stop()
        if self.connect_worker and self.connect_worker.isRunning():
            self.connect_worker.wait(1000)
        event.accept()
