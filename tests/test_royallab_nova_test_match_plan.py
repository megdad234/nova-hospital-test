import pathlib,sqlite3,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from hospital.royallab_nova_test_match_plan import propose_test_matches,canonical_name
class TestMatchPlan(unittest.TestCase):
 def setUp(self):
  self.c=sqlite3.connect(':memory:')
  self.c.execute("CREATE TABLE hospital_lab_tests(id INTEGER PRIMARY KEY,name TEXT)")
  self.c.executemany("INSERT INTO hospital_lab_tests VALUES(?,?)",[(1,'Urine General Examination'),(2,'Malaria'),(3,'Malaria')])
 def tearDown(self):self.c.close()
 def test_unique_exact_match_does_not_approve(self):
  result=propose_test_matches(self.c,[{'source_test_id':'10','name':' urine  GENERAL examination '}])
  self.assertEqual(result['proposals'][0]['nova_test_id'],1)
  self.assertFalse(result['proposals'][0]['approved'])
  self.assertEqual(result['live_bindings_created'],0)
 def test_ambiguous_and_unknown_do_not_map(self):
  result=propose_test_matches(self.c,[{'source_test_id':'11','name':'Malaria'},{'source_test_id':'12','name':'CBC'}])
  self.assertEqual(result['proposals'],[])
  self.assertEqual([x['reason'] for x in result['review_required']],['duplicate_nova_name','no_exact_nova_name'])
 def test_source_duplicate_and_review_flag(self):
  result=propose_test_matches(self.c,[{'source_test_id':'10','name':'Urine General Examination'},{'source_test_id':'11','name':'urine general examination'}])
  self.assertEqual(result['proposals'],[])
  self.assertTrue(all(x['reason']=='duplicate_source_name' for x in result['review_required']))
  result=propose_test_matches(self.c,[{'source_test_id':'10','name':'Urine General Examination','review_flags':['unknown_format']}])
  self.assertEqual(result['review_required'][0]['reason'],'source_review_flags')
 def test_arabic_normalization(self):
  self.assertEqual(canonical_name('فَحصُ البَول'),canonical_name('فحص البول'))
if __name__=='__main__':unittest.main()
