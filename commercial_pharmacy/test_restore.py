from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest
from commercial_pharmacy.backup import create_backup
from commercial_pharmacy.database import open_pharmacy_database
from commercial_pharmacy.restore import restore_offline
from commercial_pharmacy.runtime_isolation import initialize_directories, paths

class OfflineRestoreTests(unittest.TestCase):
    def test_offline_restore_preserves_rollback(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            protected = root / "hospital"
            protected.mkdir()
            hospital_marker = protected / "hospital.sqlite"
            hospital_marker.write_bytes(b"protected")
            config = paths({"NOVA_COMMERCIAL_DATA_DIR": str(root / "pharmacy")})
            initialize_directories(config)
            with closing(open_pharmacy_database(config, protected_hospital_paths=[protected])) as conn:
                conn.execute("CREATE TABLE stock (id INTEGER PRIMARY KEY)")
                conn.execute("INSERT INTO stock VALUES(1)")
                conn.commit()
                saved = create_backup(conn, config, "snapshot.sqlite3")
                conn.execute("INSERT INTO stock VALUES(2)")
                conn.commit()
                with self.assertRaises(RuntimeError):
                    restore_offline(saved, config, service_stopped=False)
            with self.assertRaises(ValueError):
                restore_offline(hospital_marker, config, service_stopped=True,
                                protected_hospital_paths=[protected])
            outcome = restore_offline(saved, config, service_stopped=True,
                                      protected_hospital_paths=[protected])
            with closing(sqlite3.connect(config.database)) as current:
                self.assertEqual(current.execute("SELECT COUNT(*) FROM stock").fetchone()[0], 1)
            self.assertTrue(Path(outcome["rollback"]).is_file())
            with closing(sqlite3.connect(outcome["rollback"])) as previous:
                self.assertEqual(previous.execute("SELECT COUNT(*) FROM stock").fetchone()[0], 2)
            self.assertEqual(hospital_marker.read_bytes(), b"protected")

    def test_invalid_restore_preserves_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = paths({"NOVA_COMMERCIAL_DATA_DIR": str(Path(tmp) / "commercial")})
            initialize_directories(config)
            with closing(open_pharmacy_database(config)) as conn:
                conn.execute("CREATE TABLE stock (id INTEGER)")
                conn.execute("INSERT INTO stock VALUES (42)")
                conn.commit()
            bad = config.backups / "invalid.sqlite3"
            bad.write_bytes(b"invalid sqlite")
            with self.assertRaises((sqlite3.DatabaseError, ValueError)):
                restore_offline(bad, config, service_stopped=True)
            with closing(sqlite3.connect(config.database)) as conn:
                self.assertEqual(conn.execute("SELECT id FROM stock").fetchone()[0], 42)

if __name__ == "__main__":
    unittest.main()
