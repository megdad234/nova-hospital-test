import pathlib,sqlite3,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"hospital"))
from royallab_nova_line_mapping import verify_line_mapping
class MappingTests(unittest.TestCase):
 def setUp(self):
  self.c=sqlite3.connect(":memory:")
  self.c.executescript("""
   CREATE TABLE hospital_lab_lines(id INTEGER PRIMARY KEY,item_id INTEGER,code TEXT,name TEXT,unit TEXT);
   INSERT INTO hospital_lab_lines VALUES(11,22,'WBC','White blood cells','10^9/L');
   INSERT INTO hospital_lab_lines VALUES(12,23,'WBC','White blood cells','10^9/L');
  """)
 def tearDown(self):self.c.close()
 def test_valid_mapping_read_only(self):
  before=self.c.total_changes
  out=verify_line_mapping(self.c,22,{"royal1":11})
  self.assertEqual(out["mapped_lines"]["royal1"]["code"],"WBC")
  self.assertFalse(out["clinical_approval"])
  self.assertEqual(before,self.c.total_changes)
 def test_cross_order_and_duplicate_mapping_rejected(self):
  for mapping in ({"royal1":12},{"royal1":11,"royal2":11},{"royal1":True}):
   with self.subTest(mapping=mapping),self.assertRaises(ValueError):
    verify_line_mapping(self.c,22,mapping)
if __name__=="__main__":unittest.main()
