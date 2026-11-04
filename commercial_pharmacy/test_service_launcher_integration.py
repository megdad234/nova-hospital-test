"""Validate Windows service source launcher isolation without invoking SCM."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from commercial_pharmacy.launch import prepare

class ServiceLauncherIntegrationTests(unittest.TestCase):
    def test_preflight_refuses_hospital_data_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pharmacy = root / "pharmacy"
            pharmacy.mkdir()
            (pharmacy / "app.py").write_text("DATA = 'NOVA_COMMERCIAL_DATA_DIR'\nDB = 'commercial_pharmacy.sqlite3'\n")
            (pharmacy / "server_host.py").write_text("NOVA_COMMERCIAL_PORT = 18763\n")
            hospital = root / "hospital"
            hospital.mkdir()
            with self.assertRaises(ValueError):
                prepare(root, hospital, 18763, [hospital])

if __name__ == "__main__":
    unittest.main()
