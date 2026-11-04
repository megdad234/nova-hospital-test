"""Integration smoke test for the commercial maintenance command line."""
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import json
import tempfile
import unittest
from commercial_pharmacy.cli import run
from commercial_pharmacy.runtime_isolation import paths

class CliTests(unittest.TestCase):
    def invoke(self, *args):
        output = StringIO()
        with redirect_stdout(output):
            code = run(list(args))
        self.assertEqual(code, 0)
        return json.loads(output.getvalue())

    def test_initialize_inspect_and_protected_hospital(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            protected = root / "hospital"
            protected.mkdir()
            marker = protected / "original.txt"
            marker.write_text("unchanged")
            commercial = root / "pharmacy"
            args = ("--data-dir", str(commercial), "--protect-hospital-dir", str(protected))
            before = self.invoke(*args, "inspect")
            self.assertFalse(before["initialized"])
            result = self.invoke(*args, "initialize")
            self.assertFalse(result["hospital_database_enabled"])
            self.assertTrue((commercial / "commercial_config.json").is_file())
            after = self.invoke(*args, "inspect")
            self.assertTrue(after["initialized"])
            self.assertFalse(after["database_exists"])
            self.assertEqual(marker.read_text(), "unchanged")
            with self.assertRaises(ValueError):
                self.invoke("--data-dir", str(protected), "--protect-hospital-dir",
                            str(protected), "initialize")

if __name__ == "__main__":
    unittest.main()
