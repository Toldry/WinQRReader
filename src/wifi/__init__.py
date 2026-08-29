"""
Windows WiFi Integration Package for WinQRReader
"""
from .manager import WindowsWiFiManager, ConnectionResult
from .profile_builder import generate_wlan_profile_xml

__all__ = ["WindowsWiFiManager", "ConnectionResult", "generate_wlan_profile_xml"]
