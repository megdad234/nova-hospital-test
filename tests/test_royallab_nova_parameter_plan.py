import pathlib,sqlite3,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"hospital"))
from royallab_nova_parameter_plan import plan_existing_parameters,source_code
class ParameterPlanTests(unittest.TestCase):
 def setUp(self):
  self.db=sqlite3.connect(":memory:")
  self.db.execute("CREATE TABLE hospital_lab_parameters(id INTEGER PRIMARY KEY,test_id INTEGER,code TEXT,name TEXT,unit TEXT)")
  self.db.execute("INSERT INTO hospital_lab_parameters VALUES(11,3,'ROYAL_FMT_123','Color','')")
  self.db.execute("INSERT INTO hospital_lab_parameters VALUES(12,4,'ROYAL_FMT_123','Other','')")
 def test_exact_id_and_test_scope(self):
  p=plan_existing_parameters(self.db,3,[{"source_format_id":"123","kind":"select","label":"Color","unit":""}])
  self.assertTrue(p["ready"]);self.assertEqual(p["mapped"][0]["parameter_id"],11)
  self.assertFalse(p["writes"]);self.assertFalse(p["clinical_approval"])
 def test_never_fuzzy_match_or_change_existing(self):
  p=plan_existing_parameters(self.db,3,[{"source_format_id":"123","kind":"text","label":"Colour","unit":""},{"source_format_id":"124","kind":"number","label":"RBC","unit":"/HPF"}])
  self.assertEqual(len(p["blocked"]),1);self.assertEqual(len(p["missing"]),1)
  self.assertEqual(self.db.execute("SELECT name FROM hospital_lab_parameters WHERE id=11").fetchone()[0],"Color")
 def test_inactive_source_never_installed_or_activated(self):
  for value in (False,0,"False","false","0"):
   with self.subTest(value=value):
    p=plan_existing_parameters(self.db,3,[{"source_format_id":"123","kind":"select","label":"Color","unit":"","active":value}])
    self.assertFalse(p["ready"])
    self.assertEqual(p["blocked"][0]["reason"],"inactive_source_analyte")
    self.assertFalse(p["mapped"])
    self.assertFalse(p["missing"])
 def test_reject_unsupported_and_duplicate(self):
  p=plan_existing_parameters(self.db,3,[{"source_format_id":"5","kind":"unknown","label":"Unknown"}])
  self.assertEqual(p["blocked"][0]["reason"],"unsupported_format")
  with self.assertRaises(ValueError):plan_existing_parameters(self.db,3,[{"source_format_id":"5","kind":"text","label":"A"},{"source_format_id":"5","kind":"text","label":"B"}])
  with self.assertRaises(ValueError):source_code("5;DROP TABLE")
if __name__=="__main__":unittest.main()
