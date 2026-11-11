import importlib.util,pathlib,unittest
p=pathlib.Path(__file__).resolve().parents[1]/'.github/ci/royallab_native_gateway_patch.py'
spec=importlib.util.spec_from_file_location('royallab_native_gateway_patch',p)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class GatewayPatchTests(unittest.TestCase):
 def test_auth_and_original_order_route_preserved(self):
  src="from hospital import core, lab, finance, admin, royallab_nova_live_order_overlay\n"+"                    if path==\'/api/hospital/patients\':\n                        return self.reply({})\n                    if path==\'/api/hospital/patients\':\n                        return self.reply({})\n                    "+m.ANCHOR+"\n"
  out=m.patch(src)
  self.assertIn("core.require_role(role,'admin','reception','lab')",out)
  self.assertIn("core.require_role(role,'admin','lab')",out)
  self.assertIn(m.ANCHOR,out)
  self.assertIn('royallab_native_catalog_api',out)
  with self.assertRaises(ValueError):m.patch(out)
 def test_unknown_source_rejected(self):
  with self.assertRaises(ValueError):m.patch("something else")
if __name__=='__main__':unittest.main()
