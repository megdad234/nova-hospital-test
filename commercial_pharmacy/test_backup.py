import sqlite3
from contextlib import closing
from pathlib import Path
import tempfile
import unittest
from commercial_pharmacy.backup import create_backup, inspect_backup, stage_restore
from commercial_pharmacy.database import open_pharmacy_database
from commercial_pharmacy.runtime_isolation import initialize_directories, paths

class BackupTests(unittest.TestCase):
    def test_online_backup_and_staged_restore(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            protected = root / "hospital"
            protected.mkdir()
            marker = protected / "original.db"
            marker.write_bytes(b"unchanged")
            p = paths({"NOVA_COMMERCIAL_DATA_DIR": str(root / "commercial")})
            initialize_directories(p)
            with closing(open_pharmacy_database(p, protected_hospital_paths=[protected])) as conn:
                conn.execute("CREATE TABLE items (id INTEGER PRIMARY KEY)")
                conn.execute("INSERT INTO items VALUES (1)")
                conn.commit()
                backup = create_backup(conn, p, "snapshot.sqlite3")
                self.assertTrue(inspect_backup(backup)["valid"])
                conn.execute("INSERT INTO items VALUES (2)")
                conn.commit()
                candidate = stage_restore(backup, p)
                with closing(sqlite3.connect(candidate)) as staged:
                    self.assertEqual(staged.execute("SELECT count(*) FROM items").fetchone()[0], 1)
                self.assertEqual(conn.execute("SELECT count(*) FROM items").fetchone()[0], 2)
            self.assertEqual(marker.read_bytes(), b"unchanged")

if __name__ == "__main__":
    unittest.main()
