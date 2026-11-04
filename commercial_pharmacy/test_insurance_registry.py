"""Tests for independent pharmacy insurance membership identity."""
from contextlib import closing
from pathlib import Path
import tempfile
import unittest
from commercial_pharmacy.database import open_pharmacy_database
from commercial_pharmacy.insurance_registry import (
    add_membership, find_membership, initialize_registry, register_customer)
from commercial_pharmacy.runtime_isolation import initialize_directories, paths

class InsuranceRegistryTests(unittest.TestCase):
    def test_card_lookup_and_unique_membership(self):
        with tempfile.TemporaryDirectory() as tmp:
            hospital = Path(tmp) / "hospital"
            hospital.mkdir()
            p = paths({"NOVA_COMMERCIAL_DATA_DIR": str(Path(tmp) / "pharmacy")})
            initialize_directories(p)
            with closing(open_pharmacy_database(p, protected_hospital_paths=[hospital])) as conn:
                initialize_registry(conn)
                cid = register_customer(conn, "Test Customer", "0123456789")
                membership = add_membership(conn, cid, "Insurer A", "CARD-100", "POL-1")
                row = find_membership(conn, "Insurer A", "CARD-100")
                self.assertEqual(row["id"], membership)
                self.assertEqual(row["customer_id"], cid)
                self.assertEqual(row["policy_number"], "POL-1")
                self.assertIsNone(find_membership(conn, "Insurer A", "missing"))
                with self.assertRaises(Exception):
                    add_membership(conn, cid, "Insurer A", "CARD-100")
                conn.rollback()
            self.assertFalse(list(hospital.iterdir()))

if __name__ == "__main__":
    unittest.main()
