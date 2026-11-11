import pathlib,sys,unittest,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'.github/ci'))
from royallab_order_route_patch import patch
class OrderRoutePatchTests(unittest.TestCase):
 def test_exact_original_route_only(self):
  with zipfile.ZipFile(ROOT/'NOVA_Hospital_GitHub_Ready_Source.zip') as z:
   source=z.read('hospital/gateway.py').decode('utf-8-sig')
  output=patch(source)
  self.assertIn('royallab_nova_live_order_overlay.overlay_order_detail(c,core.order_detail(c,oid,role),role)',output)
  self.assertIn("core.require_role(role,'admin','reception','cashier','lab')",output)
  self.assertIn("lab.save_values(c,user,data)",output)
  self.assertEqual(output.count("lab.save_values(c,user,data)"),source.count("lab.save_values(c,user,data)"))
  with self.assertRaises(ValueError):patch(output)
if __name__=='__main__':unittest.main()
