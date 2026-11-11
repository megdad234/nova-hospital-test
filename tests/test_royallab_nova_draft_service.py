import pathlib,sqlite3,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"hospital"))
from royallab_nova_draft_service import save_reviewed_draft
from tests.test_royallab_actual_nova_save import fixture,load_original_save,FORM
class DraftServiceTests(unittest.TestCase):
 def test_save_via_original_nova_with_verified_line(self):
  c=fixture()
  try:
   payloads=[]
   def original(conn,actor,payload):
    payloads.append(payload)
    return load_original_save()(conn,actor,payload)
   save_reviewed_draft(c,{"id":7},FORM,{"r1":"Positive"},{"r1":11},22,0,original)
   self.assertEqual(len(payloads),1)
   self.assertIs(payloads[0]["publish"],False)
   self.assertEqual(c.execute("SELECT value FROM hospital_lab_lines WHERE id=11").fetchone()[0],"Positive")
   self.assertEqual(c.execute("SELECT result_status FROM hospital_order_items WHERE id=22").fetchone()[0],"draft")
  finally:c.close()
 def test_approved_result_is_never_downgraded(self):
  c=fixture()
  try:
   c.execute("UPDATE hospital_order_items SET result_status='approved' WHERE id=22")
   calls=[]
   with self.assertRaises(PermissionError):
    save_reviewed_draft(c,{"id":7},FORM,{"r1":"Positive"},{"r1":11},22,0,lambda *a:calls.append(1))
   self.assertEqual(calls,[])
   self.assertEqual(c.execute("SELECT result_status FROM hospital_order_items WHERE id=22").fetchone()[0],"approved")
  finally:c.close()
 def test_unpaid_and_stale_rejected_before_save(self):
  for status,version,exception in (("unpaid",0,PermissionError),("paid",9,ValueError)):
   c=fixture(status)
   try:
    calls=[]
    with self.assertRaises(exception):
     save_reviewed_draft(c,{"id":7},FORM,{"r1":"Positive"},{"r1":11},22,version,lambda *a:calls.append(1))
    self.assertEqual(calls,[])
   finally:c.close()
 def test_cross_order_line_rejected_before_save(self):
  c=fixture()
  try:
   c.execute("INSERT INTO hospital_lab_lines(id,item_id,value,modified_at,source,code,name,unit) VALUES(12,99,'',NULL,'manual','R1','Royal result','')")
   called=[]
   with self.assertRaises(ValueError):
    save_reviewed_draft(c,{"id":7},FORM,{"r1":"Positive"},{"r1":12},22,0,lambda *a:called.append(1))
   self.assertEqual(called,[])
   self.assertEqual(c.execute("SELECT COUNT(*) FROM hospital_lab_revisions").fetchone()[0],0)
  finally:c.close()
if __name__=="__main__":unittest.main()
