"""Real Royal Lab source exports encode booleans as strings in some rows."""
import pathlib,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from hospital.royallab_nova_typed_form_contract import source_bool
class SourceBooleanTests(unittest.TestCase):
 def test_source_true_values(self):
  for value in (True,1,"True","true","1"):
   with self.subTest(value=value):self.assertIs(source_bool(value),True)
 def test_source_false_values(self):
  for value in (False,0,"False","false","0"):
   with self.subTest(value=value):self.assertIs(source_bool(value),False)
 def test_unknown_never_coerced_to_true(self):
  for value in (None,"","unknown","yes","no",[],{}):
   with self.subTest(value=value):self.assertIsNone(source_bool(value))
if __name__=="__main__":unittest.main()
