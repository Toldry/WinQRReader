"""
QR Code Processing Package for WinQRReader
"""
from .parser import WiFiCredentials, parse_wifi_qr, is_wifi_qr
from .detector import SuperReliableQRDetector

__all__ = ["WiFiCredentials", "parse_wifi_qr", "is_wifi_qr", "SuperReliableQRDetector"]
