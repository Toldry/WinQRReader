"""
QThread Camera Capture & Async QR Processing Worker
Delivers silky-smooth 30+ FPS camera streaming while running asynchronous zxing-cpp enhanced QR detection in the background.
Includes multi-backend fallback and camera contention recovery.
"""
import logging
import threading
import time
from typing import List, Optional

import cv2
import numpy as np
from PyQt6.QtCore import QMutex, QThread, pyqtSignal

from ..config import CAMERA_FPS, CAMERA_FRAME_HEIGHT, CAMERA_FRAME_WIDTH, DEFAULT_CAMERA_INDEX
from ..qr.detector import DetectionResult, SuperReliableQRDetector

try:
    import zxingcpp
    HAS_ZXING = True
except ImportError:
    HAS_ZXING = False

logger = logging.getLogger(__name__)


def list_available_cameras(max_tested: int = 4) -> List[int]:
    """Discover available camera indices on the system."""
    available = []
    for i in range(max_tested):
        # Quick non-blocking test with DSHOW, then default
        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap = cv2.VideoCapture(i)

        if cap.isOpened():
            ret, _ = cap.read()
            if ret:
                available.append(i)
            cap.release()
    return available if available else [0]


class CameraDiscoveryWorker(QThread):
    """Background worker to asynchronously probe and discover camera hardware without freezing UI."""
    cameras_discovered = pyqtSignal(list)

    def __init__(self, max_tested: int = 4):
        super().__init__()
        self.max_tested = max_tested

    def run(self):
        cameras = list_available_cameras(self.max_tested)
        self.cameras_discovered.emit(cameras)


class CameraCaptureThread(QThread):
    """
    High-performance video capture and detection thread.
    - Streams video frames at full camera framerate (30 FPS) without blocking.
    - Runs sub-millisecond zxing scan on every frame.
    - Offloads multi-scale / CLAHE enhanced inference passes to an async worker thread.
    - Handles camera contention and automatic device recovery.
    """

    frame_ready = pyqtSignal(np.ndarray, object)  # frame, DetectionResult
    qr_detected = pyqtSignal(object)              # DetectionResult
    error_occurred = pyqtSignal(str)
    camera_started = pyqtSignal()
    camera_stopped = pyqtSignal()

    def __init__(self, camera_index: int = DEFAULT_CAMERA_INDEX, detector: Optional[SuperReliableQRDetector] = None):
        super().__init__()
        self.camera_index = camera_index
        self.detector = detector if detector is not None else SuperReliableQRDetector()
        self.running = False
        self.detection_paused = False
        self.cap: Optional[cv2.VideoCapture] = None
        self._mutex = QMutex()

        # Asynchronous detection worker state
        self._latest_detection: Optional[DetectionResult] = None
        self._detection_lock = threading.Lock()
        self._pending_frame: Optional[np.ndarray] = None
        self._worker_thread: Optional[threading.Thread] = None

        self._last_detected_text = ""
        self._last_detected_time = 0.0
        self._resume_cooldown_time = 0.0
        self._flush_frames_count = 0

    def set_camera_index(self, index: int):
        self._mutex.lock()
        self.camera_index = index
        self._mutex.unlock()
        if self.isRunning():
            self.stop()
            self.start()

    def retry_camera(self):
        """Restart camera capture loop to re-acquire hardware."""
        if self.isRunning():
            self.stop()
        self.start()

    def pause_detection(self):
        """Pause scanning/capturing when QR code is found or user requested."""
        self._mutex.lock()
        self.detection_paused = True
        self._mutex.unlock()
        with self._detection_lock:
            self._pending_frame = None
            self._latest_detection = None

    def resume_detection(self):
        """Resume active QR scanning with hardware buffer flush and debounce cooldown."""
        self._mutex.lock()
        self.detection_paused = False
        self._last_detected_text = ""
        self._flush_frames_count = 5  # Flush 5 stale hardware buffer frames
        self._resume_cooldown_time = time.time() + 0.8  # 0.8s cooldown before re-detecting
        self._mutex.unlock()
        with self._detection_lock:
            self._pending_frame = None
            self._latest_detection = None

    def stop(self):
        self._mutex.lock()
        self.running = False
        self._mutex.unlock()
        self.wait(1000)

    def _async_detection_worker(self):
        """Background thread executing multi-tier CLAHE + Zoom + OpenCV detection passes."""
        while self.running:
            frame_to_process = None
            with self._detection_lock:
                if self._pending_frame is not None:
                    frame_to_process = self._pending_frame
                    self._pending_frame = None

            if frame_to_process is None:
                time.sleep(0.015)
                continue

            self._mutex.lock()
            paused = self.detection_paused
            cooldown_active = time.time() < self._resume_cooldown_time
            self._mutex.unlock()

            if paused or cooldown_active:
                time.sleep(0.03)
                continue

            # Run full heavy detection pipeline
            try:
                detection = self.detector.detect_and_decode(frame_to_process)
                with self._detection_lock:
                    if detection.found and not paused and not (time.time() < self._resume_cooldown_time):
                        self._latest_detection = detection
                    else:
                        self._latest_detection = None

                if detection.found and detection.text and not paused and not (time.time() < self._resume_cooldown_time):
                    self._handle_detection(detection)
            except Exception as e:
                logger.debug(f"Async detection error: {e}")

    def _handle_detection(self, detection: DetectionResult):
        current_time = time.time()
        if current_time < self._resume_cooldown_time:
            return
        if detection.text != self._last_detected_text or (current_time - self._last_detected_time > 2.0):
            self._last_detected_text = detection.text
            self._last_detected_time = current_time
            self.qr_detected.emit(detection)

    def _open_camera_with_fallback(self) -> Optional[cv2.VideoCapture]:
        """Attempt to open camera with DirectShow, MSMF, or default backend."""
        backends = [
            ("DirectShow", cv2.CAP_DSHOW),
            ("MediaFoundation", cv2.CAP_MSMF),
            ("Default", cv2.CAP_ANY),
        ]

        for name, backend in backends:
            logger.info(f"Attempting to open camera {self.camera_index} with backend {name}...")
            cap = cv2.VideoCapture(self.camera_index, backend)
            if cap.isOpened():
                # Test read a frame to confirm camera is not locked by another process
                ret, frame = cap.read()
                if ret and frame is not None:
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_FRAME_WIDTH)
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_FRAME_HEIGHT)
                    cap.set(cv2.CAP_PROP_FPS, CAMERA_FPS)
                    logger.info(f"Camera {self.camera_index} successfully acquired with {name}.")
                    return cap
                else:
                    logger.warning(f"Camera opened with {name} but failed to capture test frame (possible device lock).")
                    cap.release()
        return None

    def run(self):
        self.running = True
        self.cap = self._open_camera_with_fallback()

        if self.cap is None:
            self.error_occurred.emit("Camera is in use by another application or unavailable.")
            self.running = False
            return

        self.camera_started.emit()

        # Start asynchronous deep-learning detection worker
        self._worker_thread = threading.Thread(target=self._async_detection_worker, daemon=True)
        self._worker_thread.start()

        frame_interval = 1.0 / CAMERA_FPS
        last_frame_time = time.time()
        consecutive_read_failures = 0

        while self.running:
            self._mutex.lock()
            paused = self.detection_paused
            self._mutex.unlock()

            if paused:
                self.msleep(30)
                continue

            ret, frame = self.cap.read()
            if not ret or frame is None:
                consecutive_read_failures += 1
                if consecutive_read_failures > 30:  # ~1 second of continuous failures
                    self.error_occurred.emit("Camera connection lost or taken by another application.")
                    break
                self.msleep(10)
                continue

            consecutive_read_failures = 0

            # Flip horizontally for natural mirror effect
            frame = cv2.flip(frame, 1)

            # Flush stale hardware buffer frames if resuming
            flushing = False
            self._mutex.lock()
            if self._flush_frames_count > 0:
                self._flush_frames_count -= 1
                flushing = True
            cooldown_active = time.time() < self._resume_cooldown_time
            self._mutex.unlock()

            # Fast Pass: Instant zxing-cpp check (<2ms) directly on stream (skip if flushing/cooldown)
            current_detection = None
            if not flushing and not cooldown_active and HAS_ZXING:
                try:
                    zx_res = zxingcpp.read_barcode(frame)
                    if zx_res and zx_res.valid and zx_res.text.strip():
                        pts = self.detector._zxing_points_to_numpy(zx_res.position)
                        current_detection = DetectionResult(
                            text=zx_res.text.strip(),
                            points=pts,
                            engine="zxing-cpp",
                            found=True,
                        )
                        self._handle_detection(current_detection)
                except Exception:
                    pass

            # Queue frame for background enhanced inference (skip if flushing/cooldown)
            with self._detection_lock:
                if not flushing and not cooldown_active:
                    self._pending_frame = frame
                    if current_detection is None and self._latest_detection is not None:
                        current_detection = self._latest_detection
                else:
                    self._pending_frame = None
                    current_detection = None

            # Emit frame immediately for silky-smooth 30 FPS video streaming!
            self.frame_ready.emit(frame.copy(), current_detection)

            elapsed = time.time() - last_frame_time
            sleep_time = max(0.001, frame_interval - elapsed)
            time.sleep(sleep_time)
            last_frame_time = time.time()

        if self.cap is not None:
            self.cap.release()
            self.cap = None

        self.camera_stopped.emit()
        logger.info("Camera capture thread terminated.")
