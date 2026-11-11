import importlib.util,json,pathlib,sqlite3,tempfile,unittest
from contextlib import closing
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("runner",ROOT/".github/ci/royallab_import_offline.py")
runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
class ImportTests(unittest.TestCase):
 def test_copy_only_import_and_repeat(self):
  with tempfile.TemporaryDirectory() as d:
   d=pathlib.Path(d);db=d/"copy.db";library=d/"library.json";options=d/"unlinked.json"
   with closing(sqlite3.connect(db)) as c:
    c.execute("CREATE TABLE hospital_lab_tests(id INTEGER PRIMARY KEY,name TEXT)")
    c.execute("INSERT INTO hospital_lab_tests VALUES(7,'original')")
   library.write_text(json.dumps({"tests":[{"TestID":str(i),"Name":"T"} for i in range(367)],
       "analytes":[{"analyte_id":str(i),"test_id":str(i%367),"name":"A","result_formats":[]} for i in range(1245)]}))
   options.write_text(json.dumps([{"ColoseEndedResultOptionID":str(i),"reason":"missing_closed_format"} for i in range(2551)]))
   first=runner.run(db,library,options);second=runner.run(db,library,options)
   self.assertEqual(first["batch_id"],second["batch_id"])
   self.assertEqual(first["counts"]["royal_lab_source_analytes"],1245)
   with sqlite3.connect(db) as c:
    self.assertEqual(c.execute("SELECT * FROM hospital_lab_tests").fetchall(),[(7,"original")])
 def test_refuse_nonexistent_database(self):
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaises(ValueError):runner.run(pathlib.Path(d)/"missing.db","unused","unused")
if __name__=="__main__":unittest.main()
