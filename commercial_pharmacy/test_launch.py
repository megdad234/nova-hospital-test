"""Integration smoke test for the commercial maintenance command line."""
from contextlib import closing, redirect_stdout
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
            diagnosis = self.invoke(*args, "diagnose")
            self.assertFalse(diagnosis["database_exists"])
            self.assertFalse(diagnosis["hospital_service_enabled"])
            self.assertEqual(self.invoke(*args, "list-backups")["backups"], [])
            before = self.invoke(*args, "inspect")
            self.assertFalse(before["initialized"])
            result = self.invoke(*args, "initialize")
            self.assertFalse(result["hospital_database_enabled"])
            self.assertTrue((commercial / "commercial_config.json").is_file())
            after = self.invoke(*args, "inspect")
            self.assertTrue(after["initialized"])
            self.assertFalse(after["database_exists"])
            self.assertEqual(marker.read_text(), "unchanged")
            self.assertFalse((commercial / "commercial_pharmacy.sqlite3").exists())
            with self.assertRaises(ValueError):
                self.invoke("--data-dir", str(protected), "--protect-hospital-dir",
                            str(protected), "initialize")

    def test_diagnose_existing_database_read_only(self):
        import sqlite3
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = root / "commercial"
            self.invoke("--data-dir", str(data), "initialize")
            database = data / "commercial_pharmacy.sqlite3"
            with closing(sqlite3.connect(database)) as conn:
                conn.execute("CREATE TABLE inventory (id INTEGER)")
                conn.execute("INSERT INTO inventory VALUES (1)")
                conn.commit()
            result = self.invoke("--data-dir", str(data), "diagnose")
            self.assertEqual(self.invoke("--data-dir", str(data), "list-backups")["backups"], [])
            self.assertEqual(result["database_integrity"], "ok")
            self.assertTrue(result["database_exists"])
            health = self.invoke("--data-dir", str(data), "check-database")
            self.assertEqual(health["integrity"], "ok")
            self.assertTrue(health["read_only"])
            with closing(sqlite3.connect(database)) as conn:
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM inventory").fetchone()[0], 1)

    def test_automatic_backup_retention_keeps_manual_backups(self):
        import sqlite3
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = root / "commercial"
            self.invoke("--data-dir", str(data), "initialize")
            with closing(sqlite3.connect(data / "commercial_pharmacy.sqlite3")) as db:
                db.execute("CREATE TABLE items (id INTEGER)")
                db.execute("INSERT INTO items VALUES (7)")
            first = self.invoke("--data-dir", str(data), "backup-auto", "--retain", "1")
            self.assertTrue(Path(first["backup"]).exists())
            manual = self.invoke("--data-dir", str(data), "backup", "manual.sqlite3")
            second = self.invoke("--data-dir", str(data), "backup-auto", "--retain", "1")
            self.assertTrue(Path(second["backup"]).exists())
            self.assertFalse(Path(first["backup"]).exists())
            self.assertTrue(Path(manual["backup"]).exists())
            inventory = self.invoke("--data-dir", str(data), "list-backups")["backups"]
            self.assertEqual(len(inventory), 2)
            with self.assertRaises(ValueError):
                self.invoke("--data-dir", str(data), "backup-auto", "--retain", "0")

if __name__ == "__main__":
    unittest.main()
