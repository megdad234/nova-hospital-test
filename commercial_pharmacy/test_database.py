"""Exercise standalone SQLite guard without using any NOVA Hospital database."""
import sqlite3
from contextlib import closing
from pathlib import Path
import tempfile
import unittest

from commercial_pharmacy.database import open_pharmacy_database, verify_pharmacy_database
from commercial_pharmacy.runtime_isolation import initialize_directories, paths

class DatabaseTests(unittest.TestCase):
    def test_database_is_created_only_in_commercial_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            hospital = Path(temp) / "hospital"
            hospital.mkdir()
            hospital_db = hospital / "nova.sqlite3"
            hospital_db.write_bytes(b"DO NOT TOUCH")
            p = paths({"NOVA_COMMERCIAL_DATA_DIR": str(Path(temp) / "commercial")})
            initialize_directories(p)
            with closing(open_pharmacy_database(p, protected_hospital_paths=[hospital])) as conn:
                self.assertTrue(verify_pharmacy_database(conn, p))
                self.assertEqual(conn.execute("PRAGMA foreign_keys").fetchone()[0], 1)
                conn.execute("CREATE TABLE IF NOT EXISTS commercial_test (id INTEGER PRIMARY KEY)")
            self.assertTrue(p.database.exists())
            self.assertEqual(hospital_db.read_bytes(), b"DO NOT TOUCH")
            self.assertEqual(list(hospital.iterdir()), [hospital_db])

    def test_refuse_hospital_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            hospital = Path(temp) / "hospital"
            hospital.mkdir()
            p = paths({"NOVA_COMMERCIAL_DATA_DIR": str(hospital)})
            with self.assertRaises(ValueError):
                open_pharmacy_database(p, protected_hospital_paths=[hospital])

if __name__ == "__main__":
    unittest.main()
