import unittest,importlib.util,pathlib
p=pathlib.Path(__file__).resolve().parents[1]/"hospital/royallab_field_adapter.py"
s=importlib.util.spec_from_file_location("adapter",p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class AdapterTests(unittest.TestCase):
 def test_all_tests_and_orphan_analytes_preserved(self):
  tests=[{"TestID":str(i),"Name":"T"+str(i)} for i in range(367)]
  analytes=[{"analyte_id":str(i),"test_id":str(i%367),"name":"A","result_formats":[]} for i in range(1245)]
  analytes[0]["test_id"]="9999"
  analytes[1]["result_formats"]=[{"id":"1","types":["ColoseEndedResultFormat"],"options":[{"id":"1","label":"Positive"},{"id":"2","label":"Negative"}]}]
  analytes[3]["result_formats"]=[{"id":"3","types":["ColoseEndedResultFormat","StringResultFormat"],"options":[{"id":"3","label":"Trace"}]}]
  analytes[2]["result_formats"]=[{"id":"2","types":["DoubleResultFormat"],"unit":"mg/dL","options":[]}]
  result=m.build_fields({"tests":tests,"analytes":analytes})
  self.assertEqual(len(result["tests"]),367)
  self.assertEqual(len(result["detached_analytes"]),1)
  self.assertEqual(sum(len(t["fields"]) for t in result["tests"])+sum(len(x["fields"]) for x in result["detached_analytes"]),1245)
  fields=[f for t in result["tests"] for f in t["fields"]]
  self.assertEqual(next(f for f in fields if f["source_format_id"]=="1")["kind"],"select")
  self.assertEqual(next(f for f in fields if f["source_format_id"]=="2")["unit"],"mg/dL")
  self.assertEqual(next(f for f in fields if f["source_format_id"]=="3")["kind"],"select_or_text")
 def test_reject_partial_source(self):
  with self.assertRaises(ValueError):m.build_fields({"tests":[],"analytes":[]})
if __name__=="__main__":unittest.main()
