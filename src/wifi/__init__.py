"""
WiFi Integration Package for WinQRReader (Windows netsh / Linux NetworkManager)
"""
from .linux_manager import LinuxWiFiManager
from .manager import ConnectionResult, WindowsWiFiManager, create_wifi_manager
from .profile_builder import generate_wlan_profile_xml

__all__ = [
    "WindowsWiFiManager",
    "LinuxWiFiManager",
    "ConnectionResult",
    "create_wifi_manager",
    "generate_wlan_profile_xml",
]
