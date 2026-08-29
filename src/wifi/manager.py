"""
Windows 11 WiFi Network Connection Manager
Handles native Windows WLANProfile registration, connection requests, interface state querying, and informative error handling.
"""
import logging
import os
import subprocess
import tempfile
import time
from dataclasses import dataclass
from typing import Optional, Tuple

from .profile_builder import generate_wlan_profile_xml

logger = logging.getLogger(__name__)


@dataclass
class ConnectionResult:
    success: bool
    message: str
    ssid: str = ""
    auth_type: str = ""


class WindowsWiFiManager:
    """Manages Windows 11 WiFi connections using native netsh commands and WLAN profile XMLs."""

    def __init__(self):
        self._check_wlan_service()

    def _check_wlan_service(self) -> bool:
        """Verify WLAN AutoConfig service is accessible."""
        try:
            res = subprocess.run(
                ["netsh", "wlan", "show", "interfaces"],
                capture_output=True,
                text=True,
                errors="replace",
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                timeout=5,
            )
            return res.returncode == 0
        except Exception as e:
            logger.warning(f"Failed to check WLAN interfaces: {e}")
            return False

    def get_current_connection(self) -> Tuple[bool, str]:
        """Check if currently connected to a WiFi network. Returns (is_connected, ssid)."""
        try:
            res = subprocess.run(
                ["netsh", "wlan", "show", "interfaces"],
                capture_output=True,
                text=True,
                errors="replace",
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                timeout=5,
            )
            output = res.stdout or ""
            is_connected = False
            current_ssid = ""

            for line in output.splitlines():
                line = line.strip()
                if line.startswith("State") and ":" in line:
                    state_val = line.split(":", 1)[1].strip()
                    if "connected" in state_val.lower():
                        is_connected = True
                elif line.startswith("SSID") and not line.startswith("BSSID") and ":" in line:
                    current_ssid = line.split(":", 1)[1].strip()

            if is_connected and current_ssid:
                return True, current_ssid
            return False, ""
        except Exception as e:
            logger.error(f"Error checking connection status: {e}")
            return False, ""

    def connect_network(
        self,
        ssid: str,
        password: str = "",
        auth_type: str = "WPA2",
        is_hidden: bool = False,
        timeout_seconds: int = 15,
        status_callback=None,
    ) -> ConnectionResult:
        """
        Create Windows WLAN profile and connect to the specified WiFi network.
        """
        clean_ssid = ssid.strip()
        if not clean_ssid:
            return ConnectionResult(success=False, message="SSID cannot be empty.", ssid=ssid)

        if status_callback:
            status_callback("Generating Windows WLAN Profile...")

        xml_content = generate_wlan_profile_xml(clean_ssid, password, auth_type, is_hidden)

        temp_xml_path = None
        try:
            # Write profile XML to temporary file
            with tempfile.NamedTemporaryFile("w", suffix=".xml", delete=False, encoding="utf-8") as f:
                f.write(xml_content)
                temp_xml_path = f.name

            if status_callback:
                status_callback(f"Adding network profile '{clean_ssid}'...")

            # Add profile using netsh
            add_res = subprocess.run(
                ["netsh", "wlan", "add", "profile", f"filename={temp_xml_path}", "user=all"],
                capture_output=True,
                text=True,
                errors="replace",
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                timeout=8,
            )

            if add_res.returncode != 0:
                raw_err = (add_res.stderr or "").strip() or (add_res.stdout or "").strip()
                logger.error(f"Failed to add profile: {raw_err}")
                return ConnectionResult(
                    success=False,
                    message=f"Failed to register WiFi profile for '{clean_ssid}': {raw_err or 'Invalid profile syntax.'}",
                    ssid=clean_ssid,
                    auth_type=auth_type,
                )

            if status_callback:
                status_callback(f"Connecting to '{clean_ssid}'...")

            # Initiate connection using Profile name
            conn_res = subprocess.run(
                ["netsh", "wlan", "connect", f"name={clean_ssid}"],
                capture_output=True,
                text=True,
                errors="replace",
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                timeout=8,
            )

            if conn_res.returncode != 0:
                raw_err = (conn_res.stderr or "").strip() or (conn_res.stdout or "").strip()
                logger.error(f"netsh wlan connect failed (code {conn_res.returncode}): {raw_err}")

                # Provide friendly, informative error messages for common Windows network failure modes
                if "not available to connect" in raw_err.lower() or "cannot find" in raw_err.lower():
                    err_msg = f"Network '{clean_ssid}' is out of range or not currently available."
                elif "service has not been started" in raw_err.lower() or "no wireless interface" in raw_err.lower():
                    err_msg = "WiFi is turned off or no wireless adapter was found."
                elif raw_err:
                    err_msg = f"Connection failed: {raw_err}"
                else:
                    err_msg = f"Network '{clean_ssid}' was not found. Please ensure the network is in range."

                return ConnectionResult(
                    success=False,
                    message=err_msg,
                    ssid=clean_ssid,
                    auth_type=auth_type,
                )

            # Poll for connection status
            start_time = time.time()
            while time.time() - start_time < timeout_seconds:
                connected, current_ssid = self.get_current_connection()
                if connected and (current_ssid.lower() == clean_ssid.lower()):
                    if status_callback:
                        status_callback(f"Successfully connected to '{clean_ssid}'!")
                    return ConnectionResult(
                        success=True,
                        message=f"Connected to '{clean_ssid}' successfully.",
                        ssid=clean_ssid,
                        auth_type=auth_type,
                    )
                time.sleep(1.0)
                if status_callback:
                    elapsed = int(time.time() - start_time)
                    status_callback(f"Waiting for connection... ({elapsed}s)")

            # Check one last time
            connected, current_ssid = self.get_current_connection()
            if connected and (current_ssid.lower() == clean_ssid.lower()):
                return ConnectionResult(
                    success=True,
                    message=f"Connected to '{clean_ssid}' successfully.",
                    ssid=clean_ssid,
                    auth_type=auth_type,
                )

            return ConnectionResult(
                success=False,
                message=f"Connection to '{clean_ssid}' timed out. Network is out of range or credentials do not match.",
                ssid=clean_ssid,
                auth_type=auth_type,
            )

        except subprocess.TimeoutExpired:
            return ConnectionResult(
                success=False,
                message=f"Network command timed out while attempting to connect to '{clean_ssid}'.",
                ssid=clean_ssid,
                auth_type=auth_type,
            )
        except Exception as e:
            logger.exception(f"Unexpected error connecting to {clean_ssid}: {e}")
            return ConnectionResult(
                success=False,
                message=f"Connection error: {str(e)}",
                ssid=clean_ssid,
                auth_type=auth_type,
            )
        finally:
            if temp_xml_path and os.path.exists(temp_xml_path):
                try:
                    os.remove(temp_xml_path)
                except Exception:
                    pass

    def delete_profile(self, ssid: str) -> bool:
        """Remove a network profile from Windows."""
        try:
            res = subprocess.run(
                ["netsh", "wlan", "delete", "profile", f"name={ssid}"],
                capture_output=True,
                text=True,
                errors="replace",
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                timeout=5,
            )
            return res.returncode == 0
        except Exception as e:
            logger.warning(f"Error deleting profile '{ssid}': {e}")
            return False
