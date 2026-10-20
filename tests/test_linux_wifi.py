"""
Unit Tests for the Linux NetworkManager (nmcli) WiFi Backend
All nmcli invocations are mocked, so these tests run on any OS.
"""
import subprocess
import unittest
from unittest.mock import patch

from src.wifi.linux_manager import LinuxWiFiManager, build_security_args, split_terse_fields
from src.wifi.manager import WindowsWiFiManager, create_wifi_manager


def completed(stdout: str = "", returncode: int = 0, stderr: str = "") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


class FakeNmcli:
    """Records nmcli calls and answers them based on the subcommand."""

    def __init__(self, up_result: subprocess.CompletedProcess = None, devices: str = "wlp2s0:wifi:disconnected\n"):
        self.calls = []
        self.up_result = up_result or completed("Connection successfully activated")
        self.devices = devices
        self.active_ssid = ""

    def __call__(self, command, **kwargs):
        args = command[1:]
        self.calls.append(args)
        if args[:2] == ["-t", "-f"] and args[2] == "RUNNING":
            return completed("running\n")
        if args[:2] == ["-t", "-f"] and args[2] == "DEVICE,TYPE,STATE":
            return completed(self.devices)
        if args[:2] == ["-t", "-f"] and args[2] == "ACTIVE,SSID":
            if self.active_ssid:
                return completed(f"no:Neighbor\nyes:{self.active_ssid}\n")
            return completed("no:Neighbor\n")
        if "up" in args:
            if self.up_result.returncode == 0:
                self.active_ssid = args[-1].replace(":", "\\:")
            return self.up_result
        return completed()

    def find_call(self, *subcommand):
        for call in self.calls:
            if call[: len(subcommand)] == list(subcommand):
                return call
        return None


class TestTerseParsing(unittest.TestCase):
    def test_split_plain_fields(self):
        self.assertEqual(split_terse_fields("yes:HomeNet"), ["yes", "HomeNet"])

    def test_split_escaped_colon_and_backslash(self):
        self.assertEqual(split_terse_fields(r"yes:Cafe\:5G\\Guest"), ["yes", r"Cafe:5G\Guest"])

    def test_split_empty_ssid(self):
        self.assertEqual(split_terse_fields("no:"), ["no", ""])


class TestSecurityArgs(unittest.TestCase):
    def test_wpa2(self):
        self.assertEqual(
            build_security_args("WPA", "secret123"),
            ["wifi-sec.key-mgmt", "wpa-psk", "wifi-sec.psk", "secret123"],
        )

    def test_wpa3(self):
        self.assertEqual(build_security_args("SAE", "secret123")[:2], ["wifi-sec.key-mgmt", "sae"])

    def test_open(self):
        self.assertEqual(build_security_args("nopass", ""), [])

    def test_wep_raw_key_and_passphrase(self):
        raw_key_args = build_security_args("WEP", "abcde")
        self.assertIn("wifi-sec.wep-key0", raw_key_args)
        self.assertEqual(raw_key_args[raw_key_args.index("wifi-sec.wep-key-type") + 1], "1")
        passphrase_args = build_security_args("WEP", "a longer passphrase")
        self.assertEqual(passphrase_args[passphrase_args.index("wifi-sec.wep-key-type") + 1], "2")


class TestLinuxWiFiManager(unittest.TestCase):
    def test_connect_success_builds_profile_and_activates(self):
        fake_nmcli = FakeNmcli()
        with patch("src.wifi.linux_manager.subprocess.run", side_effect=fake_nmcli):
            manager = LinuxWiFiManager()
            result = manager.connect_network("Cafe:5G", "secret123", "WPA2", is_hidden=True)

        self.assertTrue(result.success, result.message)
        add_call = fake_nmcli.find_call("connection", "add")
        self.assertIsNotNone(add_call)
        self.assertEqual(add_call[add_call.index("ssid") + 1], "Cafe:5G")
        self.assertEqual(add_call[add_call.index("ifname") + 1], "wlp2s0")
        self.assertEqual(add_call[add_call.index("wifi.hidden") + 1], "yes")
        self.assertEqual(add_call[add_call.index("wifi-sec.psk") + 1], "secret123")
        self.assertIsNotNone(fake_nmcli.find_call("--wait", "15", "connection", "up", "id", "Cafe:5G"))

    def test_connect_without_wifi_adapter(self):
        fake_nmcli = FakeNmcli(devices="enp3s0:ethernet:connected\nlo:loopback:unmanaged\n")
        with patch("src.wifi.linux_manager.subprocess.run", side_effect=fake_nmcli):
            result = LinuxWiFiManager().connect_network("HomeNet", "secret123")

        self.assertFalse(result.success)
        self.assertIn("no wireless adapter", result.message)
        self.assertIsNone(fake_nmcli.find_call("connection", "add"))

    def test_connect_out_of_range(self):
        up_failure = completed(
            returncode=10,
            stderr="Error: Connection activation failed: No network with SSID 'HomeNet' found.",
        )
        fake_nmcli = FakeNmcli(up_result=up_failure)
        with patch("src.wifi.linux_manager.subprocess.run", side_effect=fake_nmcli):
            result = LinuxWiFiManager().connect_network("HomeNet", "secret123")

        self.assertFalse(result.success)
        self.assertIn("out of range", result.message)

    def test_connect_wrong_password(self):
        up_failure = completed(
            returncode=4,
            stderr="Error: Connection activation failed: Secrets were required, but not provided.",
        )
        fake_nmcli = FakeNmcli(up_result=up_failure)
        with patch("src.wifi.linux_manager.subprocess.run", side_effect=fake_nmcli):
            result = LinuxWiFiManager().connect_network("HomeNet", "wrong")

        self.assertFalse(result.success)
        self.assertIn("password", result.message)

    def test_nmcli_missing(self):
        with patch("src.wifi.linux_manager.subprocess.run", side_effect=FileNotFoundError("nmcli")):
            manager = LinuxWiFiManager()
            self.assertEqual(manager.get_current_connection(), (False, ""))
            result = manager.connect_network("HomeNet", "secret123")

        self.assertFalse(result.success)
        self.assertIn("NetworkManager", result.message)

    def test_get_current_connection_unescapes_ssid(self):
        fake_nmcli = FakeNmcli()
        fake_nmcli.active_ssid = r"Cafe\:5G"
        with patch("src.wifi.linux_manager.subprocess.run", side_effect=fake_nmcli):
            self.assertEqual(LinuxWiFiManager().get_current_connection(), (True, "Cafe:5G"))


class TestWiFiManagerFactory(unittest.TestCase):
    def test_linux_platform_selects_nmcli_backend(self):
        with patch("src.wifi.manager.sys.platform", "linux"), \
                patch("src.wifi.linux_manager.subprocess.run", side_effect=FakeNmcli()):
            self.assertIsInstance(create_wifi_manager(), LinuxWiFiManager)

    def test_windows_platform_selects_netsh_backend(self):
        with patch("src.wifi.manager.sys.platform", "win32"), \
                patch("src.wifi.manager.subprocess.run", return_value=completed()):
            self.assertIsInstance(create_wifi_manager(), WindowsWiFiManager)


if __name__ == "__main__":
    unittest.main()
