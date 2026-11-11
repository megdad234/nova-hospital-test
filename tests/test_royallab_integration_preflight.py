import pathlib,sqlite3,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"hospital"))
from royallab_staging import stage
from royallab_integration_preflight import integration_preflight
class PreflightTests(unittest.TestCase):
 def test_flags_unknown_without_enabling_live_entry(self):
  with sqlite3.connect(":memory:") as c:
   tests=[{"TestID":str(i),"Name":"Test"} for i in range(367)]
   analytes=[{"analyte_id":str(i),"test_id":str(i%367),"name":"Field","result_formats":[]} for i in range(1245)]
   options=[{"ColoseEndedResultOptionID":str(i),"reason":"missing"} for i in range(2551)]
   batch=stage(c,{"tests":tests,"analytes":analytes},options,"preflight-test")
   before=c.total_changes
   result=integration_preflight(c,batch)
   self.assertEqual(result["source_field_count"],1245)
   self.assertEqual(result["blocked_field_issues"],1245)
   self.assertEqual(result["review_flags"]["unsupported:unknown"],1245)
   self.assertFalse(result["may_enable_live_entry"])
   self.assertEqual(c.total_changes,before)
if __name__=="__main__":unittest.main()
