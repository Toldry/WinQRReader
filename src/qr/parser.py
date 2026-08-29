"""
Parser for WiFi QR Code schemas and general QR payloads
"""
import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class WiFiCredentials:
    ssid: str
    auth_type: str = "WPA2"  # WPA, WPA2, WPA3, WEP, nopass (Open)
    password: str = ""
    is_hidden: bool = False
    raw_payload: str = ""

    @property
    def display_auth(self) -> str:
        t = self.auth_type.upper()
        if t in ("WPA", "WPA2", "WPA2-PSK", "WPA-PSK"):
            return "WPA2-Personal"
        elif t in ("WPA3", "SAE", "WPA3-SAE"):
            return "WPA3-Personal"
        elif t == "WEP":
            return "WEP"
        elif t in ("NOPASS", "OPEN", "NONE", ""):
            return "Open (No Password)"
        return t

    @property
    def requires_password(self) -> bool:
        return self.auth_type.upper() not in ("NOPASS", "OPEN", "NONE", "")


def is_wifi_qr(text: str) -> bool:
    """Check if raw QR text adheres to WiFi URI schema."""
    if not text:
        return False
    clean = text.strip()
    return clean.upper().startswith("WIFI:")


def unescape_wifi_string(value: str) -> str:
    """Unescape special characters formatted according to WiFi QR standard (e.g. \\;, \\:, \\\\)."""
    # Replace escaped sequences
    result = []
    i = 0
    while i < len(value):
        if value[i] == "\\" and i + 1 < len(value):
            next_char = value[i + 1]
            if next_char in ("\\", ";", ":", ","):
                result.append(next_char)
                i += 2
                continue
        result.append(value[i])
        i += 1
    return "".join(result)


def parse_wifi_qr(text: str) -> Optional[WiFiCredentials]:
    """
    Parse standard WiFi QR code string into WiFiCredentials.
    Example: 'WIFI:T:WPA;S:MyNetwork;P:MyPassword;H:false;;'
    """
    if not text or not is_wifi_qr(text):
        return None

    raw_clean = text.strip()
    content = raw_clean[5:]  # Strip 'WIFI:' prefix

    # Parse key-value tokens handling escaped semicolons and colons
    fields = {}
    tokens = []
    current_token = []
    i = 0
    while i < len(content):
        if content[i] == "\\" and i + 1 < len(content):
            current_token.append(content[i : i + 2])
            i += 2
            continue
        elif content[i] == ";":
            token_str = "".join(current_token).strip()
            if token_str:
                tokens.append(token_str)
            current_token = []
            i += 1
            continue
        else:
            current_token.append(content[i])
            i += 1

    token_str = "".join(current_token).strip()
    if token_str:
        tokens.append(token_str)

    for token in tokens:
        # Find first non-escaped colon
        colon_idx = -1
        j = 0
        while j < len(token):
            if token[j] == "\\" and j + 1 < len(token):
                j += 2
                continue
            if token[j] == ":":
                colon_idx = j
                break
            j += 1

        if colon_idx != -1:
            key = token[:colon_idx].strip().upper()
            val = token[colon_idx + 1 :]
            fields[key] = val

    ssid_raw = fields.get("S", "")
    auth_raw = fields.get("T", "WPA").upper()
    pass_raw = fields.get("P", "")
    hidden_raw = fields.get("H", "false").lower()

    if not ssid_raw:
        # If no explicit S: tag, try to recover
        return None

    ssid = unescape_wifi_string(ssid_raw)
    password = unescape_wifi_string(pass_raw)

    # Normalize auth type
    if auth_raw in ("WPA", "WPA2", "WPA/WPA2", "WPA2-PSK"):
        auth_type = "WPA2"
    elif auth_raw in ("WPA3", "SAE", "WPA3-SAE"):
        auth_type = "WPA3"
    elif auth_raw == "WEP":
        auth_type = "WEP"
    elif auth_raw in ("NOPASS", "OPEN", "NONE", ""):
        auth_type = "nopass"
        password = ""
    else:
        auth_type = auth_raw

    is_hidden = hidden_raw in ("true", "1", "yes")

    return WiFiCredentials(
        ssid=ssid,
        auth_type=auth_type,
        password=password,
        is_hidden=is_hidden,
        raw_payload=raw_clean,
    )
