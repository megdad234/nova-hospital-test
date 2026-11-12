"""Exercise EVERY usable real source test through NOVA paid-order draft bridge.

Only disposable in-memory order rows. No real patient, no clinical approval,
no printing, no pharmacy, and never a clinical diagnosis/reference inference.
"""
import sqlite3
import unittest
from hospital.royallab_catalog_audit import SOURCE
from hospital.royallab_native_catalog_store import (
    install_file, list_tests, clinical_test_form, is_non_lab_service)
from hospital.royallab_native_result_drafts import validate_source_form
from hospital.royallab_native_order_bridge import (
    attach_native_test, save_order_item_draft, load_order_item_draft)

STAFF = {"id": 1, "role": "lab"}
INACTIVE = (False, 0, "False", "false", "0")


def synthetic_value(field):
    kind = field["kind"]
    if kind.startswith("select"):
        active = [o for o in field.get("options", []) if o.get("active") not in INACTIVE]
        if active:
            return str(active[0]["id"])
        if kind == "select_or_number":
            return "1.25"
        if kind == "select_or_text":
            return "TEST-DRAFT"
        raise ValueError("No active source dropdown options")
    if kind == "number":
        return "1.25"
    if kind == "text":
        return "TEST-DRAFT"
    raise ValueError("Unsupported clinical field kind")


class RealCatalogOrderRoundtrip(unittest.TestCase):
    def test_all_usable_real_source_tests_save_and_reload_on_paid_nova_items(self):
        db = sqlite3.connect(":memory:")
        try:
            cid = install_file(db, SOURCE)
            db.executescript("""
                CREATE TABLE hospital_orders (id INTEGER PRIMARY KEY,status TEXT);
                CREATE TABLE hospital_order_items (
                  id INTEGER PRIMARY KEY,order_id INTEGER,result_status TEXT);
                INSERT INTO hospital_orders VALUES (1,'paid');
            """)
            ready = blocked = services = 0
            kinds = set()
            for item_id, source in enumerate(list_tests(db, cid), start=1):
                form = clinical_test_form(db, cid, source["source_test_id"])
                if is_non_lab_service(form):
                    services += 1
                    continue
                try:
                    validate_source_form(form)
                except ValueError:
                    blocked += 1
                    continue
                # This is a fake order only: selected source IDs and values
                # come from the actual archive, not guessed test-name mappings.
                values = {}
                for field in form["fields"]:
                    kinds.add(field["kind"])
                    values[str(field["source_format_id"])] = synthetic_value(field)
                db.execute("INSERT INTO hospital_order_items VALUES (?,?,?)",
                           (item_id, 1, "draft"))
                attach_native_test(db, STAFF, item_id, source["source_test_id"])
                saved = save_order_item_draft(db, STAFF, item_id, values)
                reopened = load_order_item_draft(db, STAFF, item_id)
                self.assertEqual(saved["status"], "draft")
                self.assertEqual(reopened["values"], saved["values"])
                self.assertEqual(saved["values"], values)
                ready += 1
            self.assertEqual(ready + blocked + services, 367)
            self.assertEqual(services, 37)
            self.assertGreaterEqual(ready, 271)
            self.assertLessEqual(blocked, 59)
            self.assertEqual(ready + blocked, 330)
            self.assertIn("select", kinds)
            # Original relational metadata (not a name or range guess)
            # proves that CBC and other source values are numeric.
            self.assertIn("number", kinds)
            self.assertIn("text", kinds)
            self.assertEqual(db.execute(
                "SELECT COUNT(*) FROM royal_lab_native_result_drafts").fetchone()[0], ready)
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
