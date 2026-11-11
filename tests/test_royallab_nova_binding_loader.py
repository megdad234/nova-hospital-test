import pathlib,sqlite3,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'hospital'))
from royallab_nova_binding_loader import load_reviewed_bindings
from royallab_nova_binding_schema import create_schema
class BindingLoaderTests(unittest.TestCase):
 def setUp(self):
  self.c=sqlite3.connect(':memory:')
  self.c.executescript("""CREATE TABLE hospital_order_items(id INTEGER PRIMARY KEY,test_id INTEGER);
 CREATE TABLE hospital_lab_tests(id INTEGER PRIMARY KEY);
 CREATE TABLE royal_lab_import_batches(id INTEGER PRIMARY KEY);
 INSERT INTO hospital_lab_tests VALUES(7),(8);
 INSERT INTO hospital_order_items VALUES(22,7);
 INSERT INTO royal_lab_import_batches VALUES(1);""")
 def tearDown(self):self.c.close()
 def test_missing_approval_table_never_enables_typed_fields(self):
  self.assertEqual(load_reviewed_bindings(self.c,[{'id':22}],1),{})
  self.assertEqual(load_reviewed_bindings(self.c,[{'id':22}],0),{})
 def test_schema_creates_no_approval_and_rejects_wrong_test(self):
  create_schema(self.c)
  self.assertEqual(self.c.execute('SELECT COUNT(*) FROM royal_lab_approved_item_bindings').fetchone()[0],0)
  self.c.execute("""INSERT INTO royal_lab_approved_item_bindings
    (item_id,batch_id,nova_test_id,source_test_id,reviewed,reviewed_by,reviewed_at)
    VALUES(22,1,8,'7',1,3,'2026-11-11')""")
  self.assertEqual(load_reviewed_bindings(self.c,[{'id':22,'test_id':7}],1),{})
 def test_unreviewed_binding_rejected(self):
  create_schema(self.c)
  self.c.execute("""INSERT INTO royal_lab_approved_item_bindings
   (item_id,batch_id,nova_test_id,source_test_id) VALUES(22,1,7,'7')""")
  self.assertEqual(load_reviewed_bindings(self.c,[{'id':22}],1),{})
 def test_approval_without_reviewer_rejected_by_database(self):
  create_schema(self.c)
  with self.assertRaises(sqlite3.IntegrityError):
   self.c.execute("""INSERT INTO royal_lab_approved_item_bindings
    (item_id,batch_id,nova_test_id,source_test_id,reviewed)
    VALUES(22,1,7,'7',1)""")
if __name__=='__main__':unittest.main()
