import pathlib,sqlite3,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"hospital"))
from royallab_nova_order_detail_types import attach_reviewed_types
class DetailOverlayTests(unittest.TestCase):
 def setUp(self):
  self.db=sqlite3.connect(":memory:")
  self.db.executescript("""CREATE TABLE hospital_order_items(id INTEGER PRIMARY KEY,test_id INTEGER);
 CREATE TABLE hospital_lab_parameters(id INTEGER PRIMARY KEY,test_id INTEGER,code TEXT,active INTEGER);
 CREATE TABLE hospital_lab_lines(id INTEGER PRIMARY KEY,item_id INTEGER,code TEXT,parameter_id INTEGER);
 INSERT INTO hospital_order_items VALUES(22,7);
 INSERT INTO hospital_lab_parameters VALUES(1,7,'ROYAL_FMT_20',1);
 INSERT INTO hospital_lab_lines VALUES(11,22,'ROYAL_FMT_20',1);""")
  self.items=[{"id":22,"lines":[{"id":11,"name":"Color","value":"Yellow"}]}]
  self.form={"review_flags":[],"fields":[{"source_format_id":"20","kind":"select","label":"Color",
    "options":[{"label":"Yellow","active":True},{"label":"Red","active":True}]}]}
 def test_metadata_overlay_no_mutation(self):
  result=attach_reviewed_types(self.db,self.items,{22:self.form})
  self.assertEqual(result[0]["lines"][0]["royal_lab_field"]["kind"],"select")
  self.assertEqual(result[0]["lines"][0]["royal_lab_field"]["options"],["Yellow","Red"])
  self.assertNotIn("royal_lab_field",self.items[0]["lines"][0])
 def test_string_item_id_cannot_receive_typed_overlay(self):
  forged=[{"id":"22","lines":[{"id":11,"name":"Color","value":"Yellow"}]}]
  result=attach_reviewed_types(self.db,forged,{22:self.form})
  self.assertNotIn("royal_lab_field",result[0]["lines"][0])
 def test_unreviewed_and_unknown_forms_fall_back(self):
  self.form["review_flags"]=["requires_review"]
  self.assertNotIn("royal_lab_field",attach_reviewed_types(self.db,self.items,{22:self.form})[0]["lines"][0])
  self.assertEqual(attach_reviewed_types(self.db,self.items,{})[0]["lines"],self.items[0]["lines"])
if __name__=="__main__":unittest.main()
