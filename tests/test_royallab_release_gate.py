import importlib.util,json,pathlib,tempfile,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
P=ROOT/'.github/ci/royallab_release_gate.py'
spec=importlib.util.spec_from_file_location('release_gate',P)
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
class ReleaseGateTests(unittest.TestCase):
 def test_missing_manifest_blocks(self):
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaisesRegex(RuntimeError,'no live release manifest'):mod.verify(d)
 def test_unsubstantiated_manifest_blocks(self):
  with tempfile.TemporaryDirectory() as d:
   h=pathlib.Path(d)/'hospital';h.mkdir()
   flags=('source_catalog_packaged','installer_imports_source_catalog','nova_test_bindings_installed','dropdown_runtime_e2e_passed','clinical_review_policy_verified')
   (h/'royallab_live_release_manifest.json').write_text(json.dumps({**{x:True for x in flags},'source_test_count':367}),encoding='utf-8')
   with self.assertRaisesRegex(RuntimeError,'source bundle evidence missing'):mod.verify(d)
 def test_fake_source_digest_blocks(self):
  with tempfile.TemporaryDirectory() as d:
   h=pathlib.Path(d)/'hospital';h.mkdir()
   (h/'library.json').write_text('{}',encoding='utf-8')
   (h/'unlinked.json').write_text('[]',encoding='utf-8')
   flags=('source_catalog_packaged','installer_imports_source_catalog','nova_test_bindings_installed','dropdown_runtime_e2e_passed','clinical_review_policy_verified')
   manifest={**{x:True for x in flags},'source_test_count':367,'source_bundle':{x:{'path':'hospital/'+x+'.json','sha256':'0'*64} for x in ('library','unlinked')},'runtime_evidence':{'passed':True,'real_installed_windows':True,'dropdowns_verified':True}}
   (h/'royallab_live_release_manifest.json').write_text(json.dumps(manifest),encoding='utf-8')
   with self.assertRaisesRegex(RuntimeError,'digest mismatch'):mod.verify(d)
if __name__=='__main__':unittest.main()
