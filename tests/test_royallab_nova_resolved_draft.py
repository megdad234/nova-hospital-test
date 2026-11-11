import pathlib,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"hospital"))
from royallab_nova_resolved_draft import save_resolved_review_draft
from tests.test_royallab_actual_nova_save import fixture,load_original_save
FORM={"mode":"review_only","can_save_patient_results":False,
      "fields":[{"source_format_id":"20","kind":"select","options":[{"label":"Positive"},{"label":"Negative"}]}]}
def setup(status="paid"):
 c=fixture(status)
 c.execute("ALTER TABLE hospital_order_items ADD COLUMN test_id INTEGER")
 c.execute("UPDATE hospital_order_items SET test_id=7 WHERE id=22")
 c.execute("CREATE TABLE hospital_lab_parameters(id INTEGER PRIMARY KEY,test_id INTEGER,code TEXT,active INTEGER)")
 c.execute("ALTER TABLE hospital_lab_lines ADD COLUMN parameter_id INTEGER")
 c.execute("INSERT INTO hospital_lab_parameters VALUES(1,7,'ROYAL_FMT_20',1)")
 c.execute("UPDATE hospital_lab_lines SET code='ROYAL_FMT_20',parameter_id=1 WHERE id=11")
 c.commit()
 return c
class ResolvedDraftTests(unittest.TestCase):
 def test_real_nova_save_with_resolved_source_format(self):
  c=setup()
  try:
   save_resolved_review_draft(c,{"id":7},FORM,{"20":"Positive"},22,0,load_original_save())
   self.assertEqual(c.execute("SELECT value FROM hospital_lab_lines WHERE id=11").fetchone()[0],"Positive")
   self.assertEqual(c.execute("SELECT result_status,result_version FROM hospital_order_items WHERE id=22").fetchone()[:],("draft",1))
   self.assertEqual(c.execute("SELECT COUNT(*) FROM hospital_lab_revisions").fetchone()[0],1)
  finally:c.close()
 def test_inactive_or_unpaid_never_saves(self):
  for inactive in (False,True):
   c=setup("paid" if inactive else "unpaid")
   try:
    if inactive:c.execute("UPDATE hospital_lab_parameters SET active=0")
    with self.assertRaises((ValueError,PermissionError)):
     save_resolved_review_draft(c,{"id":7},FORM,{"20":"Positive"},22,0,load_original_save())
    self.assertEqual(c.execute("SELECT COUNT(*) FROM hospital_lab_revisions").fetchone()[0],0)
   finally:c.close()
if __name__=="__main__":unittest.main()
