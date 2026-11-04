"""Assembly contract: no hospital reference copying, no auto-service registration."""
from pathlib import Path
import unittest

SOURCE = (Path(__file__).parent / "windows" / "assemble-standalone-payload.ps1").read_text(encoding="utf-8")

class AssemblyContractTests(unittest.TestCase):
    def test_explicit_runtime_and_launchers(self):
        for required in ("PythonRuntimeDirectory", "LaunchersDirectory", "SourceStage",
                         "HOSPITAL_COUPLING_BLOCKERS.json", "standalone_network_and_schema_clear",
                         "check-runtime-payload.ps1", "COMMERCIAL_RUNTIME_PREFLIGHT.json", "preflight_passed"):
            self.assertIn(required, SOURCE)

    def test_never_copies_hospital_reference_or_registers_service(self):
        self.assertNotIn("Copy-Item -LiteralPath (Join-Path $source 'hospital_reference')", SOURCE)
        self.assertNotIn("sc.exe create", SOURCE)
        self.assertNotIn("Start-Service", SOURCE)
        self.assertIn("NOT_RELEASE_APPROVED", SOURCE)

if __name__ == "__main__":
    unittest.main()
