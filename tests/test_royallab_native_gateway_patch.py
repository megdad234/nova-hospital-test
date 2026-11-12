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
  self.assertIn('royallab_native_order_bridge',out)
  self.assertIn('royallab_clinical_template_review',out)
  self.assertIn("/royallab-native/review/propose",out)
  self.assertIn("/royallab-native/review/approve",out)
  self.assertIn("/royallab-native/review/history/",out)
  self.assertIn("core.require_role(role,'admin')",out)
  get,post=out.split("                    if path=='/api/hospital/patients':",1)
  self.assertIn("/royallab-native/order/draft/",get)
  self.assertNotIn("/royallab-native/order/attach",get)
  self.assertIn("/royallab-native/order/attach",post)
  self.assertIn("royallab_native_order_bridge.save_order_item_draft",post)
  with self.assertRaises(ValueError):m.patch(out)
 def test_unknown_source_rejected(self):
  with self.assertRaises(ValueError):m.patch("something else")
if __name__=='__main__':unittest.main()
