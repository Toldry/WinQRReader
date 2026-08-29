"""
Super-Reliable QR Code Detection Engine powered by zxing-cpp
with Adaptive Preprocessing (CLAHE, Polarity Inversion, Multi-Scale Center Zoom & 2x Upscaling)
and OpenCV QRCodeDetector Fallback.
"""
import logging
from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np

try:
    import zxingcpp
    HAS_ZXING = True
except ImportError:
    HAS_ZXING = False

logger = logging.getLogger(__name__)


@dataclass
class DetectionResult:
    text: str
    points: Optional[np.ndarray] = None  # Shape (4, 2)
    engine: str = "None"
    found: bool = False


class SuperReliableQRDetector:
    """
    High-accuracy, sub-millisecond QR code detector optimized for laptop webcams scanning smartphone screens.
    Uses zxing-cpp as the core high-performance engine backed by multi-stage optical enhancement passes:
    1. Native full-frame zxing scan
    2. CLAHE adaptive contrast normalization (anti-glare)
    3. Dark-mode polarity inversion
    4. Multi-scale center digital zoom crops (0.75x, 0.60x, 0.50x) with 2x cubic super-sampling
    5. OpenCV standard QRCodeDetector fallback
    """

    def __init__(self):
        self.opencv_detector = cv2.QRCodeDetector()
        self.clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))

    def detect_and_decode(self, frame: np.ndarray) -> DetectionResult:
        """Execute the multi-tier QR detection pipeline on an incoming video frame or photo."""
        if frame is None or frame.size == 0:
            return DetectionResult(text="", found=False)

        # Normalize color channels
        if len(frame.shape) == 2:
            bgr = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
            gray = frame
        elif frame.shape[2] == 4:
            bgr = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
            gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        else:
            bgr = frame
            gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

        # -------------------------------------------------------------
        # Tier 1: Fast native frame pass via zxing-cpp
        # -------------------------------------------------------------
        if HAS_ZXING:
            try:
                zx_res = zxingcpp.read_barcode(
                    bgr,
                    try_rotate=True,
                    try_downscale=True,
                    try_invert=True,
                )
                if zx_res and zx_res.valid and zx_res.text.strip():
                    pts = self._zxing_points_to_numpy(zx_res.position)
                    return DetectionResult(text=zx_res.text.strip(), points=pts, engine="zxing-cpp", found=True)
            except Exception as e:
                logger.debug(f"zxing native scan error: {e}")

        # -------------------------------------------------------------
        # Tier 2: CLAHE Adaptive Contrast Enhancement
        # (Fixes phone screen glare and washed-out webcam exposures)
        # -------------------------------------------------------------
        enhanced_gray = self.clahe.apply(gray)
        enhanced_bgr = cv2.cvtColor(enhanced_gray, cv2.COLOR_GRAY2BGR)

        if HAS_ZXING:
            try:
                zx_res = zxingcpp.read_barcode(
                    enhanced_bgr,
                    try_rotate=True,
                    try_downscale=True,
                    try_invert=True,
                )
                if zx_res and zx_res.valid and zx_res.text.strip():
                    pts = self._zxing_points_to_numpy(zx_res.position)
                    return DetectionResult(text=zx_res.text.strip(), points=pts, engine="zxing-CLAHE", found=True)
            except Exception:
                pass

        # -------------------------------------------------------------
        # Tier 3: Inverted Polarity (for dark-mode phone screens)
        # -------------------------------------------------------------
        inverted_gray = cv2.bitwise_not(gray)
        if HAS_ZXING:
            try:
                zx_res = zxingcpp.read_barcode(
                    inverted_gray,
                    try_rotate=True,
                    try_downscale=True,
                    try_invert=True,
                )
                if zx_res and zx_res.valid and zx_res.text.strip():
                    pts = self._zxing_points_to_numpy(zx_res.position)
                    return DetectionResult(text=zx_res.text.strip(), points=pts, engine="zxing-Inverted", found=True)
            except Exception:
                pass

        # -------------------------------------------------------------
        # Tier 4: Multi-Scale Center Digital Zoom Crops & 2x Upsampling
        # (Detects small or distant phone screens held at natural distance)
        # -------------------------------------------------------------
        h, w = frame.shape[:2]
        for crop_ratio in [0.75, 0.60, 0.50]:
            crop_w = int(w * crop_ratio)
            crop_h = int(h * crop_ratio)
            x1 = (w - crop_w) // 2
            y1 = (h - crop_h) // 2
            cropped_bgr = bgr[y1 : y1 + crop_h, x1 : x1 + crop_w]

            if HAS_ZXING:
                try:
                    zx_res = zxingcpp.read_barcode(
                        cropped_bgr,
                        try_rotate=True,
                        try_downscale=True,
                        try_invert=True,
                    )
                    if zx_res and zx_res.valid and zx_res.text.strip():
                        pts = self._zxing_points_to_numpy(zx_res.position)
                        if pts is not None:
                            pts[:, 0] += x1
                            pts[:, 1] += y1
                        return DetectionResult(text=zx_res.text.strip(), points=pts, engine="zxing-ZoomCrop", found=True)
                except Exception:
                    pass

            # 2x Cubic Upscaling on Center Crop
            try:
                crop_2x = cv2.resize(cropped_bgr, (0, 0), fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
                if HAS_ZXING:
                    zx_res = zxingcpp.read_barcode(
                        crop_2x,
                        try_rotate=True,
                        try_downscale=True,
                        try_invert=True,
                    )
                    if zx_res and zx_res.valid and zx_res.text.strip():
                        pts = self._zxing_points_to_numpy(zx_res.position)
                        if pts is not None:
                            pts[:, 0] = pts[:, 0] / 2.0 + x1
                            pts[:, 1] = pts[:, 1] / 2.0 + y1
                        return DetectionResult(text=zx_res.text.strip(), points=pts, engine="zxing-Zoom2x", found=True)
            except Exception:
                pass

        # -------------------------------------------------------------
        # Tier 5: Standard OpenCV QRCodeDetector Fallback
        # -------------------------------------------------------------
        try:
            text, points, _ = self.opencv_detector.detectAndDecode(gray)
            if text and text.strip():
                pts = np.array(points[0], dtype=np.float32) if points is not None and len(points) > 0 else None
                return DetectionResult(text=text.strip(), points=pts, engine="OpenCV-Standard", found=True)
        except Exception:
            pass

        try:
            text, points, _ = self.opencv_detector.detectAndDecode(enhanced_gray)
            if text and text.strip():
                pts = np.array(points[0], dtype=np.float32) if points is not None and len(points) > 0 else None
                return DetectionResult(text=text.strip(), points=pts, engine="OpenCV-CLAHE", found=True)
        except Exception:
            pass

        return DetectionResult(text="", found=False)

    def _zxing_points_to_numpy(self, pos) -> Optional[np.ndarray]:
        """Convert zxing Position object into standard (4, 2) numpy array."""
        try:
            pts = [
                [pos.top_left.x, pos.top_left.y],
                [pos.top_right.x, pos.top_right.y],
                [pos.bottom_right.x, pos.bottom_right.y],
                [pos.bottom_left.x, pos.bottom_left.y],
            ]
            return np.array(pts, dtype=np.float32)
        except Exception:
            return None
