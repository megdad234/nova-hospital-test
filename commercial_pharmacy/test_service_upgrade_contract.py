"""Static regression checks for non-destructive commercial service upgrades."""
from pathlib import Path
import unittest

SCRIPT = Path(__file__).resolve().parent / "windows" / "install-commercial-service.ps1"

class CommercialServiceUpgradeContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SCRIPT.read_text(encoding="utf-8")

    def test_existing_service_is_reused_not_deleted(self):
        section = self.source.split("if ($existingService) {", 1)[1].split(
            '$fullExe =', 1)[0]
        self.assertIn("COMMERCIAL_PHARMACY_EXISTING_SERVICE_REUSED", section)
        self.assertNotIn("sc.exe delete", section)
        self.assertNotIn("Stop-Service", section)

    def test_existing_service_command_and_port_are_checked(self):
        self.assertIn('$expectedCommand', self.source)
        self.assertIn('$configuredExe.Trim() -ne $expectedCommand', self.source)

    def test_lan_rule_supported_during_upgrade(self):
        section = self.source.split("if ($existingService) {", 1)[1].split(
            "COMMERCIAL_PHARMACY_EXISTING_SERVICE_REUSED", 1)[0]
        self.assertIn("New-NetFirewallRule", section)
        self.assertIn("-Profile Private", section)

    def test_hospital_port_and_identity_are_not_used(self):
        self.assertIn("$Port -eq 10080", self.source)
        self.assertIn("'NOVACommercialPharmacyServer'", self.source)
        self.assertNotIn("sc.exe delete NOVAHospital", self.source)

if __name__ == "__main__":
    unittest.main()
