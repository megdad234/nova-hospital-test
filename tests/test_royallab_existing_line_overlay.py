import json
import sqlite3
import unittest
from hospital.royallab_existing_line_overlay import overlay_existing_order_lines

class ExistingLineOverlayTests(unittest.TestCase):
    def test_existing_nova_result_lines_receive_dropdowns_only_for_royal_tests(self):
        with sqlite3.connect(":memory:") as db:
            db.execute("CREATE TABLE hospital_lab_tests(id INTEGER PRIMARY KEY,code TEXT)")
            db.execute("CREATE TABLE hospital_lab_parameters(id INTEGER PRIMARY KEY,test_id INTEGER)")
            db.execute("CREATE TABLE hospital_order_items(id INTEGER PRIMARY KEY,test_id INTEGER)")
            db.execute("""CREATE TABLE royal_lab_nova_parameter_metadata(
              nova_parameter_id INTEGER PRIMARY KEY,kind TEXT,options_json TEXT,
              numeric_ranges_json TEXT,text_ranges_json TEXT)""")
            db.execute("INSERT INTO hospital_lab_tests VALUES(1,'ROYAL-11'),(2,'OLD')")
            db.execute("INSERT INTO hospital_lab_parameters VALUES(10,1),(20,2)")
            db.execute("INSERT INTO hospital_order_items VALUES(100,1),(200,2)")
            db.execute("INSERT INTO royal_lab_nova_parameter_metadata VALUES(10,'select',?,?,?)",
                       (json.dumps([{"id":"1","label":"Positive","active":True},
                                    {"id":"2","label":"Inactive","active":False}]),"[]","[]"))
            detail={"items":[{"id":100,"lines":[{"id":1000,"parameter_id":10,"value":""}]},
                             {"id":200,"lines":[{"id":2000,"parameter_id":20,"value":""}]}]}
            result=overlay_existing_order_lines(db,detail)
            self.assertEqual(result["items"][0]["lines"][0]["royal_lab_field"]["options"],["Positive"])
            self.assertNotIn("royal_lab_field",result["items"][1]["lines"][0])
            self.assertNotIn("royal_lab_field",detail["items"][0]["lines"][0])

if __name__=="__main__":
    unittest.main()
