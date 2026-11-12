import unittest,importlib.util,pathlib
p=pathlib.Path(__file__).resolve().parents[1]/"hospital/royallab_field_adapter.py"
s=importlib.util.spec_from_file_location("adapter",p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class AdapterTests(unittest.TestCase):
 def test_all_tests_and_orphan_analytes_preserved(self):
  tests=[{"TestID":str(i),"Name":"T"+str(i)} for i in range(367)]
  analytes=[{"analyte_id":str(i),"test_id":str(i%367),"name":"A","result_formats":[]} for i in range(1245)]
  analytes[0]["test_id"]="9999"
  analytes[1]["name"]="Colour"
  analytes[1]["result_formats"]=[{"id":"1","title":"   ","types":["ColoseEndedResultFormat"],"options":[{"id":"1","label":"Positive"},{"id":"2","label":"Negative"}]}]
  analytes[3]["result_formats"]=[{"id":"3","types":["ColoseEndedResultFormat","StringResultFormat"],"options":[{"id":"3","label":"Trace"}]}]
  analytes[2]["result_formats"]=[{"id":"2","types":["DoubleResultFormat"],"unit":"mg/dL","options":[]}]
  result=m.build_fields({"tests":tests,"analytes":analytes})
  self.assertEqual(len(result["tests"]),367)
  self.assertEqual(len(result["detached_analytes"]),1)
  self.assertEqual(sum(len(t["fields"]) for t in result["tests"])+sum(len(x["fields"]) for x in result["detached_analytes"]),1245)
  fields=[f for t in result["tests"] for f in t["fields"]]
  self.assertEqual(next(f for f in fields if f["source_format_id"]=="1")["kind"],"select")
  self.assertEqual(next(f for f in fields if f["source_format_id"]=="1")["label"],"Colour")
  self.assertEqual(next(f for f in fields if f["source_format_id"]=="2")["unit"],"mg/dL")
  self.assertEqual(next(f for f in fields if f["source_format_id"]=="3")["kind"],"select_or_text")
 def test_duplicate_test_identity_is_rejected(self):
  tests=[{"TestID":str(i),"Name":"Test"} for i in range(367)]
  tests[-1]["TestID"]="0"
  analytes=[{"analyte_id":str(i),"test_id":"0","name":"A","result_formats":[]} for i in range(1245)]
  with self.assertRaisesRegex(ValueError,"duplicate source test IDs"):
   m.build_fields({"tests":tests,"analytes":analytes})
 def test_duplicate_field_identity_requires_review(self):
  tests=[{"TestID":str(i),"Name":"Test"} for i in range(367)]
  analytes=[{"analyte_id":str(i),"test_id":"0","name":"A","result_formats":[{"id":"shared" if i<2 else str(i),"types":["DoubleResultFormat"]}]} for i in range(1245)]
  result=m.build_fields({"tests":tests,"analytes":analytes})
  self.assertIn("duplicate_source_format_ids",result["tests"][0]["review_flags"])
 def test_inactive_and_duplicate_dropdown_options_flagged(self):
  tests=[{"TestID":str(i),"Name":"Test"} for i in range(367)]
  analytes=[{"analyte_id":str(i),"test_id":"0","name":"A","result_formats":[{"id":str(i),"types":["DoubleResultFormat"]}]} for i in range(1245)]
  analytes[0]["active"]=False
  analytes[1]["result_formats"]=[{"id":"1","types":["ColoseEndedResultFormat"],"options":[{"id":"x","label":"A"},{"id":"x","label":"B"}]}]
  result=m.build_fields({"tests":tests,"analytes":analytes})
  self.assertIn("inactive_source_field",result["tests"][0]["review_flags"])
  self.assertIn("missing_or_duplicate_source_option_ids",result["tests"][0]["review_flags"])
 def test_restores_proven_numeric_subtypes_from_source_foreign_keys(self):
  tests=[{"TestID":str(i),"Name":"T"+str(i)} for i in range(367)]
  analytes=[{"analyte_id":str(i),"test_id":"21","name":"A"+str(i),
             "result_formats":[{"id":str(10000+i),"types":["StringResultFormat"]}]} for i in range(1245)]
  analytes[0]["result_formats"]=[{"id":"258","types":["OpenEndedResultFormat"]}]
  analytes[1]["result_formats"]=[{"id":"564","types":["OpenEndedResultFormat","StringResultFormat"]}]
  result=m.build_fields({"tests":tests,"analytes":analytes})
  fields=result["tests"][21]["fields"]
  self.assertEqual(next(f for f in fields if f["source_format_id"]=="258")["kind"],"number")
  self.assertEqual(next(f for f in fields if f["source_format_id"]=="564")["kind"],"text")
  self.assertIn("DoubleResultFormat",next(f for f in fields if f["source_format_id"]=="258")["types"])
 def test_numeric_source_provenance_is_nonoverlapping(self):
  from hospital.royallab_source_numeric_format_map import (
   DOUBLE_RESULT_FORMAT_IDS, INTEGER_RESULT_FORMAT_IDS, SOURCE_COMMIT)
  self.assertEqual(len(DOUBLE_RESULT_FORMAT_IDS),490)
  self.assertEqual(len(INTEGER_RESULT_FORMAT_IDS),76)
  self.assertFalse(DOUBLE_RESULT_FORMAT_IDS.intersection(INTEGER_RESULT_FORMAT_IDS))
  self.assertIn("258",DOUBLE_RESULT_FORMAT_IDS)
  self.assertEqual(len(SOURCE_COMMIT),40)
 def test_reject_partial_source(self):
  with self.assertRaises(ValueError):m.build_fields({"tests":[],"analytes":[]})
if __name__=="__main__":unittest.main()
