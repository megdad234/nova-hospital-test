"""Service-state parsing regressions; no Windows service is touched."""
import unittest
from unittest.mock import patch
from types import SimpleNamespace
from commercial_pharmacy.windows_service_state import require_stopped_service

class ServiceStateTests(unittest.TestCase):
    @patch("commercial_pharmacy.windows_service_state.sys.platform", "win32")
    @patch("commercial_pharmacy.windows_service_state.subprocess.run")
    def test_stopped_service(self, run):
        run.return_value = SimpleNamespace(returncode=0, stdout="STATE : 1 STOPPED", stderr="")
        self.assertEqual(require_stopped_service()["state"], "stopped")
        self.assertEqual(run.call_args.args[0][-1], "NOVACommercialPharmacyServer")

    @patch("commercial_pharmacy.windows_service_state.sys.platform", "win32")
    @patch("commercial_pharmacy.windows_service_state.subprocess.run")
    def test_running_service_blocks_restore(self, run):
        run.return_value = SimpleNamespace(returncode=0, stdout="STATE : 4 RUNNING", stderr="")
        with self.assertRaises(RuntimeError):
            require_stopped_service()

    @patch("commercial_pharmacy.windows_service_state.sys.platform", "win32")
    @patch("commercial_pharmacy.windows_service_state.subprocess.run")
    def test_missing_service(self, run):
        run.return_value = SimpleNamespace(returncode=1060, stdout="", stderr="OpenService FAILED 1060")
        self.assertEqual(require_stopped_service()["state"], "not_installed")

    @patch("commercial_pharmacy.windows_service_state.sys.platform", "win32")
    @patch("commercial_pharmacy.windows_service_state.subprocess.run")
    def test_unknown_failure_blocks_restore(self, run):
        run.return_value = SimpleNamespace(returncode=5, stdout="", stderr="Access denied")
        with self.assertRaises(RuntimeError):
            require_stopped_service()

if __name__ == "__main__":
    unittest.main()
