import importlib.util,pathlib,unittest
p=pathlib.Path(__file__).resolve().parents[1]/'.github/ci/royallab_native_autoseed_patch.py'
spec=importlib.util.spec_from_file_location('royallab_native_autoseed_patch',p)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class AutoseedPatchTests(unittest.TestCase):
 def test_inserts_only_after_lab_schema(self):
  original='def init(c):\n'+m.ANCHOR+'\n        pass\n'
  patched=m.patch(original)
  self.assertIn('ROYALLAB_NATIVE_AUTOSEED',patched)
  self.assertIn('_royallab_install(c, _royallab_path)',patched)
  self.assertIn('from pathlib import Path',patched)
  self.assertIn("for table in ('hospital_lab_parameters','hospital_lab_lines'):",patched)
  compile(patched,'lab.py','exec')
  with self.assertRaises(ValueError):m.patch(patched)
 def test_fails_closed_if_lab_source_changes(self):
  with self.assertRaises(ValueError):m.patch('def init(c):pass')
if __name__=='__main__':unittest.main()
