import pathlib,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"hospital"))
from royallab_nova_save_bridge import prepare_nova_save_payload
class BridgeTests(unittest.TestCase):
 def setUp(self):
  self.form={"mode":"review_only","can_save_patient_results":False,"fields":[
   {"source_format_id":"r1","kind":"select","options":[{"label":"Positive"},{"label":"Negative"}]},
   {"source_format_id":"r2","kind":"number","unit":"mg/dL"},
   {"source_format_id":"r3","kind":"unknown"}]}
 def test_draft_payload_matches_existing_nova_save_contract(self):
  p=prepare_nova_save_payload(self.form,{"r1":"Negative","r2":"5.0"},{"r1":11,"r2":12},22,3)
  self.assertEqual(p["values"],[{"line_id":11,"value":"Negative"},{"line_id":12,"value":"5.0"}])
  self.assertEqual(p["expected_version"],3)
  self.assertIs(p["publish"],False)
  self.assertEqual(p["source"],"manual")
 def test_reject_unmapped_invalid_unknown_and_duplicate_lines(self):
  cases=[({"r1":"Positive"},{"r2":12}),({"r1":"Invented"},{"r1":11}),
         ({"r3":"value"},{"r3":13}),({"r1":"Positive","r2":"5"},{"r1":11,"r2":11})]
  for entered,mapping in cases:
   with self.subTest(entered=entered,mapping=mapping),self.assertRaises(ValueError):
    prepare_nova_save_payload(self.form,entered,mapping,22,0)
 def test_reject_live_form(self):
  with self.assertRaises(ValueError):
   prepare_nova_save_payload({**self.form,"mode":"live"},{"r1":"Positive"},{"r1":11},22,0)
if __name__=="__main__":unittest.main()
