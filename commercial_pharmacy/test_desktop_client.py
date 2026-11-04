"""LAN client launch URL tests."""
import unittest
from commercial_pharmacy.desktop_client import pharmacy_url

class DesktopClientTests(unittest.TestCase):
    def test_local_and_lan_hosts(self):
        self.assertEqual(pharmacy_url(), "http://127.0.0.1:18763/")
        self.assertEqual(pharmacy_url("192.168.1.10"), "http://192.168.1.10:18763/")
        self.assertEqual(pharmacy_url("pharmacy-server"), "http://pharmacy-server:18763/")

    def test_refuse_invalid_or_reserved_addresses(self):
        for host in ("", "http://evil", "user@host", "x/path", "host:123", "host?x", "::1", "999.999.999.999", "123.456"):
            with self.subTest(host=host), self.assertRaises(ValueError):
                pharmacy_url(host)
        for port in (0, 80, 10080, 65536):
            with self.subTest(port=port), self.assertRaises(ValueError):
                pharmacy_url("127.0.0.1", port)

if __name__ == "__main__":
    unittest.main()
