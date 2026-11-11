import pathlib,sqlite3,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'hospital'))
from royallab_nova_live_order_overlay import overlay_order_detail
from royallab_nova_binding_schema import create_schema
class LiveOverlayTests(unittest.TestCase):
 def setUp(self):
  self.c=sqlite3.connect(':memory:')
  self.c.executescript("""CREATE TABLE hospital_order_items(id INTEGER PRIMARY KEY,test_id INTEGER);
 CREATE TABLE hospital_lab_tests(id INTEGER PRIMARY KEY);
 CREATE TABLE royal_lab_import_batches(id INTEGER PRIMARY KEY);
 INSERT INTO hospital_lab_tests VALUES(7);
 INSERT INTO hospital_order_items VALUES(22,7);
 INSERT INTO royal_lab_import_batches VALUES(1);""")
  self.detail={'id':5,'items':[{'id':22,'test_id':7,'lines':[{'id':11,'name':'Color','value':'Yellow'}]}]}
 def tearDown(self):self.c.close()
 def test_legacy_response_unchanged_without_bindings(self):
  self.assertIs(overlay_order_detail(self.c,self.detail,'lab'),self.detail)
  create_schema(self.c)
  self.assertIs(overlay_order_detail(self.c,self.detail,'lab'),self.detail)
 def test_nonclinical_roles_never_receive_overlay(self):
  create_schema(self.c)
  for role in ('reception','cashier','frontdesk','patient'):
   self.assertIs(overlay_order_detail(self.c,self.detail,role),self.detail)
 def test_unreviewed_binding_preserves_legacy(self):
  create_schema(self.c)
  self.c.execute("""INSERT INTO royal_lab_approved_item_bindings
  (item_id,batch_id,nova_test_id,source_test_id) VALUES(22,1,7,'7')""")
  self.assertIs(overlay_order_detail(self.c,self.detail,'lab'),self.detail)
if __name__=='__main__':unittest.main()
