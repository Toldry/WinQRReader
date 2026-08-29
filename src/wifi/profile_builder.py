"""
Windows 11 Native WLAN Profile XML Generator
Conforms to Microsoft WLANProfile Schema v1
"""
import xml.sax.saxutils as saxutils
from typing import Tuple


def escape_xml(text: str) -> str:
    """Safely escape XML characters."""
    return saxutils.escape(text, entities={'"': "&quot;", "'": "&apos;"})


def string_to_hex(text: str) -> str:
    """Convert UTF-8 string to uppercase hex representation for SSID element."""
    return text.encode("utf-8").hex().upper()


def generate_wlan_profile_xml(ssid: str, password: str = "", auth_type: str = "WPA2", is_hidden: bool = False) -> str:
    """
    Generate valid Windows WLAN XML profile content.
    Supports WPA2, WPA3, WEP, and Open networks.
    """
    clean_ssid = ssid.strip()
    hex_ssid = string_to_hex(clean_ssid)
    escaped_ssid = escape_xml(clean_ssid)
    escaped_pass = escape_xml(password)
    non_broadcast = "true" if is_hidden else "false"

    auth_upper = auth_type.upper()

    if auth_upper in ("WPA3", "SAE", "WPA3-SAE"):
        # WPA3-Personal (SAE)
        security_block = f"""        <security>
            <authEncryption>
                <authentication>WPA3SAE</authentication>
                <encryption>AES</encryption>
                <useOneX>false</useOneX>
            </authEncryption>
            <sharedKey>
                <keyType>passPhrase</keyType>
                <protected>false</protected>
                <keyMaterial>{escaped_pass}</keyMaterial>
            </sharedKey>
        </security>"""
    elif auth_upper == "WEP":
        # Legacy WEP
        security_block = f"""        <security>
            <authEncryption>
                <authentication>open</authentication>
                <encryption>WEP</encryption>
                <useOneX>false</useOneX>
            </authEncryption>
            <sharedKey>
                <keyType>networkKey</keyType>
                <protected>false</protected>
                <keyMaterial>{escaped_pass}</keyMaterial>
            </sharedKey>
        </security>"""
    elif auth_upper in ("NOPASS", "OPEN", "NONE"):
        # Open Network without encryption
        security_block = """        <security>
            <authEncryption>
                <authentication>open</authentication>
                <encryption>none</encryption>
                <useOneX>false</useOneX>
            </authEncryption>
        </security>"""
    else:
        # Standard WPA2-Personal (AES) - default for almost all modern WiFi
        security_block = f"""        <security>
            <authEncryption>
                <authentication>WPA2PSK</authentication>
                <encryption>AES</encryption>
                <useOneX>false</useOneX>
            </authEncryption>
            <sharedKey>
                <keyType>passPhrase</keyType>
                <protected>false</protected>
                <keyMaterial>{escaped_pass}</keyMaterial>
            </sharedKey>
        </security>"""

    xml_template = f"""<?xml version="1.0"?>
<WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">
    <name>{escaped_ssid}</name>
    <SSIDConfig>
        <SSID>
            <hex>{hex_ssid}</hex>
            <name>{escaped_ssid}</name>
        </SSID>
        <nonBroadcast>{non_broadcast}</nonBroadcast>
    </SSIDConfig>
    <connectionType>ESS</connectionType>
    <connectionMode>auto</connectionMode>
    <MSM>
{security_block}
    </MSM>
</WLANProfile>
"""
    return xml_template
