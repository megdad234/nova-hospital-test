"""Static contract for complete Windows runtime payload validation."""
from pathlib import Path
import unittest

SCRIPT = Path(__file__).parent / "windows" / "verify-runtime-bundle.ps1"

class WindowsRuntimeBundleTests(unittest.TestCase):
    def test_bundle_requires_actual_pharmacy_and_python(self):
        source = SCRIPT.read_text(encoding="utf-8")
        for required in ("runtime/python.exe", "pharmacy/app.py", "pharmacy/server_host.py",
                         "pharmacy/static/index.html", "NOVACommercialPharmacyServer.exe"):
            self.assertIn(required, source)
        self.assertIn("COMMERCIAL_RUNTIME_BUNDLE_STRUCTURE_PASSED_NOT_FULLY_TESTED", source)
        self.assertNotIn("Start-Service", source)
        self.assertNotIn("sc.exe create", source)

if __name__ == "__main__":
    unittest.main()
