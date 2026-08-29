"""
Unit & UI Tests for Manual Camera Activation Workflow
Ensures the camera is never automatically started on app launch and requires explicit user interaction.
"""
import sys
import unittest
from unittest.mock import MagicMock, patch

from PyQt6.QtWidgets import QApplication

from src.ui.components.camera_view import CameraViewWidget
from src.ui.main_window import MainWindow

# Ensure single QApplication instance
app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)


class TestCameraActivation(unittest.TestCase):
    """Test Camera Activation overlay and MainWindow integration."""

    def test_camera_view_initial_state(self):
        """CameraViewWidget must start in inactive state with activation button visible."""
        cam_view = CameraViewWidget()
        self.assertFalse(cam_view._is_activated)
        self.assertFalse(cam_view._activation_container.isHidden())
        self.assertEqual(cam_view._status_text, "Camera Inactive")
        self.assertIsNotNone(cam_view.btn_activate)

    def test_camera_view_activation_click_emits_signal(self):
        """Clicking activate button should hide overlay and emit activate_camera_requested."""
        cam_view = CameraViewWidget()
        signal_received = []
        cam_view.activate_camera_requested.connect(lambda: signal_received.append(True))

        cam_view.btn_activate.click()

        self.assertTrue(cam_view._is_activated)
        self.assertTrue(cam_view._activation_container.isHidden())
        self.assertEqual(len(signal_received), 1)

    def test_camera_view_set_activated_toggle(self):
        """set_activated(False) should restore activation overlay."""
        cam_view = CameraViewWidget()
        cam_view.btn_activate.click()
        self.assertTrue(cam_view._is_activated)

        cam_view.set_activated(False)
        self.assertFalse(cam_view._is_activated)
        self.assertFalse(cam_view._activation_container.isHidden())

    @patch("src.ui.main_window.CameraCaptureThread")
    def test_main_window_startup_no_autostart_and_no_session_memory(self, mock_capture_thread):
        """MainWindow should NOT start camera thread on launch, and must always require activation."""
        # First session
        win1 = MainWindow()
        self.assertIsNone(win1.camera_thread)
        self.assertFalse(win1.camera_view._activation_container.isHidden())
        mock_capture_thread.assert_not_called()

        # Trigger activation
        win1.camera_view.btn_activate.click()
        self.assertIsNotNone(win1.camera_thread)
        mock_capture_thread.assert_called_once()
        win1.close()

        # Re-open session (simulating app restart) -> MUST STILL BE INACTIVE
        mock_capture_thread.reset_mock()
        win2 = MainWindow()
        self.assertIsNone(win2.camera_thread)
        self.assertFalse(win2.camera_view._activation_container.isHidden())
        mock_capture_thread.assert_not_called()
        win2.close()


if __name__ == "__main__":
    unittest.main()
