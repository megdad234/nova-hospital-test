"""Regression: NOVA lab pricing and result-choice API must see >200 tests.

The original hospital/lab.py API silently truncated active items after 200,
making the user-supplied screenshots' Vitamin D/316 and VDRL searches empty.
This test proves 367 source IDs remain searchable while respecting active
filters, popular flag, local names, prices and unrelated code.
"""
import ast
import pathlib
import re
import sys
import types
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".github" / "ci"))
from royallab_lab_catalog_visibility_patch import OLD, NEW, patch


def _load_callable(source):
    parsed = ast.parse(source)
    fn = next((n for n in parsed.body
               if isinstance(n, ast.FunctionDef) and n.name == "catalog"), None)
    if fn is None:
        raise RuntimeError("No NOVA catalog function")
    isolate = ast.Module(body=[fn], type_ignores=[])
    ast.fix_missing_locations(isolate)
    class FakePharmacy:
        def query(self, conn, sql):
            if "active=1" not in sql or "ORDER BY popular DESC,name" not in sql:
                raise AssertionError("Original active/sort protections changed")
            return [row for row in conn if row["active"]]
    ns = {"pharmacy": FakePharmacy()}
    exec(compile(isolate, "<NOVA catalog regression>", "exec"), ns)
    return ns["catalog"]


class FullLabCatalogVisibilityTests(unittest.TestCase):
    def setUp(self):
        # Put the sought tests past the old 200-item cutoff on purpose.
        self.data = [
            {"id": i, "code": f"ROYAL-{i}", "name": f"Lab item {i:03d}",
             "category": "Chemistry", "aliases": "", "popular": 0,
             "active": 1, "price": 0}
            for i in range(1, 368)
        ]
        self.data[315].update(code="ROYAL-316", name="Vitamin D",
                              price=70000, category="Chemistry")
        self.data[58].update(code="ROYAL-59", name="VDRL",
                             price=15000, category="Serology")
        # Original alphabetical sort can place either past row 200;
        # intentionally reorder to model the screenshot's server response.
        self.data = [r for r in self.data
                     if r["code"] not in ("ROYAL-316","ROYAL-59")] + [
            next(x for x in self.data if x["code"] == code)
            for code in ("ROYAL-316","ROYAL-59")
        ]
        self.func = _load_callable(NEW)

    def test_original_source_cut_off_search_at_200(self):
        old = _load_callable(OLD)
        self.assertEqual(len(old(self.data)), 200)
        self.assertEqual(len([x for x in old(self.data)
                              if "vit" in x["name"].lower()]), 0)
        self.assertEqual(len([x for x in old(self.data)
                              if "vdrl" in x["name"].lower()]), 0)

    def test_complete_367_catalog_visible_to_ui(self):
        data = self.func(self.data)
        self.assertEqual(len(data), 367)
        self.assertEqual(len({x["code"] for x in data}), 367)
        self.assertEqual(data[-2]["name"], "Vitamin D")
        self.assertEqual(data[-1]["name"], "VDRL")
        self.assertEqual(data[-2]["price"], 70000,
                         "Previously configured prices are not touched")
        self.assertEqual(data[-1]["price"], 15000)

    def test_search_by_exact_name_partial_name_and_source_number(self):
        all_rows = self.func(self.data)
        def search_ui(query):
            q=query.casefold()
            return [x for x in all_rows
                    if q in f"{x['code']} {x['name']} {x['aliases']}".casefold()]
        for q,expected in [("vit","ROYAL-316"),("Vitamin D","ROYAL-316"),
                           ("316","ROYAL-316"),("vdrl","ROYAL-59"),
                           ("59","ROYAL-59")]:
            with self.subTest(q=q):
                matches=search_ui(q)
                self.assertTrue(any(x["code"]==expected for x in matches))
                self.assertTrue(any(x["code"]==expected
                                    for x in self.func(self.data,q)))
        self.assertEqual(self.func(self.data,"NOT_A_SOURCE_TEST"),[])

    def test_source_active_only_local_additions_and_popular_filter(self):
        rows=list(self.data)
        rows += [
            {"id":400,"code":"NOVA-LOCAL-X","name":"Local new test",
             "category":"Serology","aliases":"custom","popular":1,
             "active":1,"price":25000},
            {"id":401,"code":"NOVA-LOCAL-DISABLED","name":"Inactive test",
             "category":"Serology","aliases":"","popular":1,
             "active":0,"price":500}
        ]
        self.assertEqual(len(self.func(rows)),368)
        self.assertEqual([x["code"] for x in self.func(rows,only_popular=True)],
                         ["NOVA-LOCAL-X"])
        self.assertEqual([x["code"] for x in self.func(rows,"custom")],
                         ["NOVA-LOCAL-X"])
        self.assertEqual(self.func(rows,"Inactive test"),[])

    def test_surgical_patch_refuses_unknown_anchors_and_duplicate_application(self):
        self.assertEqual(OLD.count("return rows[:200]"),1)
        self.assertEqual(NEW.count("return rows[:200]"),0)
        self.assertEqual(patch(OLD),NEW)
        with self.assertRaises(ValueError):
            patch(NEW)
        with self.assertRaises(ValueError):
            patch(OLD.replace("popular DESC,name","name"))
        with self.assertRaises(ValueError):
            patch(OLD+OLD)

    def test_windows_assembled_lab_source_uses_full_catalog(self):
        actual = ROOT / "hospital" / "lab.py"
        if not actual.exists():
            self.skipTest("Source ZIP is extracted only in the Windows CI build")
        src=actual.read_text(encoding="utf-8-sig")
        self.assertIn("NOVA_ROYALLAB_CATALOG_ALL_ACTIVE",src)
        f=_load_callable(src)
        self.assertEqual(len(f(self.data)),367)
        self.assertTrue(any(t["name"]=="Vitamin D" for t in f(self.data,"vit")))
        self.assertTrue(any(t["name"]=="VDRL" for t in f(self.data,"vdrl")))
        self.assertNotIn("return rows[:200]",ast.get_source_segment(src,
            next(n for n in ast.parse(src).body
                 if isinstance(n,ast.FunctionDef) and n.name=="catalog")))


if __name__=="__main__":
    unittest.main()
