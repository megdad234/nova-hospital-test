"""NOVA candidate matching safety regression tests."""
import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).parent))
from nova_price_list_candidates import candidates

class CandidateTests(unittest.TestCase):
    def setUp(self):
        self.catalog=[{"package_id":1,"name":"Mobizal 15mg","strength":"15mg",
                       "pack":"10 tabs","form":"tablet","manufacturer":"A"},
                      {"package_id":2,"name":"Mobizal 7.5mg","strength":"7.5mg",
                       "pack":"10 tabs","form":"tablet","manufacturer":"A"}]
    def test_spacing_variant_is_review_only(self):
        rows=candidates({"name":"MOBIZAL15mg","strength":"15mg","pack":"10 tabs"},self.catalog)
        self.assertEqual(rows[0]["package_id"],1)
        self.assertTrue(rows[0]["requires_confirmation"])
    def test_strength_conflict_flagged(self):
        rows=candidates({"name":"Mobizal 7.5mg","strength":"15mg","pack":"10 tabs"},self.catalog)
        match=next(x for x in rows if x["package_id"]==2)
        self.assertIn("strength",match["conflicts"])
    def test_alias_does_not_auto_approve(self):
        rows=candidates({"name":"Supplier Brand","strength":"15mg"},
                        self.catalog,[{"alias":"Supplier Brand","package_id":1}])
        self.assertEqual(rows[0]["package_id"],1)
        self.assertTrue(rows[0]["known_alias"])
        self.assertTrue(rows[0]["requires_confirmation"])
    def test_pack_conflict_flagged(self):
        rows=candidates({"name":"Mobizal 15mg","pack":"30 tabs"},self.catalog)
        self.assertIn("pack",rows[0]["conflicts"])

if __name__=="__main__":
    unittest.main()
