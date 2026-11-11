"""End-to-end reviewed parameter lifecycle on an isolated SQLite NOVA-compatible schema."""
import pathlib,sqlite3,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"hospital"))
from royallab_nova_parameter_plan import plan_existing_parameters
from royallab_nova_parameter_install import install_reviewed_parameters
from royallab_nova_parameter_activation import activate_reviewed_parameters
class ReviewedLifecycle(unittest.TestCase):
 def test_existing_catalog_patient_result_and_price_survive(self):
  db=sqlite3.connect(":memory:")
  db.executescript("""CREATE TABLE hospital_lab_tests(id INTEGER PRIMARY KEY,code TEXT,price INTEGER);
 CREATE TABLE hospital_lab_parameters(id INTEGER PRIMARY KEY,test_id INTEGER,code TEXT,name TEXT,unit TEXT,reference_all TEXT,reference_male TEXT,reference_female TEXT,sort_order INTEGER,active INTEGER,UNIQUE(test_id,code));
 CREATE TABLE hospital_order_items(id INTEGER PRIMARY KEY,test_id INTEGER);
 CREATE TABLE hospital_lab_lines(id INTEGER PRIMARY KEY,item_id INTEGER,code TEXT,value TEXT);
 INSERT INTO hospital_lab_tests VALUES(7,'URINE',3500);
 INSERT INTO hospital_lab_parameters VALUES(1,7,'OLD','Old Field','/HPF','1-2','','',1,1);
 INSERT INTO hospital_lab_lines VALUES(1,90,'OLD','old patient value');""")
  fields=[{"source_format_id":"18","kind":"select","label":"Color","unit":""},
          {"source_format_id":"19","kind":"number","label":"RBC","unit":"/HPF"}]
  before=db.execute("SELECT * FROM hospital_lab_lines").fetchall()
  self.assertEqual(len(plan_existing_parameters(db,7,fields)["missing"]),2)
  with self.assertRaises(PermissionError):install_reviewed_parameters(db,7,fields)
  install_reviewed_parameters(db,7,fields,approved=True)
  self.assertEqual(db.execute("SELECT COUNT(*) FROM hospital_lab_parameters WHERE active=0").fetchone()[0],2)
  self.assertTrue(plan_existing_parameters(db,7,fields)["ready"])
  with self.assertRaises(PermissionError):activate_reviewed_parameters(db,7,fields)
  activate_reviewed_parameters(db,7,fields,approved=True)
  self.assertEqual(db.execute("SELECT COUNT(*) FROM hospital_lab_parameters WHERE active=1").fetchone()[0],3)
  self.assertEqual(db.execute("SELECT * FROM hospital_lab_lines").fetchall(),before)
  self.assertEqual(db.execute("SELECT price FROM hospital_lab_tests").fetchone()[0],3500)
  self.assertEqual(db.execute("SELECT reference_all FROM hospital_lab_parameters WHERE id=1").fetchone()[0],"1-2")
  self.assertEqual(install_reviewed_parameters(db,7,fields,approved=True)["inserted"],0)
  db.close()
if __name__=="__main__":unittest.main()
