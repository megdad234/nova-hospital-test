"""Smoke original NOVA gateway patch and Royal Lab dependency imports without writes."""
import pathlib,py_compile,sys,tempfile,unittest,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'.github/ci'))
from royallab_order_route_patch import patch
class GatewaySmoke(unittest.TestCase):
 def test_patched_original_gateway_compiles_and_preserves_critical_routes(self):
  with zipfile.ZipFile(ROOT/'NOVA_Hospital_GitHub_Ready_Source.zip') as z:
   original=z.read('hospital/gateway.py').decode('utf-8-sig')
  updated=patch(original)
  self.assertIn("if path=='/api/hospital/lab/values':",updated)
  self.assertIn("if path.startswith('/api/hospital/lab/report/'):",updated)
  self.assertIn("if path.startswith('/api/hospital/order/'):",updated)
  self.assertEqual(updated.count('core.require_role('),original.count('core.require_role('))
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/'gateway.py'
   p.write_text(updated,encoding='utf-8')
   py_compile.compile(str(p),doraise=True)
 def test_dependencies_compile(self):
  for name in ('royallab_nova_live_order_overlay','royallab_nova_binding_loader',
    'royallab_nova_binding_schema','royallab_nova_order_detail_gate',
    'royallab_nova_order_detail_types','royallab_nova_typed_form_contract',
    'royallab_nova_order_line_resolver','royallab_nova_parameter_plan',
    'royallab_catalog_preview','royallab_field_adapter'):
   py_compile.compile(str(ROOT/'hospital'/(name+'.py')),doraise=True)
if __name__=='__main__':unittest.main()
