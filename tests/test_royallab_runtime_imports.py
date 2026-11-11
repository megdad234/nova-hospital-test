"""Exercise actual NOVA package import chain for the lab gateway overlay."""
import importlib,pathlib,subprocess,sys,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
class RuntimeImportTests(unittest.TestCase):
 def test_overlay_import_chain_works_from_repository_root(self):
  p=subprocess.run([sys.executable,'-c',
   'from hospital.royallab_nova_live_order_overlay import overlay_order_detail; '
   'from hospital.royallab_nova_binding_schema import create_schema; '
   'assert callable(overlay_order_detail) and callable(create_schema)'],
   cwd=ROOT,capture_output=True,text=True)
  self.assertEqual(p.returncode,0,p.stderr)
if __name__=='__main__':unittest.main()
