"""
Result Card Component
Presents parsed WiFi credentials, password reveal/copy controls, and connection triggers
"""
import webbrowser
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QGuiApplication
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ...config import THEME
from ...qr.parser import WiFiCredentials


class ResultCardWidget(QFrame):
    """
    Card displaying parsed WiFi credentials with manual Connect, Reveal Password,
    and Copy actions.
    """

    connect_requested = pyqtSignal(WiFiCredentials)
    scan_another_requested = pyqtSignal()
    status_message = pyqtSignal(str, str)  # msg, type ('info', 'success', 'error')

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("class", "card")
        self._current_creds: Optional[WiFiCredentials] = None
        self._current_raw_text = ""

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(16)

        # Stacked Widget: 0 = Standby / Instructions, 1 = WiFi Credentials, 2 = General Text / URL
        self.stack = QStackedWidget(self)
        main_layout.addWidget(self.stack)

        self._init_standby_page()
        self._init_wifi_page()
        self._init_generic_page()

        self.stack.setCurrentIndex(0)

    # -------------------------------------------------------------
    # Page 0: Standby Instructions
    # -------------------------------------------------------------
    def _init_standby_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon = QLabel("📶", page)
        icon.setFont(QFont(THEME["font_family"], 36))
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("Ready to Scan WiFi QR", page)
        title.setProperty("class", "heading")
        title.setFont(QFont(THEME["font_family"], 15, QFont.Weight.DemiBold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        desc = QLabel(
            "Point your camera at a QR code",
            page,
        )
        desc.setFont(QFont(THEME["font_family"], 11))
        desc.setStyleSheet(f"color: {THEME['text_secondary']}; line-height: 1.4;")
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(icon)
        layout.addWidget(title)
        layout.addWidget(desc)
        self.stack.addWidget(page)

    # -------------------------------------------------------------
    # Page 1: WiFi Credentials Found
    # -------------------------------------------------------------
    def _init_wifi_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        # Header Row
        header_layout = QHBoxLayout()
        icon = QLabel("📡", page)
        icon.setFont(QFont(THEME["font_family"], 16))

        title = QLabel("WiFi Network Found", page)
        title.setProperty("class", "heading")
        title.setFont(QFont(THEME["font_family"], 14, QFont.Weight.DemiBold))

        self.security_badge = QLabel("WPA2", page)
        self.security_badge.setProperty("class", "badge")

        header_layout.addWidget(icon)
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(self.security_badge)
        layout.addLayout(header_layout)

        # Network Details Grid
        grid = QGridLayout()
        grid.setSpacing(10)

        # SSID Field
        lbl_ssid = QLabel("Network Name (SSID):", page)
        lbl_ssid.setStyleSheet(f"color: {THEME['text_secondary']}; font-weight: 500;")
        self.txt_ssid = QLineEdit(page)
        self.txt_ssid.setReadOnly(True)
        self.txt_ssid.setFont(QFont(THEME["font_family"], 12, QFont.Weight.DemiBold))

        self.btn_copy_ssid = QPushButton("📋", page)
        self.btn_copy_ssid.setProperty("class", "iconBtn")
        self.btn_copy_ssid.setToolTip("Copy SSID")
        self.btn_copy_ssid.clicked.connect(self._on_copy_ssid)

        grid.addWidget(lbl_ssid, 0, 0, 1, 2)
        grid.addWidget(self.txt_ssid, 1, 0)
        grid.addWidget(self.btn_copy_ssid, 1, 1)

        # Password Field
        self.lbl_pass = QLabel("Password:", page)
        self.lbl_pass.setStyleSheet(f"color: {THEME['text_secondary']}; font-weight: 500;")
        self.txt_pass = QLineEdit(page)
        self.txt_pass.setReadOnly(True)
        self.txt_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_pass.setFont(QFont("Consolas", 12))

        self.btn_toggle_pass = QPushButton("👁️", page)
        self.btn_toggle_pass.setProperty("class", "iconBtn")
        self.btn_toggle_pass.setToolTip("Show / Hide Password")
        self.btn_toggle_pass.clicked.connect(self._on_toggle_password_visibility)

        self.btn_copy_pass = QPushButton("📋", page)
        self.btn_copy_pass.setProperty("class", "iconBtn")
        self.btn_copy_pass.setToolTip("Copy Password")
        self.btn_copy_pass.clicked.connect(self._on_copy_password)

        pass_btn_layout = QHBoxLayout()
        pass_btn_layout.setSpacing(6)
        pass_btn_layout.addWidget(self.btn_toggle_pass)
        pass_btn_layout.addWidget(self.btn_copy_pass)

        grid.addWidget(self.lbl_pass, 2, 0, 1, 2)
        grid.addWidget(self.txt_pass, 3, 0)
        grid.addLayout(pass_btn_layout, 3, 1)

        layout.addLayout(grid)

        # Action Buttons
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(8)

        self.btn_connect = QPushButton("⚡ Connect to WiFi", page)
        self.btn_connect.setProperty("class", "primaryBtn")
        self.btn_connect.setFont(QFont(THEME["font_family"], 13, QFont.Weight.DemiBold))
        self.btn_connect.clicked.connect(self._on_connect_clicked)

        self.btn_scan_another = QPushButton("🔄 Scan Another Code", page)
        self.btn_scan_another.setProperty("class", "secondaryBtn")
        self.btn_scan_another.clicked.connect(self._on_scan_another_clicked)

        btn_layout.addWidget(self.btn_connect)
        btn_layout.addWidget(self.btn_scan_another)
        layout.addLayout(btn_layout)

        self.stack.addWidget(page)

    # -------------------------------------------------------------
    # Page 2: Non-WiFi QR Payload
    # -------------------------------------------------------------
    def _init_generic_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        header_layout = QHBoxLayout()
        icon = QLabel("📝", page)
        icon.setFont(QFont(THEME["font_family"], 16))

        title = QLabel("QR Code Content", page)
        title.setProperty("class", "heading")
        title.setFont(QFont(THEME["font_family"], 14, QFont.Weight.DemiBold))

        header_layout.addWidget(icon)
        header_layout.addWidget(title)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        self.txt_generic = QLineEdit(page)
        self.txt_generic.setReadOnly(True)
        layout.addWidget(self.txt_generic)

        action_layout = QHBoxLayout()
        self.btn_copy_generic = QPushButton("📋 Copy Text", page)
        self.btn_copy_generic.setProperty("class", "secondaryBtn")
        self.btn_copy_generic.clicked.connect(self._on_copy_generic)

        self.btn_open_url = QPushButton("🌐 Open Link", page)
        self.btn_open_url.setProperty("class", "primaryBtn")
        self.btn_open_url.clicked.connect(self._on_open_url)

        action_layout.addWidget(self.btn_copy_generic)
        action_layout.addWidget(self.btn_open_url)
        layout.addLayout(action_layout)

        self.btn_scan_another_gen = QPushButton("🔄 Scan Another Code", page)
        self.btn_scan_another_gen.setProperty("class", "secondaryBtn")
        self.btn_scan_another_gen.clicked.connect(self._on_scan_another_clicked)
        layout.addWidget(self.btn_scan_another_gen)

        self.stack.addWidget(page)

    # -------------------------------------------------------------
    # Public Methods
    # -------------------------------------------------------------
    def display_wifi_credentials(self, creds: WiFiCredentials):
        self._current_creds = creds
        self.txt_ssid.setText(creds.ssid)
        self.txt_pass.setText(creds.password)
        self.security_badge.setText(creds.display_auth)

        # Show/Hide password field if network is open
        if not creds.requires_password:
            self.lbl_pass.setVisible(False)
            self.txt_pass.setVisible(False)
            self.btn_toggle_pass.setVisible(False)
            self.btn_copy_pass.setVisible(False)
        else:
            self.lbl_pass.setVisible(True)
            self.txt_pass.setVisible(True)
            self.btn_toggle_pass.setVisible(True)
            self.btn_copy_pass.setVisible(True)
            self.txt_pass.setEchoMode(QLineEdit.EchoMode.Password)
            self.btn_toggle_pass.setText("👁️")

        self.btn_connect.setEnabled(True)
        self.btn_connect.setText("⚡ Connect to WiFi")
        self.stack.setCurrentIndex(1)

    def display_generic_payload(self, text: str):
        self._current_raw_text = text
        self.txt_generic.setText(text)
        is_url = text.startswith("http://") or text.startswith("https://")
        self.btn_open_url.setVisible(is_url)
        self.stack.setCurrentIndex(2)

    def reset_to_standby(self):
        self._current_creds = None
        self._current_raw_text = ""
        self.stack.setCurrentIndex(0)

    def set_connecting_state(self, connecting: bool, status_text: str = "Connecting..."):
        if connecting:
            self.btn_connect.setEnabled(False)
            self.btn_connect.setText(f"⏳ {status_text}")
        else:
            self.btn_connect.setEnabled(True)
            self.btn_connect.setText("⚡ Connect to WiFi")

    # -------------------------------------------------------------
    # Event Handlers
    # -------------------------------------------------------------
    def _on_toggle_password_visibility(self):
        if self.txt_pass.echoMode() == QLineEdit.EchoMode.Password:
            self.txt_pass.setEchoMode(QLineEdit.EchoMode.Normal)
            self.btn_toggle_pass.setText("🙈")
        else:
            self.txt_pass.setEchoMode(QLineEdit.EchoMode.Password)
            self.btn_toggle_pass.setText("👁️")

    def _on_copy_ssid(self):
        if self._current_creds:
            clipboard = QGuiApplication.clipboard()
            clipboard.setText(self._current_creds.ssid)
            self.status_message.emit(f"Copied SSID '{self._current_creds.ssid}' to clipboard!", "success")

    def _on_copy_password(self):
        if self._current_creds and self._current_creds.password:
            clipboard = QGuiApplication.clipboard()
            clipboard.setText(self._current_creds.password)
            self.status_message.emit("WiFi password copied to clipboard!", "success")

    def _on_copy_generic(self):
        if self._current_raw_text:
            clipboard = QGuiApplication.clipboard()
            clipboard.setText(self._current_raw_text)
            self.status_message.emit("Content copied to clipboard!", "success")

    def _on_open_url(self):
        if self._current_raw_text:
            webbrowser.open(self._current_raw_text)

    def _on_connect_clicked(self):
        if self._current_creds:
            self.connect_requested.emit(self._current_creds)

    def _on_scan_another_clicked(self):
        self.reset_to_standby()
        self.scan_another_requested.emit()
