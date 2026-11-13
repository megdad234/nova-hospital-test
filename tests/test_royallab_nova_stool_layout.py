"""Photo review: stool fields are correctly mapped; clarify two original Others."""
import json
import sqlite3
import unittest
from hospital.royallab_nova_stool_layout import (
    display_order_detail, MACRO, MICRO, CUSTOM_LABELS)
from hospital.royallab_catalog_audit import SOURCE
from hospital.royallab_native_result_form import native_catalog


class RoyalStoolDisplayTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:")
        self.db.executescript("""
          CREATE TABLE hospital_lab_tests(id INTEGER PRIMARY KEY,code TEXT);
          CREATE TABLE hospital_order_items(
            id INTEGER PRIMARY KEY,test_id INTEGER,
            result_status TEXT DEFAULT 'pending',result_version INTEGER DEFAULT 0);
          INSERT INTO hospital_lab_tests VALUES(8,'ROYAL-8'),(7,'ROYAL-7');
          INSERT INTO hospital_order_items(id,test_id) VALUES(101,8),(102,7);
          INSERT INTO hospital_order_items(id,test_id,result_status,result_version)
          VALUES(103,8,'approved',1);
        """)
        self.original={
          "items":[
            {"id":101,"lines":[
              {"id":11,"code":"ROYAL_FMT_302","name":"Colour","value":"Black",
               "royal_lab_field":{"kind":"select","options":["Black","Brown"]}},
              {"id":12,"code":"ROYAL_FMT_67","name":"Consistency","value":"",
               "royal_lab_field":{"kind":"select_or_text","options":["Soft","Formed","Watery"]}},
              {"id":13,"code":"ROYAL_FMT_73","name":"Cyst","value":"",
               "royal_lab_field":{"kind":"select_or_text",
                                  "options":["NIL","E.histolytica","Giardia Lambilia","E.Coli"]}},
              {"id":14,"code":"ROYAL_FMT_307","name":"Ova","value":"",
               "royal_lab_field":{"kind":"select","options":["Nil","Schistosoma mansoni"]}},
              {"id":15,"code":"ROYAL_FMT_310","name":"Others","value":"",
               "royal_lab_field":{"kind":"select","options":["Fat Globules"]}},
              {"id":16,"code":"ROYAL_FMT_896","name":"Others","value":"",
               "royal_lab_field":{"kind":"text","options":[]}},
              {"id":17,"code":"ROYAL_FMT_1778","name":"Yeast","value":""}
            ]},
            {"id":102,"lines":[{"id":21,"code":"ROYAL_FMT_310","name":"Others","value":"x"}]},
            {"id":103,"lines":[{"id":31,"code":"ROYAL_FMT_310","name":"Others","value":"Historic"}]}
          ],
          "order_no":"SYNTHETIC"
        }

    def tearDown(self):
        self.db.close()

    def test_groups_and_disambiguated_others_with_identical_options_and_values(self):
        result=display_order_detail(self.db,self.original)
        entry=result["items"][0]["lines"]
        self.assertEqual([x["section_name"] for x in entry],
                         ["Macroscopy","Macroscopy","Microscopy",
                          "Microscopy","Microscopy","Microscopy","Microscopy"])
        self.assertEqual([x["name"] for x in entry][-3:],
                         ["Others (Listed Findings)","Others (Additional Notes)","Yeast"])
        for orig,new in zip(self.original["items"][0]["lines"],entry):
            self.assertEqual(new["id"],orig["id"])
            self.assertEqual(new["code"],orig["code"])
            self.assertEqual(new["value"],orig["value"])
            self.assertEqual(new.get("royal_lab_field"),orig.get("royal_lab_field"))
        self.assertEqual(result["order_no"],"SYNTHETIC")
        self.assertEqual(result["items"][1],self.original["items"][1])
        self.assertEqual(result["items"][2],self.original["items"][2])
        self.assertNotIn("section_name",self.original["items"][0]["lines"][0])

    def test_unrelated_and_signed_orders_remain_unmodified(self):
        r=display_order_detail(self.db,self.original)
        self.assertIs(r["items"][1],self.original["items"][1])
        self.assertIs(r["items"][2],self.original["items"][2])

    def test_real_royal_source_confirms_15_active_stool_fields_and_both_others(self):
        lib=json.loads(SOURCE.read_text(encoding="utf-8-sig"))
        cat=native_catalog(lib)
        t=next(x for x in cat["tests"] if x["source_test_id"]=="8")
        self.assertEqual(t["name"],"STOOL GENERAL ANALYSIS")
        field={str(x["source_format_id"]):x for x in t["fields"]}
        for code in MACRO|MICRO:
            self.assertIn(code,field)
        self.assertEqual(field["310"]["source_analyte_id"],
                         field["896"]["source_analyte_id"])
        self.assertEqual(field["310"]["kind"],"select")
        self.assertEqual(field["896"]["kind"],"text")
        self.assertEqual(field["67"]["kind"],"select_or_text")
        self.assertEqual(field["73"]["kind"],"select_or_text")
        self.assertTrue(any(o["label"]=="E.histolytica" for o in field["73"]["options"]))
        self.assertTrue(any(o["label"]=="Schistosoma mansoni" for o in field["307"]["options"]))
        self.assertEqual(set(CUSTOM_LABELS),{"310","896"})

if __name__=="__main__":
    unittest.main()
