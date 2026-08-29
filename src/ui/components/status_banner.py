"""
Status and Notification Banner Component
"""
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton

from ...config import THEME


class StatusBannerWidget(QFrame):
    """Notification banner for feedback messages, errors, and connection progress."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("class", "statusBanner")
        self.setVisible(False)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)

        self.icon_label = QLabel("ℹ️", self)
        self.icon_label.setFont(QFont(THEME["font_family"], 13))

        self.msg_label = QLabel("", self)
        self.msg_label.setFont(QFont(THEME["font_family"], 12))
        self.msg_label.setWordWrap(True)

        layout.addWidget(self.icon_label)
        layout.addWidget(self.msg_label, 1)

        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.hide_banner)

    def show_info(self, message: str, auto_hide_ms: int = 5000):
        self.setProperty("class", "statusBanner")
        self.style().unpolish(self)
        self.style().polish(self)
        self.icon_label.setText("ℹ️")
        self.msg_label.setText(message)
        self.setVisible(True)
        if auto_hide_ms > 0:
            self._hide_timer.start(auto_hide_ms)

    def show_success(self, message: str, auto_hide_ms: int = 6000):
        self.setProperty("class", "statusBannerSuccess")
        self.style().unpolish(self)
        self.style().polish(self)
        self.icon_label.setText("✅")
        self.msg_label.setText(message)
        self.setVisible(True)
        if auto_hide_ms > 0:
            self._hide_timer.start(auto_hide_ms)

    def show_error(self, message: str, auto_hide_ms: int = 8000):
        self.setProperty("class", "statusBannerError")
        self.style().unpolish(self)
        self.style().polish(self)
        self.icon_label.setText("⚠️")
        self.msg_label.setText(message)
        self.setVisible(True)
        if auto_hide_ms > 0:
            self._hide_timer.start(auto_hide_ms)

    def hide_banner(self):
        self.setVisible(False)
        self._hide_timer.stop()
