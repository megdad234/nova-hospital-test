"""Tests for safe NOVA price-list matching and price preview."""
import importlib.util
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).parent))
from nova_price_list_matching import preview

class MatchingTests(unittest.TestCase):
    def setUp(self):
        self.catalog = [{"package_id": 11, "name": "Drug A", "strength": "20mg",
                         "pack": "10 tabs", "factor": 10, "sale_price": 3000}]
        self.last = {11: {"price": 2000, "factor": 10}}
    def test_changed_price_preserves_markup(self):
        x = preview([{"name":"Drug A","strength":"20mg","pack":"10 tabs",
                      "purchase_price":2500}], self.catalog, self.last)
        self.assertEqual(x[0]["status"], "ready")
        self.assertEqual(x[0]["proposed_sale"], 3750)
        self.assertTrue(x[0]["selected"])
    def test_unknown_item_requires_review(self):
        x = preview([{"name":"Other","strength":"20mg","pack":"10 tabs",
                      "purchase_price":2500}], self.catalog, self.last)
        self.assertEqual(x[0]["reason"], "unmatched")
    def test_different_pack_requires_review(self):
        x = preview([{"name":"Drug A","strength":"20mg","pack":"30 tabs",
                      "purchase_price":2500}], self.catalog, self.last)
        self.assertEqual(x[0]["reason"], "unmatched")
    def test_unchanged_is_not_selected(self):
        x = preview([{"name":"Drug A","strength":"20mg","pack":"10 tabs",
                      "purchase_price":2000}], self.catalog, self.last)
        self.assertEqual(x[0]["status"], "unchanged")
        self.assertFalse(x[0]["selected"])
    def test_ambiguous_is_not_selected(self):
        x = preview([{"name":"Drug A","strength":"20mg","pack":"10 tabs",
                      "purchase_price":2500}], self.catalog * 2, self.last)
        self.assertEqual(x[0]["reason"], "ambiguous")
    def test_duplicate_upload_requires_review(self):
        row={"name":"Drug A","strength":"20mg","pack":"10 tabs","purchase_price":2500}
        x=preview([row,row], self.catalog, self.last)
        self.assertEqual(x[1]["reason"], "duplicate_in_upload")
    def test_global_markup(self):
        x=preview([{"name":"Drug A","strength":"20mg","pack":"10 tabs",
                    "purchase_price":2500}],self.catalog,self.last,20)
        self.assertEqual(x[0]["proposed_sale"],3000)

if __name__ == "__main__":
    unittest.main()
