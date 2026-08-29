"""
Unit and Integration Tests for SuperReliableQRDetector
"""
import unittest
import cv2
import numpy as np
import qrcode
from PIL import Image

from src.qr.detector import SuperReliableQRDetector


def generate_qr_image(payload: str, box_size: int = 10, border: int = 4) -> np.ndarray:
    """Generate in-memory BGR numpy array containing QR code."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=box_size,
        border=border,
    )
    qr.add_data(payload)
    qr.make(fit=True)
    img_pil = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    img_np = np.array(img_pil)
    # Convert RGB to BGR
    return cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)


class TestSuperReliableQRDetector(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.detector = SuperReliableQRDetector()

    def test_detector_clean_wifi_qr(self):
        payload = "WIFI:T:WPA;S:LivingRoom;P:Secret123;;"
        frame = generate_qr_image(payload)

        result = self.detector.detect_and_decode(frame)
        self.assertTrue(result.found, "Expected QR code to be found")
        self.assertEqual(result.text, payload)
        self.assertIn(result.engine, ["zxing-cpp", "zxing-CLAHE", "zxing-ZoomCrop", "zxing-Zoom2x", "OpenCV-Standard", "OpenCV-CLAHE"])
        self.assertIsNotNone(result.points)

    def test_detector_embedded_in_large_frame(self):
        payload = "WIFI:T:WPA3;S:CoffeeShop_5G;P:BestCoffee2026;;"
        qr_img = generate_qr_image(payload, box_size=6)
        qh, qw = qr_img.shape[:2]

        # Place QR inside a 1280x720 simulated webcam frame
        large_frame = np.ones((720, 1280, 3), dtype=np.uint8) * 180  # Gray background
        start_y = (720 - qh) // 2
        start_x = (1280 - qw) // 2
        large_frame[start_y : start_y + qh, start_x : start_x + qw] = qr_img

        result = self.detector.detect_and_decode(large_frame)
        self.assertTrue(result.found)
        self.assertEqual(result.text, payload)

    def test_detector_blurred_image(self):
        payload = "WIFI:T:WPA;S:BlurredScreenNet;P:password999;;"
        frame = generate_qr_image(payload)
        # Apply Gaussian blur simulating camera out-of-focus
        blurred = cv2.GaussianBlur(frame, (5, 5), 1.5)

        result = self.detector.detect_and_decode(blurred)
        self.assertTrue(result.found)
        self.assertEqual(result.text, payload)

    def test_detector_empty_frame(self):
        empty = np.zeros((480, 640, 3), dtype=np.uint8)
        result = self.detector.detect_and_decode(empty)
        self.assertFalse(result.found)
        self.assertEqual(result.text, "")


if __name__ == "__main__":
    unittest.main()
