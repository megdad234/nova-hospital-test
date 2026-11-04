"""Tests for actual standalone pharmacy filesystem and network isolation."""
import json
import os
from pathlib import Path
import tempfile
import unittest

from commercial_pharmacy.runtime_isolation import (
    DATABASE_NAME, PRODUCT, PORT, backup_destination, choose_port,
    initialize_directories, paths, safe_backup_filename,
    validate_paths, write_runtime_config,
)

class RuntimeIsolationTests(unittest.TestCase):
    def test_separate_database_and_directories(self):
        with tempfile.TemporaryDirectory() as temp:
            hospital = Path(temp) / "NOVA Hospital"
            hospital.mkdir()
            env = {"NOVA_COMMERCIAL_DATA_DIR": str(Path(temp) / "NOVA Pharmacy")}
            p = validate_paths(paths(env), [hospital])
            initialize_directories(p)
            self.assertEqual(p.database.name, DATABASE_NAME)
            self.assertNotEqual(p.database.parent, hospital)
            self.assertTrue(p.backups.is_dir())
            self.assertFalse(p.database.exists(), "No database should be created before app bootstrap")
            result = write_runtime_config(p, env)
            self.assertEqual(result["hospital_database_enabled"], False)
            self.assertEqual(result["port"], PORT)
            self.assertEqual(json.loads(p.config.read_text())["product"], PRODUCT)
            self.assertFalse(any(hospital.iterdir()))

    def test_protected_data_overlap(self):
        with tempfile.TemporaryDirectory() as temp:
            hospital = Path(temp) / "hospital"
            for candidate in (hospital, hospital / "subfolder", Path(temp)):
                env = {"NOVA_COMMERCIAL_DATA_DIR": str(candidate)}
                with self.assertRaises(ValueError):
                    validate_paths(paths(env), [hospital])

    def test_backup_filename_traversal(self):
        for value in ("../hospital.sqlite", "folder\\backup.db", "/tmp/a", "", "..", "a/b"):
            with self.assertRaises(ValueError):
                safe_backup_filename(value)
        with tempfile.TemporaryDirectory() as temp:
            p = paths({"NOVA_COMMERCIAL_DATA_DIR": temp})
            self.assertEqual(backup_destination(p, "pharmacy-2026-11-04.zip").parent, p.backups)

    def test_port_collision_guard(self):
        self.assertEqual(choose_port({}), PORT)
        for value in ("10080", "0", "65536", "-1", "bad"):
            with self.assertRaises(ValueError):
                choose_port({"NOVA_COMMERCIAL_PORT": value})

if __name__ == "__main__":
    unittest.main()
