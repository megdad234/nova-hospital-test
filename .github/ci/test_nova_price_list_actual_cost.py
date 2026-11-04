import sqlite3
import unittest
from nova_price_list_actual_cost import actual_last_cost

class ActualPurchaseCostTests(unittest.TestCase):
    def setUp(self):
        self.c=sqlite3.connect(":memory:")
        self.c.executescript("""
        CREATE TABLE packages(id INTEGER PRIMARY KEY,product_id INTEGER,factor INTEGER);
        CREATE TABLE purchase_lines(id INTEGER PRIMARY KEY,package_id INTEGER,qty INTEGER,bonus INTEGER,amount INTEGER);
        INSERT INTO packages VALUES(1,9,10),(2,9,1),(3,10,10);
        INSERT INTO purchase_lines VALUES(1,1,10,0,10000);
        INSERT INTO purchase_lines VALUES(2,2,20,0,4000);
        """)
    def tearDown(self):self.c.close()
    def test_latest_supplier_independent_and_pack_converted(self):
        result=actual_last_cost(self.c,1)
        self.assertEqual(result["purchase_line_id"],2)
        self.assertEqual(result["unit_purchase_cost"],2000)
    def test_bonus_reduces_unit_cost(self):
        self.c.execute("INSERT INTO purchase_lines VALUES(3,1,10,10,10000)")
        self.assertEqual(actual_last_cost(self.c,1)["unit_purchase_cost"],500)
    def test_missing_history(self):
        self.assertIsNone(actual_last_cost(self.c,3))
    def test_invalid_package(self):
        with self.assertRaises(ValueError):actual_last_cost(self.c,999)

if __name__=="__main__":unittest.main()
