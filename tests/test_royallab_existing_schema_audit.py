import sqlite3
import unittest
from hospital.royallab_existing_schema_audit import inspect_existing_lab

class ExistingLabSchemaAuditTests(unittest.TestCase):
    def test_read_only_schema_and_missing_tables(self):
        with sqlite3.connect(":memory:") as db:
            db.execute("CREATE TABLE hospital_lab_tests(id INTEGER PRIMARY KEY,code TEXT UNIQUE,name TEXT)")
            db.execute("CREATE TABLE hospital_lab_parameters(id INTEGER PRIMARY KEY,test_id INTEGER REFERENCES hospital_lab_tests(id),name TEXT)")
            db.execute("CREATE TABLE hospital_lab_lines(id INTEGER PRIMARY KEY,parameter_id INTEGER REFERENCES hospital_lab_parameters(id),value TEXT)")
            db.execute("CREATE TABLE hospital_orders(id INTEGER PRIMARY KEY,status TEXT)")
            db.execute("CREATE TABLE hospital_order_items(id INTEGER PRIMARY KEY,order_id INTEGER REFERENCES hospital_orders(id))")
            db.execute("INSERT INTO hospital_lab_tests VALUES(1,'OLD','Old test')")
            db.execute("INSERT INTO hospital_lab_parameters VALUES(1,1,'Old parameter')")
            before=db.total_changes
            result=inspect_existing_lab(db)
            self.assertTrue(result["ready_for_mapping"])
            self.assertEqual(db.total_changes,before)
            self.assertFalse(result["patient_values_read"])
            self.assertEqual(result["tables"]["hospital_lab_parameters"]["foreign_keys"][0]["to_table"],
                             "hospital_lab_tests")
            self.assertNotIn("Old test",str(result))
            db.execute("DROP TABLE hospital_lab_lines")
            self.assertFalse(inspect_existing_lab(db)["ready_for_mapping"])

if __name__=="__main__":
    unittest.main()
