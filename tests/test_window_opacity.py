"""
Regression Test for Top-Level Window Opacity
The global `QWidget { background: transparent }` rule once overrode the QMainWindow
background, which made the window see-through and smeared on Wayland compositors.
"""
import sys
import unittest
from unittest.mock import patch

from PyQt6.QtCore import QPoint
from PyQt6.QtGui import QColor, QImage
from PyQt6.QtWidgets import QApplication, QWidget

from src.ui.main_window import MainWindow

app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)

SAMPLE_STEP_PIXELS = 8


def count_non_opaque_pixels(widget: QWidget) -> int:
    """Render the widget onto a fully transparent canvas and count pixels it left see-through."""
    image = QImage(widget.size(), QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(QColor(0, 0, 0, 0))
    render_flags = QWidget.RenderFlag.DrawWindowBackground | QWidget.RenderFlag.DrawChildren
    widget.render(image, QPoint(), flags=render_flags)
    return sum(
        1
        for x in range(0, image.width(), SAMPLE_STEP_PIXELS)
        for y in range(0, image.height(), SAMPLE_STEP_PIXELS)
        if image.pixelColor(x, y).alpha() < 255
    )


class TestWindowOpacity(unittest.TestCase):
    @patch("src.ui.main_window.create_wifi_manager")
    def test_main_window_is_fully_opaque(self, _mock_wifi_manager):
        window = MainWindow()
        window.show()
        app.processEvents()
        try:
            self.assertEqual(count_non_opaque_pixels(window), 0)
        finally:
            window.close()


if __name__ == "__main__":
    unittest.main()
