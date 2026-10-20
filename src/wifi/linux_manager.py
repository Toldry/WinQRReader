"""
Linux (Ubuntu) WiFi Network Connection Manager
Uses NetworkManager's `nmcli` CLI to register connection profiles, activate them,
and query the current interface state. Mirrors the WindowsWiFiManager interface.
"""
import logging
import os
import subprocess
import time
from typing import List, Optional, Tuple

from .manager import ConnectionResult

logger = logging.getLogger(__name__)

# WEP keys of these lengths are raw keys (ASCII 5/13 or hex 10/26); anything else is a passphrase
_WEP_RAW_KEY_LENGTHS = (5, 10, 13, 26)


def split_terse_fields(line: str) -> List[str]:
    """
    Split one line of `nmcli -t` output into unescaped field values.
    Terse mode separates fields with ':' and escapes literal ':' and '\\' with '\\'.
    """
    fields = []
    current = []
    index = 0
    while index < len(line):
        char = line[index]
        if char == "\\" and index + 1 < len(line):
            current.append(line[index + 1])
            index += 2
            continue
        if char == ":":
            fields.append("".join(current))
            current = []
        else:
            current.append(char)
        index += 1
    fields.append("".join(current))
    return fields


def build_security_args(auth_type: str, password: str) -> List[str]:
    """Translate a WiFi QR auth type into `nmcli connection add` security properties."""
    auth_upper = auth_type.upper()

    if auth_upper in ("NOPASS", "OPEN", "NONE"):
        return []
    if auth_upper in ("WPA3", "SAE", "WPA3-SAE"):
        return ["wifi-sec.key-mgmt", "sae", "wifi-sec.psk", password]
    if auth_upper == "WEP":
        # NM_WEP_KEY_TYPE: 1 = raw key, 2 = passphrase
        wep_key_type = "1" if len(password) in _WEP_RAW_KEY_LENGTHS else "2"
        return [
            "wifi-sec.key-mgmt", "none",
            "wifi-sec.wep-key-type", wep_key_type,
            "wifi-sec.wep-tx-keyidx", "0",
            "wifi-sec.wep-key0", password,
        ]
    # Standard WPA/WPA2-Personal - default for almost all modern WiFi
    return ["wifi-sec.key-mgmt", "wpa-psk", "wifi-sec.psk", password]


class LinuxWiFiManager:
    """Manages Linux WiFi connections through NetworkManager (`nmcli`)."""

    def __init__(self):
        self._check_network_manager()

    def _run_nmcli(self, args: List[str], timeout: float) -> subprocess.CompletedProcess:
        # Force untranslated output so error strings can be matched reliably
        return subprocess.run(
            ["nmcli", *args],
            capture_output=True,
            text=True,
            errors="replace",
            env={**os.environ, "LC_ALL": "C"},
            timeout=timeout,
        )

    def _check_network_manager(self) -> bool:
        """Verify NetworkManager is installed and running."""
        try:
            res = self._run_nmcli(["-t", "-f", "RUNNING", "general"], timeout=5)
            success = res.returncode == 0 and res.stdout.strip() == "running"
            logger.info(f"NetworkManager status check: {'OK' if success else 'Unavailable'}")
            return success
        except FileNotFoundError:
            logger.warning("nmcli not found. NetworkManager is required for WiFi connections on Linux.")
            return False
        except Exception as e:
            logger.warning(f"Failed to check NetworkManager status: {e}")
            return False

    def _find_wifi_device(self) -> Optional[str]:
        """Return the name of the first WiFi interface managed by NetworkManager."""
        res = self._run_nmcli(["-t", "-f", "DEVICE,TYPE,STATE", "device"], timeout=5)
        for line in (res.stdout or "").splitlines():
            fields = split_terse_fields(line)
            if len(fields) >= 3 and fields[1] == "wifi" and fields[2] != "unmanaged":
                return fields[0]
        return None

    def get_current_connection(self) -> Tuple[bool, str]:
        """Check if currently connected to a WiFi network. Returns (is_connected, ssid)."""
        try:
            res = self._run_nmcli(
                ["-t", "-f", "ACTIVE,SSID", "device", "wifi", "list", "--rescan", "no"],
                timeout=5,
            )
            for line in (res.stdout or "").splitlines():
                fields = split_terse_fields(line)
                if len(fields) >= 2 and fields[0] == "yes" and fields[1]:
                    logger.debug(f"Current WiFi status: Connected to '{fields[1]}'")
                    return True, fields[1]
            logger.debug("Current WiFi status: Not connected")
            return False, ""
        except FileNotFoundError:
            logger.debug("Current WiFi status: Unknown (nmcli not installed)")
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
        Create a NetworkManager connection profile and activate it.
        """
        clean_ssid = ssid.strip()
        if not clean_ssid:
            logger.error("connect_network called with empty SSID.")
            return ConnectionResult(success=False, message="SSID cannot be empty.", ssid=ssid)

        logger.info(
            f"Initiating WiFi connection: SSID='{clean_ssid}', Auth='{auth_type}', "
            f"Hidden={is_hidden}, HasPassword={bool(password)}"
        )

        def result(success: bool, message: str) -> ConnectionResult:
            return ConnectionResult(success=success, message=message, ssid=clean_ssid, auth_type=auth_type)

        try:
            wifi_device = self._find_wifi_device()
            if wifi_device is None:
                return result(False, "WiFi is turned off or no wireless adapter was found.")
            logger.debug(f"Using WiFi device '{wifi_device}'.")

            if status_callback:
                status_callback(f"Adding network profile '{clean_ssid}'...")

            # Replace any existing profile of the same name, like `netsh wlan add profile` does
            self._run_nmcli(["connection", "delete", "id", clean_ssid], timeout=8)

            # Secrets are passed as arguments, briefly visible to local users via the process
            # list; comparable to the plaintext profile XML written on Windows
            add_args = [
                "connection", "add",
                "type", "wifi",
                "con-name", clean_ssid,
                "ifname", wifi_device,
                "ssid", clean_ssid,
                "connection.autoconnect", "yes",
                "wifi.hidden", "yes" if is_hidden else "no",
                *build_security_args(auth_type, password),
            ]
            logger.info(f"Adding NetworkManager profile '{clean_ssid}' via nmcli...")
            add_res = self._run_nmcli(add_args, timeout=8)

            if add_res.returncode != 0:
                raw_err = (add_res.stderr or "").strip() or (add_res.stdout or "").strip()
                logger.error(f"Failed to add profile: {raw_err}")
                return result(
                    False,
                    f"Failed to register WiFi profile for '{clean_ssid}': {raw_err or 'Invalid profile settings.'}",
                )

            logger.info(f"NetworkManager profile '{clean_ssid}' added successfully.")

            if status_callback:
                status_callback(f"Connecting to '{clean_ssid}'...")

            # `connection up` blocks until the connection activates or fails
            logger.info(f"Connecting to '{clean_ssid}' via nmcli connection up...")
            conn_res = self._run_nmcli(
                ["--wait", str(timeout_seconds), "connection", "up", "id", clean_ssid],
                timeout=timeout_seconds + 5,
            )

            if conn_res.returncode != 0:
                raw_err = (conn_res.stderr or "").strip() or (conn_res.stdout or "").strip()
                logger.error(f"nmcli connection up failed (code {conn_res.returncode}): {raw_err}")
                lowered = raw_err.lower()

                if "no network with ssid" in lowered or "not found" in lowered:
                    err_msg = f"Network '{clean_ssid}' is out of range or not currently available."
                elif "secrets were required" in lowered or "802.1x supplicant" in lowered:
                    err_msg = f"The password for '{clean_ssid}' was rejected."
                elif "timeout" in lowered:
                    err_msg = (
                        f"Connection to '{clean_ssid}' timed out. "
                        "Network is out of range or credentials do not match."
                    )
                elif "not authorized" in lowered or "insufficient privileges" in lowered:
                    err_msg = "Not authorized to change network settings. Check your PolicyKit permissions."
                elif raw_err:
                    err_msg = f"Connection failed: {raw_err}"
                else:
                    err_msg = f"Network '{clean_ssid}' was not found. Please ensure the network is in range."
                return result(False, err_msg)

            # Confirm the interface actually reports the new SSID
            deadline = time.time() + 3.0
            while True:
                connected, current_ssid = self.get_current_connection()
                if connected and current_ssid.lower() == clean_ssid.lower():
                    break
                if time.time() >= deadline:
                    logger.warning("nmcli reported success but the active SSID could not be confirmed.")
                    break
                time.sleep(0.5)

            if status_callback:
                status_callback(f"Successfully connected to '{clean_ssid}'!")
            return result(True, f"Connected to '{clean_ssid}' successfully.")

        except FileNotFoundError:
            logger.error("nmcli executable not found.")
            return result(False, "NetworkManager (nmcli) is not installed. Install the 'network-manager' package.")
        except subprocess.TimeoutExpired:
            return result(False, f"Network command timed out while attempting to connect to '{clean_ssid}'.")
        except Exception as e:
            logger.exception(f"Unexpected error connecting to {clean_ssid}: {e}")
            return result(False, f"Connection error: {str(e)}")

    def delete_profile(self, ssid: str) -> bool:
        """Remove a network profile from NetworkManager."""
        try:
            res = self._run_nmcli(["connection", "delete", "id", ssid], timeout=5)
            return res.returncode == 0
        except Exception as e:
            logger.warning(f"Error deleting profile '{ssid}': {e}")
            return False
