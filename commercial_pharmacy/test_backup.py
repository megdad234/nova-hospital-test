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

    def test_reject_unsafe_backup_names_and_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = paths({"NOVA_COMMERCIAL_DATA_DIR": str(Path(tmp) / "commercial")})
            initialize_directories(config)
            with closing(open_pharmacy_database(config)) as conn:
                for name in (".", "..", "../hospital.db", "folder/name.sqlite3", "bad name.sqlite3"):
                    with self.subTest(name=name), self.assertRaises(ValueError):
                        create_backup(conn, config, name)
                created = create_backup(conn, config, "first.sqlite3")
                with self.assertRaises(FileExistsError):
                    create_backup(conn, config, "first.sqlite3")
                self.assertTrue(created.is_file())
                link = config.backups / "linked.sqlite3"
                try:
                    link.symlink_to(created)
                except (OSError, NotImplementedError):
                    pass
                else:
                    with self.assertRaises(FileExistsError):
                        create_backup(conn, config, "linked.sqlite3")

if __name__ == "__main__":
    unittest.main()
