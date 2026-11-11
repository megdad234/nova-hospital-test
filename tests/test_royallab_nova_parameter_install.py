import pathlib,sqlite3,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"hospital"))
from royallab_nova_parameter_install import install_reviewed_parameters
class InstallTests(unittest.TestCase):
 def setUp(self):
  self.db=sqlite3.connect(":memory:")
  self.db.executescript("""CREATE TABLE hospital_lab_tests(id INTEGER PRIMARY KEY,price INTEGER);
  CREATE TABLE hospital_lab_parameters(id INTEGER PRIMARY KEY,test_id INTEGER,code TEXT,name TEXT,unit TEXT,reference_all TEXT,reference_male TEXT,reference_female TEXT,sort_order INTEGER,active INTEGER,UNIQUE(test_id,code));
  INSERT INTO hospital_lab_tests VALUES(7,2500);""")
  self.fields=[{"source_format_id":"18","kind":"select","label":"Color","unit":""},
               {"source_format_id":"19","kind":"number","label":"RBC","unit":"/HPF"}]
 def test_explicit_approval_inactive_idempotent_and_price_unchanged(self):
  with self.assertRaises(PermissionError):install_reviewed_parameters(self.db,7,self.fields)
  self.assertEqual(self.db.execute("SELECT count(*) FROM hospital_lab_parameters").fetchone()[0],0)
  r=install_reviewed_parameters(self.db,7,self.fields,approved=True)
  self.assertEqual(r["inserted"],2);self.assertFalse(r["clinical_approval"])
  self.assertEqual(self.db.execute("SELECT count(*) FROM hospital_lab_parameters WHERE active=0").fetchone()[0],2)
  self.assertEqual(install_reviewed_parameters(self.db,7,self.fields,approved=True)["inserted"],0)
  self.assertEqual(self.db.execute("SELECT price FROM hospital_lab_tests WHERE id=7").fetchone()[0],2500)
 def test_missing_test_and_unsupported_format_blocked(self):
  with self.assertRaises(ValueError):install_reviewed_parameters(self.db,8,self.fields,approved=True)
  with self.assertRaises(ValueError):install_reviewed_parameters(self.db,7,self.fields+[{"source_format_id":"20","kind":"unknown","label":"Unknown"}],approved=True)
  self.assertEqual(self.db.execute("SELECT count(*) FROM hospital_lab_parameters").fetchone()[0],0)
 def test_atomic_rollback_on_insert_error(self):
  self.db.execute("""CREATE TRIGGER reject_19 BEFORE INSERT ON hospital_lab_parameters
   WHEN NEW.code='ROYAL_FMT_19' BEGIN SELECT RAISE(FAIL,'reject'); END""")
  with self.assertRaises(sqlite3.IntegrityError):install_reviewed_parameters(self.db,7,self.fields,approved=True)
  self.assertEqual(self.db.execute("SELECT count(*) FROM hospital_lab_parameters").fetchone()[0],0)
if __name__=="__main__":unittest.main()
