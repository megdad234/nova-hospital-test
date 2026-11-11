import pathlib,sqlite3,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'hospital'))
from royallab_nova_binding_loader import load_reviewed_bindings
class BindingLoaderTests(unittest.TestCase):
 def test_no_approval_table_means_no_typed_fields(self):
  c=sqlite3.connect(':memory:')
  try:
   self.assertEqual(load_reviewed_bindings(c,[{'id':22}],1),{})
   self.assertEqual(load_reviewed_bindings(c,[{'id':22}],0),{})
  finally:c.close()
 def test_unreviewed_binding_never_loads_source_form(self):
  c=sqlite3.connect(':memory:')
  try:
   c.execute('CREATE TABLE royal_lab_approved_item_bindings(item_id INTEGER,batch_id INTEGER,source_test_id TEXT,reviewed INTEGER,source_test_code TEXT)')
   c.execute("INSERT INTO royal_lab_approved_item_bindings VALUES(22,1,'7',0,'LAB')")
   self.assertEqual(load_reviewed_bindings(c,[{'id':22}],1),{})
  finally:c.close()
if __name__=='__main__':unittest.main()
