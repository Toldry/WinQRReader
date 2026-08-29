"""
Unit Tests for Windows WLAN Profile XML Generator
"""
import unittest
import xml.etree.ElementTree as ET
from src.wifi.profile_builder import escape_xml, generate_wlan_profile_xml, string_to_hex


class TestWiFiProfileBuilder(unittest.TestCase):

    def test_wpa2_profile_xml_structure(self):
        xml_str = generate_wlan_profile_xml(ssid="TestNetwork", password="MySecretPassword123", auth_type="WPA2")
        self.assertIn("<name>TestNetwork</name>", xml_str)
        self.assertIn("<authentication>WPA2PSK</authentication>", xml_str)
        self.assertIn("<encryption>AES</encryption>", xml_str)
        self.assertIn("<keyMaterial>MySecretPassword123</keyMaterial>", xml_str)
        self.assertIn("<nonBroadcast>false</nonBroadcast>", xml_str)

        # Validate that it parses as well-formed XML
        root = ET.fromstring(xml_str)
        self.assertIsNotNone(root)

    def test_wpa3_profile_xml_structure(self):
        xml_str = generate_wlan_profile_xml(ssid="WPA3_Net", password="WPA3_Password", auth_type="WPA3")
        self.assertIn("<authentication>WPA3SAE</authentication>", xml_str)
        self.assertIn("<encryption>AES</encryption>", xml_str)
        root = ET.fromstring(xml_str)
        self.assertIsNotNone(root)

    def test_open_profile_xml_structure(self):
        xml_str = generate_wlan_profile_xml(ssid="OpenWiFi", auth_type="nopass")
        self.assertIn("<authentication>open</authentication>", xml_str)
        self.assertIn("<encryption>none</encryption>", xml_str)
        self.assertNotIn("sharedKey", xml_str)
        root = ET.fromstring(xml_str)
        self.assertIsNotNone(root)

    def test_wep_profile_xml_structure(self):
        xml_str = generate_wlan_profile_xml(ssid="WEP_Net", password="1234567890", auth_type="WEP")
        self.assertIn("<authentication>open</authentication>", xml_str)
        self.assertIn("<encryption>WEP</encryption>", xml_str)
        self.assertIn("<keyType>networkKey</keyType>", xml_str)
        root = ET.fromstring(xml_str)
        self.assertIsNotNone(root)

    def test_hidden_ssid_flag(self):
        xml_str = generate_wlan_profile_xml(ssid="HiddenNet", password="pass", is_hidden=True)
        self.assertIn("<nonBroadcast>true</nonBroadcast>", xml_str)
        root = ET.fromstring(xml_str)
        self.assertIsNotNone(root)

    def test_special_characters_xml_escaping(self):
        # Special XML characters: &, <, >, ", '
        ssid = "Bob & Alice's <Cafe> \"WiFi\""
        password = "P&ss<w>ord'\""
        xml_str = generate_wlan_profile_xml(ssid=ssid, password=password, auth_type="WPA2")

        # Must parse as valid XML without syntax errors
        root = ET.fromstring(xml_str)
        self.assertIsNotNone(root)

    def test_hex_conversion(self):
        self.assertEqual(string_to_hex("WiFi"), "57694669")


if __name__ == "__main__":
    unittest.main()
