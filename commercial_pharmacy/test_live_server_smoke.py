import unittest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from commercial_pharmacy.live_server_smoke import run


class LiveServerSmokeTests(unittest.TestCase):
    @patch("commercial_pharmacy.live_server_smoke.run", side_effect=FileNotFoundError("server source missing"))
    def test_cli_writes_diagnostic_when_launch_fails(self, mocked_run):
        from commercial_pharmacy.live_server_smoke import main
        with tempfile.TemporaryDirectory() as folder:
            report = Path(folder) / "smoke.json"
            code = main(["--source-root", folder, "--data-dir", folder,
                         "--output", str(report)])
            self.assertEqual(code, 2)
            result = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(result["error"], "FileNotFoundError")
            self.assertFalse(result["http_responded"])

    def test_rejects_invalid_port_before_start(self):
        with self.assertRaises(ValueError):
            run(".", ".", port=0)

    @patch("commercial_pharmacy.live_server_smoke.check_port_free", return_value=False)
    @patch("commercial_pharmacy.live_server_smoke.subprocess.Popen")
    def test_occupied_port_never_starts_server(self, popen, free):
        result = run(".", ".", timeout=1)
        self.assertEqual(result["error"], "port_already_in_use")
        self.assertFalse(result["http_responded"])
        popen.assert_not_called()

    @patch("commercial_pharmacy.live_server_smoke.check_port_free", return_value=True)
    @patch("commercial_pharmacy.live_server_smoke.urlopen")
    @patch("commercial_pharmacy.live_server_smoke.subprocess.Popen")
    @patch("commercial_pharmacy.live_server_smoke.prepare")
    def test_non_success_http_does_not_pass(self, prepare, popen, urlopen, free):
        prepare.return_value = (["python", "server.py"], {}, ".")
        popen.return_value.poll.return_value = None
        response = MagicMock()
        response.status = 302
        urlopen.return_value.__enter__.return_value = response
        result = run(".", ".", timeout=1)
        self.assertFalse(result["http_responded"])
        self.assertEqual(result["error"], "unexpected_http_status")
        popen.return_value.terminate.assert_called_once()

    @patch("commercial_pharmacy.live_server_smoke.check_port_free", return_value=True)
    @patch("commercial_pharmacy.live_server_smoke.urlopen")
    @patch("commercial_pharmacy.live_server_smoke.subprocess.Popen")
    @patch("commercial_pharmacy.live_server_smoke.prepare")
    def test_http_success_is_not_database_acceptance(self, prepare, popen, urlopen, free):
        prepare.return_value = (["python", "server.py"], {}, ".")
        process = popen.return_value
        process.poll.return_value = None
        response = MagicMock()
        response.status = 200
        urlopen.return_value.__enter__.return_value = response
        result = run(".", ".", timeout=1)
        self.assertTrue(result["http_responded"])
        self.assertFalse(result["database_verified"])
        self.assertFalse(result["pos_verified"])
        process.terminate.assert_called_once()

    @patch("commercial_pharmacy.live_server_smoke.check_port_free", return_value=True)
    @patch("commercial_pharmacy.live_server_smoke.subprocess.Popen")
    @patch("commercial_pharmacy.live_server_smoke.prepare")
    def test_early_exit_reports_failure(self, prepare, popen, free):
        prepare.return_value = (["python", "server.py"], {}, ".")
        process = popen.return_value
        process.poll.return_value = 1
        process.returncode = 1
        result = run(".", ".", timeout=1)
        self.assertFalse(result["http_responded"])
        self.assertEqual(result["error"], "server_exited_before_http")
        process.terminate.assert_not_called()


if __name__ == "__main__":
    unittest.main()
