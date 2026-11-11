import pathlib,sqlite3,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"hospital"))
from royallab_nova_typed_form_contract import reviewed_order_form
class TypedContractTests(unittest.TestCase):
 def setUp(self):
  self.db=sqlite3.connect(":memory:")
  self.db.executescript("""CREATE TABLE hospital_order_items(id INTEGER PRIMARY KEY,test_id INTEGER);
 CREATE TABLE hospital_lab_parameters(id INTEGER PRIMARY KEY,test_id INTEGER,code TEXT,active INTEGER);
 CREATE TABLE hospital_lab_lines(id INTEGER PRIMARY KEY,item_id INTEGER,code TEXT,parameter_id INTEGER);
 INSERT INTO hospital_order_items VALUES(22,7);
 INSERT INTO hospital_lab_parameters VALUES(1,7,'ROYAL_FMT_20',1);
 INSERT INTO hospital_lab_lines VALUES(11,22,'ROYAL_FMT_20',1);""")
  self.form={"review_flags":[],"fields":[{"source_format_id":"20","kind":"select","label":"Color","unit":"",
     "options":[{"label":"Yellow","active":True},{"label":"Red","active":True},{"label":"Old","active":False}]}]}
 def test_exact_typed_options_only_no_writes(self):
  result=reviewed_order_form(self.db,22,self.form)
  self.assertEqual(result["fields"][0]["line_id"],11)
  self.assertEqual(result["fields"][0]["options"],["Yellow","Red"])
  self.assertFalse(result["can_save_patient_results"])
 def test_source_string_boolean_flags(self):
  field=self.form["fields"][0]
  field["required"]="True"
  field["active"]="True"
  field["options"][2]["active"]="False"
  result=reviewed_order_form(self.db,22,self.form)
  self.assertTrue(result["fields"][0]["required"])
  self.assertEqual(result["fields"][0]["options"],["Yellow","Red"])
  field["required"]="False"
  self.assertFalse(reviewed_order_form(self.db,22,self.form)["fields"][0]["required"])
 def test_inactive_analyte_fails_closed(self):
  for value in (False,0,"False","false","0"):
   with self.subTest(value=value):
    self.form["fields"][0]["active"]=value
    with self.assertRaisesRegex(ValueError,"Inactive source analyte"):
     reviewed_order_form(self.db,22,self.form)
 def test_review_flags_and_ambiguous_dropdown_block(self):
  self.form["review_flags"]=["mixed_format_requires_combobox"]
  with self.assertRaises(ValueError):reviewed_order_form(self.db,22,self.form)
  self.form["review_flags"]=[]
  self.form["fields"][0]["options"].append({"label":"Yellow","active":True})
  with self.assertRaises(ValueError):reviewed_order_form(self.db,22,self.form)
if __name__=="__main__":unittest.main()
