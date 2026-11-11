import unittest,sqlite3,importlib.util,pathlib
P=pathlib.Path(__file__).resolve().parents[2]/"hospital/royallab_staging.py"
spec=importlib.util.spec_from_file_location("royallab_staging",P)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def fixture():
 tests=[{"TestID":str(i),"Name":"T"+str(i)} for i in range(367)]
 analytes=[{"analyte_id":str(i),"test_id":str(i%367),"name":"A"+str(i)} for i in range(1245)]
 options=[{"ColoseEndedResultOptionID":str(i),"reason":"missing_closed_format"} for i in range(2551)]
 return {"tests":tests,"analytes":analytes},options
class StagingTests(unittest.TestCase):
 def test_isolated_idempotent_and_lossless(self):
  c=sqlite3.connect(":memory:");c.execute("CREATE TABLE hospital_lab_tests(id INTEGER PRIMARY KEY,name TEXT)");c.execute("INSERT INTO hospital_lab_tests VALUES(1,'untouched')")
  library,options=fixture();bid=m.stage(c,library,options,"sample-sha")
  self.assertEqual(m.verify(c,bid),{"royal_lab_source_tests":367,"royal_lab_source_analytes":1245,"royal_lab_unresolved_options":2551})
  self.assertEqual(m.stage(c,library,options,"sample-sha"),bid)
  self.assertEqual(c.execute("SELECT name FROM hospital_lab_tests").fetchall(),[("untouched",)])
 def test_invalid_counts_do_not_write(self):
  c=sqlite3.connect(":memory:");lib,opts=fixture();lib["tests"].pop()
  with self.assertRaises(ValueError):m.stage(c,lib,opts,"bad")
  self.assertEqual(c.execute("SELECT name FROM sqlite_master WHERE name='royal_lab_import_batches'").fetchall(),[])
if __name__=="__main__":unittest.main()
