"""
Application Configuration and Constants for WinQRReader
"""
import os
import sys
from pathlib import Path

# Base Paths (Handling both dev mode and PyInstaller bundle mode)
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys._MEIPASS)
    USER_DATA_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "WinQRReader"
else:
    BASE_DIR = Path(__file__).resolve().parent.parent
    USER_DATA_DIR = BASE_DIR

LOGS_DIR = USER_DATA_DIR / "logs"
try:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
except Exception:
    import tempfile
    LOGS_DIR = Path(tempfile.gettempdir()) / "WinQRReader" / "logs"
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE_PATH = LOGS_DIR / "winqrreader.log"

ASSETS_DIR = BASE_DIR / "assets"
LOGO_PATH = ASSETS_DIR / "logo.png"

# Camera Settings
DEFAULT_CAMERA_INDEX = 0
CAMERA_FRAME_WIDTH = 1280
CAMERA_FRAME_HEIGHT = 720
CAMERA_FPS = 30

# UI Theme Tokens (Windows 11 Fluent Dark Theme)
THEME = {
    "bg_dark": "#18181b",           # Zinc 900
    "bg_card": "#27272a",           # Zinc 800
    "bg_card_hover": "#3f3f46",     # Zinc 700
    "bg_subtle": "#121214",         # Zinc 950
    "border_subtle": "#3f3f46",     # Zinc 700
    "border_focus": "#0078d4",      # Windows 11 Accent Blue
    "accent_primary": "#0078d4",    # Win 11 Blue
    "accent_hover": "#1084d8",
    "accent_pressed": "#006cbd",
    "accent_light": "#60cdff",      # Fluent Cyan Accent
    "success": "#10b981",           # Emerald 500
    "success_bg": "#064e3b",        # Emerald 900
    "warning": "#f59e0b",           # Amber 500
    "error": "#ef4444",             # Red 500
    "error_bg": "#450a0a",
    "text_primary": "#f4f4f5",      # Zinc 100
    "text_secondary": "#a1a1aa",    # Zinc 400
    "text_muted": "#71717a",        # Zinc 500
    "font_family": "'Segoe UI Variable Display', 'Segoe UI', -apple-system, sans-serif",
}
