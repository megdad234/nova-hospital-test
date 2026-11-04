"""Tests for guarded NOVA price approval and rollback."""
import sqlite3
import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).parent))
from nova_price_list_approval import validate_approval, apply_approved, rollback_approved

class ApprovalTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:")
        self.db.execute("CREATE TABLE packages(id INTEGER PRIMARY KEY, sale_price INTEGER)")
        self.db.execute("INSERT INTO packages VALUES(11,3000)")
        self.rows=[dict(package_id=11,status="ready",selected=True,old_sale=3000,
                        new_purchase=2500,proposed_sale=3750)]
        self.audit=[]
    def tearDown(self):
        self.db.close()
    def test_approve_and_rollback(self):
        changes=validate_approval(self.rows,{11:{"action":"approve"}},{11:3000})
        with self.db:
            apply_approved(self.db,changes,lambda action,data:self.audit.append(action))
        self.assertEqual(self.db.execute("SELECT sale_price FROM packages").fetchone()[0],3750)
        with self.db:
            rollback_approved(self.db,changes,lambda action,data:self.audit.append(action))
        self.assertEqual(self.db.execute("SELECT sale_price FROM packages").fetchone()[0],3000)
    def test_stale_preview_rejected(self):
        with self.assertRaises(ValueError):
            validate_approval(self.rows,{11:{"action":"approve"}},{11:3200})
    def test_unmatched_rejected(self):
        with self.assertRaises(ValueError):
            validate_approval(self.rows,{99:{"action":"approve"}},{11:3000})
    def test_concurrent_update_rejected(self):
        changes=validate_approval(self.rows,{11:{"action":"approve"}},{11:3000})
        self.db.execute("UPDATE packages SET sale_price=3200 WHERE id=11")
        with self.assertRaises(ValueError):
            with self.db:
                apply_approved(self.db,changes,lambda action,data:None)
        self.assertEqual(self.db.execute("SELECT sale_price FROM packages").fetchone()[0],3200)
    def test_rollback_refuses_later_edit(self):
        changes=validate_approval(self.rows,{11:{"action":"approve"}},{11:3000})
        with self.db:
            apply_approved(self.db,changes,lambda action,data:None)
        self.db.execute("UPDATE packages SET sale_price=4000 WHERE id=11")
        with self.assertRaises(ValueError):
            with self.db:
                rollback_approved(self.db,changes,lambda action,data:None)
        self.assertEqual(self.db.execute("SELECT sale_price FROM packages").fetchone()[0],4000)

if __name__=="__main__":
    unittest.main()
