import pathlib,sqlite3,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from hospital.royallab_nova_live_order_overlay import diagnose_royallab_visibility

class VisibilityDiagnosisTests(unittest.TestCase):
 def setUp(self):
  self.c=sqlite3.connect(':memory:')
  self.detail={'items':[{'id':22,'test_id':7,'lines':[{'id':1,'value':'PRIVATE'}]}]}
 def tearDown(self):self.c.close()
 def test_missing_staging_is_explicit_and_patient_safe(self):
  d=diagnose_royallab_visibility(self.c,self.detail)
  self.assertEqual(d['status'],'source_or_bindings_not_installed')
  self.assertNotIn('PRIVATE',str(d))
 def test_binding_statuses(self):
  self.c.executescript("""CREATE TABLE royal_lab_import_batches(id INTEGER PRIMARY KEY);
  CREATE TABLE royal_lab_source_tests(batch_id INTEGER);
  CREATE TABLE royal_lab_approved_item_bindings(item_id INTEGER,batch_id INTEGER,reviewed INTEGER,clinical_approved INTEGER);
  """)
  self.assertEqual(diagnose_royallab_visibility(self.c,self.detail)['items'][0]['reason'],'no_item_binding')
  self.c.execute("INSERT INTO royal_lab_approved_item_bindings VALUES(22,1,0,0)")
  self.assertEqual(diagnose_royallab_visibility(self.c,self.detail)['items'][0]['reason'],'review_pending')
  self.c.execute("UPDATE royal_lab_approved_item_bindings SET reviewed=1")
  self.assertEqual(diagnose_royallab_visibility(self.c,self.detail)['items'][0]['reason'],'clinical_approval_pending')
  self.c.execute("UPDATE royal_lab_approved_item_bindings SET clinical_approved=1")
  self.assertEqual(diagnose_royallab_visibility(self.c,self.detail)['items'][0]['reason'],'approved_binding_present_check_field_mapping')
if __name__=='__main__':unittest.main()
