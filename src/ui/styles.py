"""
Windows 11 Fluent Dark Theme Stylesheet for WinQRReader
"""
from ..config import THEME

FLUENT_DARK_STYLESHEET = f"""
/* Global Reset and Font */
* {{
    font-family: {THEME['font_family']};
    font-size: 13px;
    color: {THEME['text_primary']};
    outline: none;
}}

/* Main Window */
QMainWindow {{
    background-color: {THEME['bg_dark']};
}}

QWidget {{
    background-color: transparent;
}}

/* Header and Navigation */
#headerBar {{
    background-color: {THEME['bg_subtle']};
    border-bottom: 1px solid {THEME['border_subtle']};
    padding: 8px 16px;
}}

#appTitle {{
    font-size: 18px;
    font-weight: 700;
    color: #ffffff;
    letter-spacing: -0.3px;
}}

#appSubtitle {{
    font-size: 11px;
    color: {THEME['text_secondary']};
}}

/* Cards and Panels */
QFrame.card {{
    background-color: {THEME['bg_card']};
    border: 1px solid {THEME['border_subtle']};
    border-radius: 12px;
    padding: 16px;
}}

QFrame.cameraFrame {{
    background-color: #09090b;
    border: 1px solid {THEME['border_subtle']};
    border-radius: 12px;
}}

/* Labels */
QLabel.heading {{
    font-size: 16px;
    font-weight: 600;
    color: #ffffff;
}}

QLabel.subheading {{
    font-size: 12px;
    color: {THEME['text_secondary']};
}}

QLabel.badge {{
    background-color: rgba(96, 205, 255, 0.15);
    color: {THEME['accent_light']};
    border: 1px solid rgba(96, 205, 255, 0.3);
    border-radius: 6px;
    padding: 3px 8px;
    font-weight: 600;
    font-size: 11px;
}}

QLabel.badgeSuccess {{
    background-color: rgba(16, 185, 129, 0.15);
    color: {THEME['success']};
    border: 1px solid rgba(16, 185, 129, 0.3);
    border-radius: 6px;
    padding: 3px 8px;
    font-weight: 600;
    font-size: 11px;
}}

/* Text Inputs */
QLineEdit {{
    background-color: rgba(0, 0, 0, 0.35);
    border: 1px solid {THEME['border_subtle']};
    border-radius: 8px;
    padding: 8px 12px;
    color: #ffffff;
    font-size: 13px;
    selection-background-color: {THEME['accent_primary']};
}}

QLineEdit:focus {{
    border: 1.5px solid {THEME['accent_light']};
    background-color: rgba(0, 0, 0, 0.5);
}}

QLineEdit:read-only {{
    background-color: rgba(0, 0, 0, 0.2);
    color: {THEME['text_secondary']};
}}

/* Primary Buttons */
QPushButton.primaryBtn {{
    background-color: {THEME['accent_primary']};
    color: #ffffff;
    font-weight: 600;
    font-size: 13px;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    padding: 10px 20px;
    min-height: 20px;
}}

QPushButton.primaryBtn:hover {{
    background-color: {THEME['accent_hover']};
}}

QPushButton.primaryBtn:pressed {{
    background-color: {THEME['accent_pressed']};
}}

QPushButton.primaryBtn:disabled {{
    background-color: #3f3f46;
    color: #71717a;
    border: none;
}}

/* Secondary Buttons */
QPushButton.secondaryBtn {{
    background-color: rgba(255, 255, 255, 0.06);
    color: {THEME['text_primary']};
    font-weight: 500;
    font-size: 13px;
    border: 1px solid {THEME['border_subtle']};
    border-radius: 8px;
    padding: 8px 16px;
    min-height: 20px;
}}

QPushButton.secondaryBtn:hover {{
    background-color: rgba(255, 255, 255, 0.12);
    border-color: rgba(255, 255, 255, 0.2);
}}

QPushButton.secondaryBtn:pressed {{
    background-color: rgba(255, 255, 255, 0.04);
}}

/* Icon Buttons */
QPushButton.iconBtn {{
    background-color: rgba(255, 255, 255, 0.06);
    border: 1px solid {THEME['border_subtle']};
    border-radius: 6px;
    padding: 6px 10px;
}}

QPushButton.iconBtn:hover {{
    background-color: rgba(255, 255, 255, 0.15);
}}

/* Combo Box (Camera Selector) */
QComboBox {{
    background-color: rgba(255, 255, 255, 0.06);
    border: 1px solid {THEME['border_subtle']};
    border-radius: 8px;
    padding: 6px 12px;
    color: {THEME['text_primary']};
    min-width: 140px;
}}

QComboBox:hover {{
    background-color: rgba(255, 255, 255, 0.1);
}}

QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 24px;
    border-left: none;
}}

QComboBox QAbstractItemView {{
    background-color: {THEME['bg_card']};
    border: 1px solid {THEME['border_subtle']};
    border-radius: 8px;
    selection-background-color: {THEME['accent_primary']};
    selection-color: #ffffff;
    padding: 4px;
}}

/* Status Banner */
QFrame.statusBanner {{
    background-color: rgba(39, 39, 42, 0.95);
    border: 1px solid {THEME['border_subtle']};
    border-radius: 8px;
    padding: 8px 12px;
}}

QFrame.statusBannerSuccess {{
    background-color: rgba(6, 78, 59, 0.85);
    border: 1px solid rgba(16, 185, 129, 0.4);
    border-radius: 8px;
    padding: 8px 12px;
}}

QFrame.statusBannerError {{
    background-color: rgba(69, 10, 10, 0.85);
    border: 1px solid rgba(239, 68, 68, 0.4);
    border-radius: 8px;
    padding: 8px 12px;
}}

/* Scrollbars */
QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 0px;
}}

QScrollBar::handle:vertical {{
    background: #3f3f46;
    min-height: 20px;
    border-radius: 4px;
}}

QScrollBar::handle:vertical:hover {{
    background: #52525b;
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
"""
