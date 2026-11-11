import importlib.util,json,pathlib,tempfile,unittest
P=pathlib.Path(__file__).resolve().parents[1]/'.github/ci/royallab_source_bundle_preflight.py'
spec=importlib.util.spec_from_file_location('source_preflight',P)
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
class SourceBundleTests(unittest.TestCase):
 def test_valid_bundle_and_missing_source_rejection(self):
  with tempfile.TemporaryDirectory() as d:
   a=pathlib.Path(d)/'library.json';b=pathlib.Path(d)/'unlinked.json'
   library={'tests':[{'TestID':i} for i in range(367)],'analytes':[{'analyte_id':i} for i in range(1245)]}
   a.write_text(json.dumps(library),encoding='utf-8')
   b.write_text(json.dumps([{} for _ in range(2551)]),encoding='utf-8')
   result=mod.verify(a,b)
   self.assertEqual(result['tests'],367)
   self.assertFalse(result['clinical_approved'])
   self.assertEqual(result['live_bindings_created'],0)
   library['tests'].pop()
   a.write_text(json.dumps(library),encoding='utf-8')
   with self.assertRaisesRegex(ValueError,'367-test'):mod.verify(a,b)
 def test_missing_files_fail(self):
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaises(FileNotFoundError):
    mod.verify(pathlib.Path(d)/'missing.json',pathlib.Path(d)/'missing2.json')
if __name__=='__main__':unittest.main()
