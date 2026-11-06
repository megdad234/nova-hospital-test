"""NSSM commercial service upgrade contract."""
from pathlib import Path
import unittest

SCRIPT = Path(__file__).resolve().parent / "windows" / "install-commercial-service.ps1"

class CommercialServiceUpgradeContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SCRIPT.read_text(encoding="utf-8")

    def test_nssm_runtime_is_bundled_and_isolated(self):
        for expected in ("nssm.exe", "runtime/python.exe", "pharmacy/server_host.py",
                         "NOVACommercialPharmacyServer", "SERVICE_AUTO_START",
                         "AppDirectory", "AppExit Default Restart"):
            self.assertIn(expected, self.source)

    def test_previous_service_migration_is_explicit(self):
        self.assertIn("Get-CimInstance Win32_Service", self.source)
        self.assertIn("if ($config.PathName -notmatch 'nssm.exe')", self.source)
        self.assertIn("Old service pending deletion", self.source)

    def test_firewall_is_private_and_port_independent(self):
        self.assertIn("New-NetFirewallRule", self.source)
        self.assertIn("-Profile Private", self.source)
        self.assertIn("$Port -eq 8765", self.source)
        self.assertIn("$Port -eq 10080", self.source)

    def test_http_readiness_and_hospital_isolation(self):
        self.assertIn("Invoke-WebRequest", self.source)
        self.assertIn("COMMERCIAL_NSSM_HTTP_READY", self.source)
        self.assertNotIn("NOVA_Hospital_Server", self.source)

if __name__ == "__main__":
    unittest.main()
