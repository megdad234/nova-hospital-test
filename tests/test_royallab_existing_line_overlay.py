import json
import sqlite3
import unittest
from hospital.royallab_existing_line_overlay import overlay_existing_order_lines

class ExistingLineOverlayTests(unittest.TestCase):
    def test_existing_nova_result_lines_receive_dropdowns_only_for_royal_tests(self):
        with sqlite3.connect(":memory:") as db:
            db.execute("CREATE TABLE hospital_lab_tests(id INTEGER PRIMARY KEY,code TEXT)")
            db.execute("CREATE TABLE hospital_lab_parameters(id INTEGER PRIMARY KEY,test_id INTEGER,code TEXT)")
            db.execute("CREATE TABLE hospital_order_items(id INTEGER PRIMARY KEY,test_id INTEGER)")
            db.execute("""CREATE TABLE royal_lab_nova_parameter_metadata(
              nova_parameter_id INTEGER PRIMARY KEY,kind TEXT,options_json TEXT,
              numeric_ranges_json TEXT,text_ranges_json TEXT)""")
            db.execute("INSERT INTO hospital_lab_tests VALUES(1,'ROYAL-11'),(2,'OLD')")
            db.execute("INSERT INTO hospital_lab_parameters VALUES(10,1,'ROYAL_FMT_11'),(20,2,'OLD_FMT')")
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
            by_code={"items":[{"id":100,"lines":[{"id":1000,"code":"ROYAL_FMT_11","value":""}]}]}
            coded=overlay_existing_order_lines(db,by_code)
            self.assertEqual(coded["items"][0]["lines"][0]["royal_lab_field"]["options"],["Positive"])
            wrong={"items":[{"id":200,"lines":[{"id":2000,"code":"ROYAL_FMT_11","value":""}]}]}
            self.assertNotIn("royal_lab_field",overlay_existing_order_lines(db,wrong)["items"][0]["lines"][0])

    def test_two_source_result_formats_same_urine_analyte_stay_distinct(self):
        # The original Royal Lab UI showed separate dropdowns for a single
        # analyte (e.g. urine crystal type + quantity). NOVA already has a
        # parameter row per source format; do not collapse their identities.
        with sqlite3.connect(":memory:") as db:
            db.executescript("""
            CREATE TABLE hospital_lab_tests(id INTEGER PRIMARY KEY,code TEXT);
            CREATE TABLE hospital_lab_parameters(id INTEGER PRIMARY KEY,test_id INTEGER,code TEXT);
            CREATE TABLE hospital_order_items(id INTEGER PRIMARY KEY,test_id INTEGER);
            CREATE TABLE royal_lab_nova_parameter_metadata(
                nova_parameter_id INTEGER PRIMARY KEY,kind TEXT,options_json TEXT,
                numeric_ranges_json TEXT,text_ranges_json TEXT);
            INSERT INTO hospital_lab_tests VALUES(7,'ROYAL-7');
            INSERT INTO hospital_lab_parameters VALUES(70,7,'ROYAL_FMT_700');
            INSERT INTO hospital_lab_parameters VALUES(71,7,'ROYAL_FMT_701');
            INSERT INTO hospital_order_items VALUES(140,7);
            """)
            for p,kinds in ((70,["Calcium oxalate","Urate"]),
                            (71,["(+)","(++)","(+++)" ])):
                db.execute("""INSERT INTO royal_lab_nova_parameter_metadata
                    VALUES (?,?,?,?,?)""",
                    (p,"select",json.dumps([{"id":str(i),"label":v,"active":True}
                                            for i,v in enumerate(kinds,1)]),"[]","[]"))
            detail={"items":[{"id":140,"lines":[
                {"id":11,"parameter_id":70,"value":"", "name":"Crystals"},
                {"id":12,"parameter_id":71,"value":"", "name":"Crystals"}]}]}
            output=overlay_existing_order_lines(db,detail)
            lines=output["items"][0]["lines"]
            self.assertEqual(len(lines),2)
            self.assertEqual(lines[0]["royal_lab_field"]["options"],["Calcium oxalate","Urate"])
            self.assertEqual(lines[1]["royal_lab_field"]["options"],["(+)","(++)","(+++)" ])
            self.assertNotEqual(lines[0]["royal_lab_field"]["options"],
                                lines[1]["royal_lab_field"]["options"])
            self.assertNotIn("royal_lab_field",detail["items"][0]["lines"][0])


if __name__=="__main__":
    unittest.main()
