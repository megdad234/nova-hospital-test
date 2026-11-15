"""Urine photo reconciliation: labels/layout only; exact Royal Lab source IDs."""
import copy
import json
import sqlite3
import unittest
from hospital.royallab_nova_urine_layout import (
    display_order_detail, MACRO, MICRO, DISPLAY_NAMES)
from hospital.royallab_catalog_audit import SOURCE
from hospital.royallab_native_result_form import native_catalog


class UrineLayoutTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.executescript("""
            CREATE TABLE hospital_lab_tests(id INTEGER PRIMARY KEY, code TEXT);
            CREATE TABLE hospital_order_items(id INTEGER PRIMARY KEY,
                test_id INTEGER, result_status TEXT DEFAULT 'pending',
                result_version INTEGER DEFAULT 0);
            INSERT INTO hospital_lab_tests VALUES(7, 'ROYAL-7'), (8, 'ROYAL-8');
            INSERT INTO hospital_order_items VALUES(101, 7, 'pending', 0);
            INSERT INTO hospital_order_items VALUES(102, 8, 'pending', 0);
            INSERT INTO hospital_order_items VALUES(103, 7, 'approved', 1);
            INSERT INTO hospital_order_items VALUES(104, 7, 'published', 0);
            INSERT INTO hospital_order_items VALUES(105, 7, 'pending', 2);
        """)
        self.rows = [
            ("ROYAL_FMT_554", "Colour", "Yellow"),
            ("ROYAL_FMT_290", "Protein", "NIL"),
            ("ROYAL_FMT_2054", "Sugar", "Nill"),
            ("ROYAL_FMT_5", "Ketones", "NIL"),
            ("ROYAL_FMT_6", "Bilirubin", "NIL"),
            ("ROYAL_FMT_851", "Pus Cells", "5-7"),
            ("ROYAL_FMT_1774", "R.B.Cs", "0-1"),
            ("ROYAL_FMT_297", "Crystals", "Calcium oxalate"),
            ("ROYAL_FMT_727", "Crystals", "(++)"),
            ("ROYAL_FMT_2052", "S.Gravity", "1.030"),
            ("ROYAL_FMT_732", "Nitrite", "Nil"),
            ("ROYAL_FMT_735", "Urobilinogin", "Nil"),
            ("ROYAL_FMT_736", "PH", "Acidic"),
            ("ROYAL_ANALYTE_472", "S.Gravity", ""),
            ("ROYAL_FMT_744", "Mucous Threads", "Nil"),
            ("ROYAL_FMT_745", "Cast", "Nil"),
            ("ROYAL_FMT_746", "Cast", "(+)"),
            ("ROYAL_FMT_748", "Epithelial Cells", "(+)"),
            ("ROYAL_FMT_850", "Comment", ""),
            ("ROYAL_FMT_555", "Others", "Few"),
            ("ROYAL_FMT_409", "Others", "note"),
            ("ROYAL_FMT_1004", "Bacteria", "Nil"),
            ("ROYAL_FMT_1005", "Yeast", "Nil"),
        ]
        lines = [{
            "id": i + 1, "code": code, "name": name, "value": value,
            "reference_range": "original", "unit": "",
            "royal_lab_field": {"kind": "select", "options": ["Nil", "Few", "(+)"]}
        } for i, (code, name, value) in enumerate(self.rows)]
        self.original = {
            "items": [
                {"id": 101, "lines": lines},
                {"id": 102, "lines": [{"code": "ROYAL_FMT_297", "name": "Crystals"}]},
                {"id": 103, "lines": copy.deepcopy(lines)},
                {"id": 104, "lines": copy.deepcopy(lines)},
                {"id": 105, "lines": copy.deepcopy(lines)},
            ],
            "order_no": "SYNTHETIC"
        }

    def tearDown(self):
        self.db.close()

    def test_only_display_changes_and_all_original_inputs_stay_independent(self):
        before = copy.deepcopy(self.original)
        result = display_order_detail(self.db, self.original)
        original_lines = before["items"][0]["lines"]
        changed_lines = result["items"][0]["lines"]
        self.assertEqual(len(original_lines), len(changed_lines))
        self.assertEqual({x["id"] for x in original_lines},
                         {x["id"] for x in changed_lines})
        for old, new in zip(original_lines, changed_lines):
            for k in ("id", "code", "value", "unit", "reference_range", "royal_lab_field"):
                self.assertEqual(new[k], old[k])
            if old["code"] in MACRO:
                self.assertEqual(new["section_name"], "Macroscopy")
            if old["code"] in MICRO:
                self.assertEqual(new["section_name"], "Microscopy")
            if old["code"] in DISPLAY_NAMES:
                self.assertEqual(new["name"], DISPLAY_NAMES[old["code"]][1])
                self.assertEqual(new["source_label"], old["name"])
            else:
                self.assertEqual(new["name"], old["name"])
        self.assertEqual(result["order_no"], "SYNTHETIC")
        self.assertEqual(self.original, before, "No caller data mutation")

    def test_preserves_other_tests_and_historical_signed_or_edited_orders(self):
        result = display_order_detail(self.db, self.original)
        for index in (1, 2, 3, 4):
            self.assertIs(result["items"][index], self.original["items"][index])
        self.assertNotIn("section_name", self.original["items"][0]["lines"][0])

    def test_manual_display_labels_and_existing_sections_are_respected(self):
        sample = copy.deepcopy(self.original)
        sample["items"][0]["lines"][7]["name"] = "Custom Crystal Label"
        sample["items"][0]["lines"][7]["section_name"] = "Verified Section"
        output = display_order_detail(self.db, sample)["items"][0]["lines"][7]
        self.assertEqual(output["name"], "Custom Crystal Label")
        self.assertEqual(output["section_name"], "Verified Section")
        self.assertNotIn("source_label", output)

    def test_missing_lab_schema_returns_unchanged_data(self):
        with sqlite3.connect(":memory:") as db:
            self.assertIs(display_order_detail(db, self.original), self.original)

    def test_original_royallab_definitions_prove_duplicate_roles(self):
        library = json.loads(SOURCE.read_text(encoding="utf-8-sig"))
        catalog = native_catalog(library)
        urine = next(t for t in catalog["tests"] if t["source_test_id"] == "7")
        self.assertEqual(urine["name"], "URINE GENERAL ANALYSIS")
        fields = {str(f["source_format_id"]): f for f in urine["fields"]}
        for code in MACRO | MICRO:
            field_id = code.removeprefix("ROYAL_FMT_") if code.startswith("ROYAL_FMT_") else "ANALYTE-472"
            self.assertIn(field_id, fields)
        for a, b, analyte_id in (
            ("297", "727", "174"),
            ("745", "746", "480"),
            ("555", "409", "226"),
        ):
            self.assertEqual(fields[a]["source_analyte_id"], analyte_id)
            self.assertEqual(fields[b]["source_analyte_id"], analyte_id)
            self.assertNotEqual(fields[a]["source_format_id"], fields[b]["source_format_id"])
        self.assertEqual(fields["297"]["kind"], "select")
        self.assertEqual(fields["727"]["kind"], "select")
        self.assertEqual(fields["745"]["kind"], "select")
        self.assertEqual(fields["746"]["kind"], "select")
        self.assertEqual(fields["555"]["kind"], "select")
        self.assertEqual(fields["409"]["kind"], "text")
        self.assertEqual(fields["2052"]["source_analyte_id"], "444")
        self.assertEqual(fields["ANALYTE-472"]["source_analyte_id"], "472")
        self.assertFalse(fields["ANALYTE-472"]["types"],
                         "Do not pretend that source has a closed dropdown")
        self.assertTrue(any(o["label"] == "Calcium oxalate" for o in fields["297"]["options"]))
        self.assertTrue(any(o["label"] == "(++)" for o in fields["727"]["options"]))
        self.assertTrue(any(o["label"] == "Few" for o in fields["555"]["options"]))


if __name__ == "__main__":
    unittest.main()
