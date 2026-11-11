import pathlib,sqlite3,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"hospital"))
from royallab_nova_parameter_install import install_reviewed_parameters
from royallab_nova_parameter_activation import activate_reviewed_parameters
class ActivationTests(unittest.TestCase):
 def setUp(self):
  self.db=sqlite3.connect(":memory:")
  self.db.executescript("""CREATE TABLE hospital_lab_tests(id INTEGER PRIMARY KEY,price INTEGER);
 CREATE TABLE hospital_lab_parameters(id INTEGER PRIMARY KEY,test_id INTEGER,code TEXT,name TEXT,unit TEXT,reference_all TEXT,reference_male TEXT,reference_female TEXT,sort_order INTEGER,active INTEGER,UNIQUE(test_id,code));
 CREATE TABLE hospital_order_items(id INTEGER PRIMARY KEY,test_id INTEGER);
 CREATE TABLE hospital_lab_lines(id INTEGER PRIMARY KEY,item_id INTEGER,code TEXT,value TEXT);
 INSERT INTO hospital_lab_tests VALUES(7,2500);
 INSERT INTO hospital_lab_lines VALUES(1,11,'OLD','patient result');""")
  self.fields=[{"source_format_id":"18","kind":"number","label":"RBC","unit":"/HPF"}]
 def test_activation_only_after_review_and_no_patient_mutations(self):
  install_reviewed_parameters(self.db,7,self.fields,approved=True)
  with self.assertRaises(PermissionError):activate_reviewed_parameters(self.db,7,self.fields)
  self.assertEqual(self.db.execute("SELECT active FROM hospital_lab_parameters").fetchone()[0],0)
  out=activate_reviewed_parameters(self.db,7,self.fields,approved=True)
  self.assertEqual(out["existing_order_lines_changed"],0)
  self.assertEqual(self.db.execute("SELECT active FROM hospital_lab_parameters").fetchone()[0],1)
  self.assertEqual(self.db.execute("SELECT value FROM hospital_lab_lines").fetchone()[0],"patient result")
  self.assertEqual(self.db.execute("SELECT price FROM hospital_lab_tests").fetchone()[0],2500)
 def test_missing_field_prevents_partial_activation(self):
  install_reviewed_parameters(self.db,7,self.fields,approved=True)
  extra={"source_format_id":"19","kind":"text","label":"Color","unit":""}
  with self.assertRaises(ValueError):activate_reviewed_parameters(self.db,7,self.fields+[extra],approved=True)
  self.assertEqual(self.db.execute("SELECT active FROM hospital_lab_parameters").fetchone()[0],0)
if __name__=="__main__":unittest.main()
