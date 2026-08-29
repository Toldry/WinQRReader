"""
Unit Tests for WiFi QR Code Schema Parser
"""
import unittest
from src.qr.parser import WiFiCredentials, is_wifi_qr, parse_wifi_qr, unescape_wifi_string


class TestWiFiQRParser(unittest.TestCase):

    def test_standard_wpa2(self):
        qr_text = "WIFI:T:WPA;S:HomeNetwork;P:SuperSecret123;H:false;;"
        self.assertTrue(is_wifi_qr(qr_text))
        creds = parse_wifi_qr(qr_text)
        self.assertIsNotNone(creds)
        self.assertEqual(creds.ssid, "HomeNetwork")
        self.assertEqual(creds.auth_type, "WPA2")
        self.assertEqual(creds.password, "SuperSecret123")
        self.assertFalse(creds.is_hidden)
        self.assertEqual(creds.display_auth, "WPA2-Personal")
        self.assertTrue(creds.requires_password)

    def test_wpa3_sae(self):
        qr_text = "WIFI:T:WPA3;S:NextGenWiFi;P:Wpa3Password99;;"
        creds = parse_wifi_qr(qr_text)
        self.assertIsNotNone(creds)
        self.assertEqual(creds.ssid, "NextGenWiFi")
        self.assertEqual(creds.auth_type, "WPA3")
        self.assertEqual(creds.password, "Wpa3Password99")
        self.assertEqual(creds.display_auth, "WPA3-Personal")

    def test_open_network(self):
        qr_text = "WIFI:T:nopass;S:Airport_Guest;;"
        creds = parse_wifi_qr(qr_text)
        self.assertIsNotNone(creds)
        self.assertEqual(creds.ssid, "Airport_Guest")
        self.assertEqual(creds.auth_type, "nopass")
        self.assertEqual(creds.password, "")
        self.assertEqual(creds.display_auth, "Open (No Password)")
        self.assertFalse(creds.requires_password)

    def test_open_network_empty_type(self):
        qr_text = "WIFI:S:CafeWiFi;P:;;"
        creds = parse_wifi_qr(qr_text)
        self.assertIsNotNone(creds)
        self.assertEqual(creds.ssid, "CafeWiFi")

    def test_wep_network(self):
        qr_text = "WIFI:T:WEP;S:OldRouter;P:1234567890;;"
        creds = parse_wifi_qr(qr_text)
        self.assertIsNotNone(creds)
        self.assertEqual(creds.ssid, "OldRouter")
        self.assertEqual(creds.auth_type, "WEP")
        self.assertEqual(creds.password, "1234567890")
        self.assertEqual(creds.display_auth, "WEP")

    def test_hidden_ssid(self):
        qr_text = "WIFI:T:WPA;S:StealthNet;P:pass;H:true;;"
        creds = parse_wifi_qr(qr_text)
        self.assertIsNotNone(creds)
        self.assertTrue(creds.is_hidden)

        qr_text_num = "WIFI:T:WPA;S:StealthNet2;P:pass;H:1;;"
        creds_num = parse_wifi_qr(qr_text_num)
        self.assertIsNotNone(creds_num)
        self.assertTrue(creds_num.is_hidden)

    def test_escaped_characters(self):
        # Escaped semicolon and colon: SSID = "My;Special:Net", Pass = "P\@ss;w:ord\!"
        qr_text = r"WIFI:T:WPA;S:My\;Special\:Net;P:P\@ss\;w\:ord\\!;;"
        creds = parse_wifi_qr(qr_text)
        self.assertIsNotNone(creds)
        self.assertEqual(creds.ssid, "My;Special:Net")
        self.assertEqual(creds.password, r"P\@ss;w:ord\!")

    def test_reversed_tag_order(self):
        qr_text = "WIFI:S:ReverseOrder;P:somepass;T:WPA;;"
        creds = parse_wifi_qr(qr_text)
        self.assertIsNotNone(creds)
        self.assertEqual(creds.ssid, "ReverseOrder")
        self.assertEqual(creds.password, "somepass")
        self.assertEqual(creds.auth_type, "WPA2")

    def test_invalid_strings(self):
        self.assertFalse(is_wifi_qr("https://google.com"))
        self.assertIsNone(parse_wifi_qr("https://google.com"))
        self.assertIsNone(parse_wifi_qr("WIFI:"))
        self.assertIsNone(parse_wifi_qr(""))
        self.assertIsNone(parse_wifi_qr(None))


if __name__ == "__main__":
    unittest.main()
