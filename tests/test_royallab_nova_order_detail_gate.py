import pathlib,sqlite3,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"hospital"))
from royallab_nova_order_detail_gate import reviewed_order_detail
class DetailGateTests(unittest.TestCase):
 def setUp(self):
  self.db=sqlite3.connect(":memory:")
  self.db.executescript("""CREATE TABLE hospital_order_items(id INTEGER PRIMARY KEY,test_id INTEGER);
 CREATE TABLE hospital_lab_parameters(id INTEGER PRIMARY KEY,test_id INTEGER,code TEXT,active INTEGER);
 CREATE TABLE hospital_lab_lines(id INTEGER PRIMARY KEY,item_id INTEGER,code TEXT,parameter_id INTEGER);
 INSERT INTO hospital_order_items VALUES(22,7);
 INSERT INTO hospital_lab_parameters VALUES(1,7,'ROYAL_FMT_20',1);
 INSERT INTO hospital_lab_lines VALUES(11,22,'ROYAL_FMT_20',1);""")
  self.detail={"id":5,"items":[{"id":22,"lines":[{"id":11,"name":"Color","value":""}]}]}
  self.form={"source_test_id":"7","review_flags":[],"fields":[{"source_format_id":"20","kind":"select","label":"Color","options":[{"label":"Yellow"},{"label":"Red"}]}]}
 def test_explicit_reviewed_binding_only(self):
  binding={22:{"item_id":22,"reviewed":True,"form":self.form}}
  typed=reviewed_order_detail(self.db,self.detail,binding)
  self.assertEqual(typed["items"][0]["lines"][0]["royal_lab_field"]["options"],["Yellow","Red"])
  self.assertNotIn("royal_lab_field",self.detail["items"][0]["lines"][0])
 def test_wrong_item_or_unreviewed_falls_back(self):
  for b in ({22:{"item_id":99,"reviewed":True,"form":self.form}},
            {22:{"item_id":22,"reviewed":False,"form":self.form}},{}):
   self.assertNotIn("royal_lab_field",reviewed_order_detail(self.db,self.detail,b)["items"][0]["lines"][0])
 def test_duplicate_items_rejected(self):
  with self.assertRaises(ValueError):
   reviewed_order_detail(self.db,{"items":[self.detail["items"][0]]*2},{})
if __name__=="__main__":unittest.main()
