import json,pathlib,sqlite3,sys,tempfile,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"hospital"))
from royallab_staging import stage
from royallab_catalog_preview import catalog,test_form
class CatalogPreviewTests(unittest.TestCase):
 def test_preview_is_read_only_and_preserves_options(self):
  with sqlite3.connect(":memory:") as c:
   c.execute("CREATE TABLE hospital_lab_tests(id INTEGER PRIMARY KEY, name TEXT)")
   c.execute("INSERT INTO hospital_lab_tests VALUES(9,'original')")
   tests=[{"TestID":str(i),"Name":"Test "+str(i)} for i in range(367)]
   analytes=[{"analyte_id":str(i),"test_id":str(i%367),"name":"Field "+str(i),
    "result_formats":[{"id":str(i),"title":"Field "+str(i),"types":["ColoseEndedResultFormat"],
      "options":[{"id":"o"+str(i),"label":"Positive","order":1}]}]} for i in range(1245)]
   unresolved=[{"ColoseEndedResultOptionID":str(i),"reason":"missing"} for i in range(2551)]
   batch=stage(c,{"tests":tests,"analytes":analytes},unresolved,"sha256-fixture")
   before=c.total_changes
   full=catalog(c,batch)
   self.assertEqual(len(full["tests"]),367)
   self.assertFalse(full["clinical_approval"])
   form=test_form(c,batch,"0")
   self.assertEqual(form["mode"],"review_only")
   self.assertFalse(form["can_save_patient_results"])
   self.assertEqual(form["fields"][0]["kind"],"select")
   self.assertEqual(form["fields"][0]["options"][0]["label"],"Positive")
   self.assertEqual(before,c.total_changes)
   self.assertEqual(c.execute("SELECT * FROM hospital_lab_tests").fetchall(),[(9,"original")])
   with self.assertRaises(KeyError):test_form(c,batch,"missing")
if __name__=="__main__":unittest.main()
