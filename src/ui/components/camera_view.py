"""
Custom Camera Viewport Widget with High-DPI QPainter Rendering,
Scanning Reticle HUD, Animated QR Polygon, and Camera Error Recovery Overlay
"""
import math
from typing import Optional

import cv2
import numpy as np
from PyQt6.QtCore import QPointF, QRect, QRectF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QFont, QImage, QLinearGradient, QPainter, QPen, QPolygonF
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from ...config import THEME
from ...qr.detector import DetectionResult


class CameraViewWidget(QWidget):
    """
    Renders live camera frames with an overlay containing:
    - Scanning guide box with animated laser sweep line
    - Dynamic bounding box tracking detected QR codes
    - In-viewport activation state with Activate Camera button
    - In-viewport error state with Retry button
    """

    activate_camera_requested = pyqtSignal()
    retry_camera_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(480, 360)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)

        self._frame_image: Optional[QImage] = None
        self._last_detection: Optional[DetectionResult] = None
        self._is_paused = False
        self._is_activated = False
        self._has_error = False
        self._status_text = "Camera Inactive"
        self._raw_frame_size = (1280, 720)

        # Reticle animation timer (60 FPS smooth rendering)
        self._anim_phase = 0.0
        self._anim_counter = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_anim_tick)
        self._timer.start(16)  # ~60 FPS smooth animation

        # Overlays
        self._setup_activation_overlay()
        self._setup_error_overlay()

    def _setup_activation_overlay(self):
        self._activation_container = QWidget(self)
        self._activation_container.setVisible(True)

        layout = QVBoxLayout(self._activation_container)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(12)

        self._act_icon = QLabel("📷", self._activation_container)
        self._act_icon.setFont(QFont(THEME["font_family"], 36))
        self._act_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._act_title = QLabel("Camera Inactive", self._activation_container)
        self._act_title.setFont(QFont(THEME["font_family"], 15, QFont.Weight.DemiBold))
        self._act_title.setStyleSheet("color: #ffffff;")
        self._act_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._act_subtitle = QLabel(
            "Click Activate Camera to start the live video feed and scan WiFi QR codes.",
            self._activation_container,
        )
        self._act_subtitle.setFont(QFont(THEME["font_family"], 11))
        self._act_subtitle.setStyleSheet(f"color: {THEME['text_secondary']};")
        self._act_subtitle.setWordWrap(True)
        self._act_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.btn_activate = QPushButton("⚡ Activate Camera", self._activation_container)
        self.btn_activate.setProperty("class", "primaryBtn")
        self.btn_activate.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_activate.clicked.connect(self._on_activate_clicked)

        btn_row = QHBoxLayout()
        btn_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        btn_row.addWidget(self.btn_activate)

        layout.addWidget(self._act_icon)
        layout.addWidget(self._act_title)
        layout.addWidget(self._act_subtitle)
        layout.addLayout(btn_row)

    def _setup_error_overlay(self):
        self._error_container = QWidget(self)
        self._error_container.setVisible(False)

        layout = QVBoxLayout(self._error_container)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(12)

        self._err_icon = QLabel("📷", self._error_container)
        self._err_icon.setFont(QFont(THEME["font_family"], 32))
        self._err_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._err_msg = QLabel("Camera is in use by another application or unavailable.", self._error_container)
        self._err_msg.setFont(QFont(THEME["font_family"], 13, QFont.Weight.Medium))
        self._err_msg.setStyleSheet("color: #f87171;")
        self._err_msg.setWordWrap(True)
        self._err_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._err_tip = QLabel("Please ensure other instances or apps (Teams, Zoom, Camera) are closed.", self._error_container)
        self._err_tip.setFont(QFont(THEME["font_family"], 11))
        self._err_tip.setStyleSheet(f"color: {THEME['text_secondary']};")
        self._err_tip.setWordWrap(True)
        self._err_tip.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.btn_retry = QPushButton("🔄 Retry Camera", self._error_container)
        self.btn_retry.setProperty("class", "primaryBtn")
        self.btn_retry.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_retry.clicked.connect(self._on_retry_clicked)

        btn_row = QHBoxLayout()
        btn_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        btn_row.addWidget(self.btn_retry)

        layout.addWidget(self._err_icon)
        layout.addWidget(self._err_msg)
        layout.addWidget(self._err_tip)
        layout.addLayout(btn_row)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "_activation_container"):
            self._activation_container.setGeometry(self.rect())
        if hasattr(self, "_error_container"):
            self._error_container.setGeometry(self.rect())

    def _on_activate_clicked(self):
        self._activation_container.setVisible(False)
        self._is_activated = True
        self._status_text = "Starting camera..."
        self.update()
        self.activate_camera_requested.emit()

    def set_activated(self, activated: bool):
        """Programmatically switch between activated and deactivated states."""
        self._is_activated = activated
        self._activation_container.setVisible(not activated)
        if not activated:
            self._frame_image = None
            self._last_detection = None
            self._has_error = False
            self._error_container.setVisible(False)
            self._status_text = "Camera Inactive"
        self.update()

    def _on_retry_clicked(self):
        self._has_error = False
        self._error_container.setVisible(False)
        self._status_text = "Retrying camera..."
        self.update()
        self.retry_camera_requested.emit()

    def _on_anim_tick(self):
        self._anim_counter += 1
        # Gentle, calm sinusoidal sweep taking ~3.5 seconds per cycle
        self._anim_phase = (math.sin(self._anim_counter * 0.035) + 1.0) / 2.0
        if not self._is_paused and not self._has_error and self._is_activated:
            self.update()

    def update_frame(self, frame_bgr: np.ndarray, detection: Optional[DetectionResult] = None):
        """Receive frame from camera thread and convert to QImage."""
        if self._has_error:
            self._has_error = False
            self._error_container.setVisible(False)

        if self._activation_container.isVisible():
            self._activation_container.setVisible(False)
        self._is_activated = True

        h, w, ch = frame_bgr.shape
        self._raw_frame_size = (w, h)
        self._last_detection = detection

        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        bytes_per_line = ch * w
        self._frame_image = QImage(rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888).copy()
        self.update()

    def set_paused(self, paused: bool, status_text: str = "Scanning Paused"):
        self._is_paused = paused
        self._status_text = status_text
        if not paused:
            self._last_detection = None
        self.update()

    def set_error(self, message: str):
        """Display error overlay inside viewfinder with retry option."""
        self._has_error = True
        self._activation_container.setVisible(False)
        self._frame_image = None
        self._err_msg.setText(message)
        self._error_container.setGeometry(self.rect())
        self._error_container.setVisible(True)
        self.update()

    def set_status_text(self, text: str):
        self._status_text = text
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        rect = self.rect()

        # Background Fill
        painter.fillRect(rect, QColor(THEME["bg_subtle"]))

        if not self._has_error:
            if self._frame_image is not None and not self._frame_image.isNull():
                img_scaled = self._frame_image.scaled(
                    self.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )

                img_x = (self.width() - img_scaled.width()) // 2
                img_y = (self.height() - img_scaled.height()) // 2
                target_rect = QRect(img_x, img_y, img_scaled.width(), img_scaled.height())

                painter.drawImage(target_rect, img_scaled)

                self._draw_scanning_hud(painter, target_rect)

                if self._last_detection and self._last_detection.found and self._last_detection.points is not None:
                    self._draw_detected_polygon(painter, target_rect, self._last_detection)
            else:
                self._draw_standby_placeholder(painter, rect)

            if self._is_paused:
                self._draw_paused_overlay(painter, rect)

        painter.end()

    def _draw_standby_placeholder(self, painter: QPainter, rect: QRect):
        if hasattr(self, "_activation_container") and self._activation_container.isVisible():
            return
        painter.setPen(QColor(THEME["text_secondary"]))
        font = QFont(THEME["font_family"], 12)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self._status_text)

    def _draw_scanning_hud(self, painter: QPainter, frame_rect: QRect):
        """Draw a sleek scanning reticle with corner brackets and laser scan line."""
        if self._is_paused:
            return

        box_size = min(frame_rect.width(), frame_rect.height()) * 0.65
        cx = frame_rect.center().x()
        cy = frame_rect.center().y()
        rx = int(cx - box_size / 2)
        ry = int(cy - box_size / 2)
        rw = int(box_size)
        rh = int(box_size)

        corner_len = 24
        pen = QPen(QColor(THEME["accent_light"]), 3)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)

        # Corners
        painter.drawLine(rx, ry + corner_len, rx, ry)
        painter.drawLine(rx, ry, rx + corner_len, ry)
        painter.drawLine(rx + rw - corner_len, ry, rx + rw, ry)
        painter.drawLine(rx + rw, ry, rx + rw, ry + corner_len)
        painter.drawLine(rx, ry + rh - corner_len, rx, ry + rh)
        painter.drawLine(rx, ry + rh, rx + corner_len, ry + rh)
        painter.drawLine(rx + rw - corner_len, ry + rh, rx + rw, ry + rh)
        painter.drawLine(rx + rw, ry + rh - corner_len, rx + rw, ry + rh)

        # Smooth Laser Scan Line
        scan_y = ry + int(self._anim_phase * rh)
        laser_grad = QLinearGradient(rx, scan_y, rx + rw, scan_y)
        laser_grad.setColorAt(0.0, QColor(0, 120, 212, 0))
        laser_grad.setColorAt(0.5, QColor(96, 205, 255, 180))
        laser_grad.setColorAt(1.0, QColor(0, 120, 212, 0))

        laser_pen = QPen(QBrush(laser_grad), 2)
        painter.setPen(laser_pen)
        painter.drawLine(rx + 4, scan_y, rx + rw - 4, scan_y)

    def _draw_detected_polygon(self, painter: QPainter, frame_rect: QRect, detection: DetectionResult):
        """Draw tracked neon polygon around detected QR code."""
        orig_w, orig_h = self._raw_frame_size
        scale_x = frame_rect.width() / max(1, orig_w)
        scale_y = frame_rect.height() / max(1, orig_h)
        offset_x = frame_rect.x()
        offset_y = frame_rect.y()

        points = detection.points
        if points is None or len(points) == 0:
            return

        poly = QPolygonF()
        for pt in points:
            px = float(pt[0]) * scale_x + offset_x
            py = float(pt[1]) * scale_y + offset_y
            poly.append(QPointF(px, py))

        fill_color = QColor(16, 185, 129, 45)
        painter.setBrush(QBrush(fill_color))

        pen = QPen(QColor(16, 185, 129), 2.5)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.drawPolygon(poly)

        painter.setBrush(QBrush(QColor(255, 255, 255)))
        painter.setPen(QPen(QColor(16, 185, 129), 1.5))
        for pt in poly:
            painter.drawEllipse(pt, 4, 4)

        if poly.count() > 0:
            top_pt = poly[0]
            tag_rect = QRectF(top_pt.x() - 40, top_pt.y() - 26, 90, 20)
            painter.setBrush(QBrush(QColor(24, 24, 27, 220)))
            painter.setPen(QPen(QColor(16, 185, 129), 1))
            painter.drawRoundedRect(tag_rect, 4, 4)

            painter.setPen(QColor(16, 185, 129))
            font = QFont(THEME["font_family"], 9, QFont.Weight.Bold)
            painter.setFont(font)
            painter.drawText(tag_rect, Qt.AlignmentFlag.AlignCenter, f"✓ {detection.engine}")

    def _draw_paused_overlay(self, painter: QPainter, rect: QRect):
        """Draw frosted dark tint and paused text when camera is paused."""
        painter.fillRect(rect, QColor(0, 0, 0, 120))

        badge_w, badge_h = 220, 36
        bx = (rect.width() - badge_w) // 2
        by = rect.height() - badge_h - 20
        badge_rect = QRect(bx, by, badge_w, badge_h)

        painter.setBrush(QBrush(QColor(24, 24, 27, 230)))
        painter.setPen(QPen(QColor(THEME["border_subtle"]), 1))
        painter.drawRoundedRect(badge_rect, 18, 18)

        painter.setPen(QColor(THEME["text_primary"]))
        font = QFont(THEME["font_family"], 11, QFont.Weight.Medium)
        painter.setFont(font)
        painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, f"⏸  {self._status_text}")
