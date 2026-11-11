import pathlib,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"hospital"))
from royallab_result_preview import validate_preview
class ResultPreviewTests(unittest.TestCase):
 def setUp(self):
  self.form={"mode":"review_only","can_save_patient_results":False,"fields":[
   {"source_format_id":"1","source_analyte_id":"a","kind":"select","options":[{"label":"Positive"},{"label":"Negative"}]},
   {"source_format_id":"2","source_analyte_id":"b","kind":"number","unit":"mg/dL"},
   {"source_format_id":"3","source_analyte_id":"c","kind":"select_or_text","options":[{"label":"Few"}]},
   {"source_format_id":"4","source_analyte_id":"d","kind":"unknown"}]}
 def test_validate_preserves_exact_options_and_units(self):
  out=validate_preview(self.form,{"1":"Positive","2":"2.50","3":"Many"})
  self.assertEqual(out["results"]["1"]["status"],"valid_option")
  self.assertEqual(out["results"]["2"]["unit"],"mg/dL")
  self.assertEqual(out["results"]["3"]["status"],"valid_text")
  self.assertTrue(out["all_valid"])
 def test_unapproved_dropdown_and_unknown_are_not_accepted(self):
  out=validate_preview(self.form,{"1":"Invented","4":"any"})
  self.assertFalse(out["all_valid"])
  self.assertEqual(out["results"]["1"]["status"],"invalid")
  self.assertEqual(out["results"]["4"]["status"],"requires_review")
 def test_reject_nan_and_infinity(self):
  for x in ("NaN","Infinity","-Infinity"):
   with self.subTest(x=x):
    self.assertEqual(validate_preview(self.form,{"2":x})["results"]["2"]["status"],"invalid")
 def test_unknown_field_and_live_mode_rejected(self):
  with self.assertRaises(ValueError):validate_preview(self.form,{"99":"hi"})
  with self.assertRaises(ValueError):validate_preview({**self.form,"mode":"live"},{"1":"Positive"})
 def test_duplicate_field_id_rejected(self):
  with self.assertRaises(ValueError):validate_preview({**self.form,"fields":self.form["fields"]*2},{})
if __name__=="__main__":unittest.main()
