"""Commercial Windows packaging identity checks."""
from pathlib import Path
import unittest

WINDOWS = Path(__file__).resolve().parent / "windows"

class InstallerContractTests(unittest.TestCase):
    def test_installer_has_unique_commercial_identity(self):
        source = (WINDOWS / "commercial-pharmacy-installer.iss").read_text(encoding="utf-8")
        for expected in ("NOVA Commercial Pharmacy", "NOVACommercialPharmacyServer.exe",
                         "NOVACommercialPharmacy.exe", "18763", "PrivilegesRequired=admin",
                         "NOVA-Commercial-Pharmacy-UNVERIFIED"):
            self.assertIn(expected, source)
        self.assertNotIn("10080", source)
        self.assertIn("-OpenLanFirewall", source)
        self.assertIn("-RemoveLanFirewallRule", source)

    def test_installer_includes_actual_standalone_runtime_payload(self):
        source = (WINDOWS / "commercial-pharmacy-installer.iss").read_text(encoding="utf-8")
        for directory in (r"commercial\\runtime\\*", r"commercial\\pharmacy\\*",
                          r"commercial\\commercial_pharmacy\\*"):
            self.assertIn(directory.replace("\\\\", "\\"), source)
            self.assertEqual(source.count(directory.replace("\\\\", "\\")), 1)
        self.assertIn("recursesubdirs", source)

    def test_installer_registers_and_removes_dedicated_service(self):
        source = (WINDOWS / "commercial-pharmacy-installer.iss").read_text(encoding="utf-8")
        self.assertIn("\n[Run]\n", source)
        self.assertIn("\n[UninstallRun]\n", source)
        self.assertIn("install-commercial-service.ps1", source)
        self.assertIn("uninstall-commercial-service.ps1", source)
        self.assertIn("-ServiceAwareExecutableConfirmed", source)

    def test_payload_preflight_rejects_hospital_reference(self):
        source = (WINDOWS / "check-runtime-payload.ps1").read_text(encoding="utf-8")
        self.assertIn("hospital_reference", source)
        self.assertIn("pharmacy/static/index.html", source)
        self.assertIn("commercial_pharmacy.launch", source)

    def test_unverified_candidate_build_requires_acknowledgement(self):
        source = (WINDOWS / "build-installer-candidate.ps1").read_text(encoding="utf-8")
        self.assertIn("NOVA_COMMERCIAL_ALLOW_UNVERIFIED_INSTALLER", source)

    def test_service_requires_machine_level_runtime(self):
        source = (WINDOWS / "install-commercial-service.ps1").read_text(encoding="utf-8")
        self.assertIn("nssm.exe", source)
        self.assertIn("runtime/python.exe", source)
        self.assertIn("pharmacy/server_host.py", source)

    def test_installer_includes_isolated_runtime_payload(self):
        source = (WINDOWS / "commercial-pharmacy-installer.iss").read_text(encoding="utf-8")
        for required in ("dist\\commercial\\runtime\\*", "dist\\commercial\\pharmacy\\*",
                         "dist\\commercial\\commercial_pharmacy\\*"):
            self.assertIn(required, source)

    def test_runtime_payload_gate_requires_actual_pharmacy_and_python(self):
        script = (WINDOWS / "check-runtime-payload.ps1").read_text(encoding="utf-8")
        builder = (WINDOWS / "build-installer-candidate.ps1").read_text(encoding="utf-8")
        self.assertIn("check-runtime-payload.ps1", builder)
        for required in ("runtime/python.exe", "pharmacy/app.py", "pharmacy/server_host.py",
                         "pharmacy/static/app.js", "commercial_pharmacy/launch.py",
                         "--preflight-only", "PYTHONNOUSERSITE"):
            self.assertIn(required, script)

    def test_scheduled_backup_scripts_are_commercial_only(self):
        install = (WINDOWS / "install-backup-task.ps1").read_text(encoding="utf-8")
        uninstall = (WINDOWS / "uninstall-backup-task.ps1").read_text(encoding="utf-8")
        self.assertIn("backup-auto --retain", install)
        self.assertIn("NOVACommercialPharmacyDailyBackup", uninstall)
        self.assertNotIn("Stop-Service", uninstall)

if __name__ == "__main__":
    unittest.main()
