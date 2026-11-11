import pathlib,sqlite3,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"hospital"))
from royallab_nova_order_line_resolver import resolve_order_lines
class ResolverTests(unittest.TestCase):
 def setUp(self):
  self.db=sqlite3.connect(":memory:")
  self.db.executescript("""CREATE TABLE hospital_order_items(id INTEGER PRIMARY KEY,test_id INTEGER);
  CREATE TABLE hospital_lab_parameters(id INTEGER PRIMARY KEY,test_id INTEGER,code TEXT,active INTEGER);
  CREATE TABLE hospital_lab_lines(id INTEGER PRIMARY KEY,item_id INTEGER,code TEXT,parameter_id INTEGER);
  INSERT INTO hospital_order_items VALUES(10,7),(11,8);
  INSERT INTO hospital_lab_parameters VALUES(1,7,'ROYAL_FMT_20',1),(2,8,'ROYAL_FMT_20',1),(3,7,'ROYAL_FMT_21',0);
  INSERT INTO hospital_lab_lines VALUES(100,10,'ROYAL_FMT_20',1),(101,11,'ROYAL_FMT_20',2),(102,10,'ROYAL_FMT_21',3);""")
 def test_own_order_and_exact_source_id(self):
  p=resolve_order_lines(self.db,10,[{"source_format_id":"20","kind":"number"}])
  self.assertEqual(p["source_to_line"],{"20":100});self.assertTrue(p["ready"])
  self.assertEqual(resolve_order_lines(self.db,11,[{"source_format_id":"20","kind":"number"}])["source_to_line"],{"20":101})
 def test_inactive_unknown_missing_block(self):
  p=resolve_order_lines(self.db,10,[{"source_format_id":"21","kind":"number"},{"source_format_id":"22","kind":"unknown"}])
  self.assertFalse(p["ready"]);self.assertEqual(len(p["unresolved"]),2)
  self.assertEqual(p["source_to_line"],{})
 def test_duplicate_and_missing_order(self):
  with self.assertRaises(ValueError):resolve_order_lines(self.db,10,[{"source_format_id":"20","kind":"number"},{"source_format_id":"20","kind":"number"}])
  with self.assertRaises(ValueError):resolve_order_lines(self.db,99,[{"source_format_id":"20","kind":"number"}])
if __name__=="__main__":unittest.main()
