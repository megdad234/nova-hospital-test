import pathlib,sqlite3,sys,unittest
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from hospital.royallab_nova_live_order_overlay import overlay_order_detail
from hospital.royallab_nova_binding_schema import create_schema
class ClinicalBindingIntegrationTests(unittest.TestCase):
 def setUp(self):
  self.c=sqlite3.connect(':memory:')
  self.c.executescript("""CREATE TABLE hospital_order_items(id INTEGER PRIMARY KEY,test_id INTEGER);
 CREATE TABLE hospital_lab_tests(id INTEGER PRIMARY KEY);
 CREATE TABLE royal_lab_import_batches(id INTEGER PRIMARY KEY);
 CREATE TABLE hospital_lab_parameters(id INTEGER PRIMARY KEY,test_id INTEGER,code TEXT,active INTEGER);
 CREATE TABLE hospital_lab_lines(id INTEGER PRIMARY KEY,item_id INTEGER,code TEXT,parameter_id INTEGER);
 INSERT INTO hospital_lab_tests VALUES(7);
 INSERT INTO hospital_order_items VALUES(22,7);
 INSERT INTO royal_lab_import_batches VALUES(1);
 INSERT INTO hospital_lab_parameters VALUES(10,7,'ROYAL_FMT_20',1);
 INSERT INTO hospital_lab_lines VALUES(11,22,'ROYAL_FMT_20',10);""")
  create_schema(self.c)
  self.detail={'id':5,'items':[{'id':22,'test_id':7,'lines':[{'id':11,'name':'Color','value':'Yellow'}]}]}
  self.form={'source_test_id':'7','review_flags':[],'fields':[{'source_format_id':'20','kind':'select','label':'Color','options':[{'label':'Yellow','active':True},{'label':'Red','active':True},{'label':'Turbid','active':'False'}]}]}
 def tearDown(self):self.c.close()
 def test_only_clinically_approved_exact_binding_gets_dropdown(self):
  self.c.execute("""INSERT INTO royal_lab_approved_item_bindings
  (item_id,batch_id,nova_test_id,source_test_id,reviewed,reviewed_by,reviewed_at)
  VALUES(22,1,7,'7',1,3,'2026-11-11')""")
  with patch('hospital.royallab_nova_binding_loader.test_form',return_value=self.form) as loader:
   self.assertIs(overlay_order_detail(self.c,self.detail,'lab'),self.detail)
   loader.assert_not_called()
   self.c.execute('UPDATE royal_lab_approved_item_bindings SET clinical_approved=1')
   typed=overlay_order_detail(self.c,self.detail,'lab')
  self.assertEqual(typed['items'][0]['lines'][0]['royal_lab_field']['options'],['Yellow','Red'])
  self.assertNotIn('royal_lab_field',self.detail['items'][0]['lines'][0])
  self.assertIs(overlay_order_detail(self.c,self.detail,'cashier'),self.detail)
if __name__=='__main__':unittest.main()
