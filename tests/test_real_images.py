"""
Unit tests verifying QR code recognition and WiFi credential extraction
on all real-world webcam photos in test_imgs/
"""
import os
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import cv2
from src.qr.detector import SuperReliableQRDetector
from src.qr.parser import WiFiCredentials, is_wifi_qr, parse_wifi_qr


class TestRealLifeQRImages(unittest.TestCase):
    """Verifies that every real-life webcam photo in test_imgs is detected and parsed correctly."""

    @classmethod
    def setUpClass(cls):
        cls.detector = SuperReliableQRDetector()
        cls.test_imgs_dir = Path(__file__).resolve().parent.parent / "test_imgs"
        cls.image_files = sorted(
            [f for f in os.listdir(cls.test_imgs_dir) if f.lower().endswith((".jpg", ".png", ".jpeg"))],
            key=lambda x: int(x.replace("test_photo_", "").replace(".jpg", "").replace(".png", ""))
            if x.startswith("test_photo_") and x.split(".")[0].replace("test_photo_", "").isdigit()
            else x,
        )

    def test_directory_has_images(self):
        """Verify that the test_imgs directory contains photos."""
        self.assertTrue(self.test_imgs_dir.exists(), f"Directory not found: {self.test_imgs_dir}")
        self.assertGreater(len(self.image_files), 0, "No image files found in test_imgs/")

    def test_all_real_world_images(self):
        """Verify that every single photo in test_imgs decodes to valid WiFi credentials."""
        results = []
        for fname in self.image_files:
            fpath = self.test_imgs_dir / fname
            with self.subTest(image=fname):
                img = cv2.imread(str(fpath))
                self.assertIsNotNone(img, f"Failed to read image: {fname}")

                detection = self.detector.detect_and_decode(img)
                self.assertTrue(
                    detection.found,
                    f"QR code was not detected in {fname} using any detection tier."
                )

                # Validate WiFi format
                self.assertTrue(
                    is_wifi_qr(detection.text),
                    f"{fname}: Decoded text is not a WiFi URI: {detection.text}"
                )

                # Validate parsed credentials
                creds = parse_wifi_qr(detection.text)
                self.assertIsNotNone(creds, f"{fname}: Could not parse WiFi credentials")
                self.assertTrue(bool(creds.ssid), f"{fname}: Parsed SSID is empty")

                results.append((fname, detection.engine, creds.ssid, creds.display_auth))

        print("\n" + "=" * 70)
        print(f"Real-World Photo Verification: {len(results)}/{len(self.image_files)} Passed")
        print("=" * 70)
        for fname, engine, ssid, auth in results:
            print(f"  [OK] {fname:<18} | Engine: {engine:<15} | SSID: {ssid:<15} | Auth: {auth}")
        print("=" * 70 + "\n")


if __name__ == "__main__":
    unittest.main()
