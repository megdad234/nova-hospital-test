"""Ensure Windows build applies Royal Lab patches before compiling installer."""
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
class BuildPipelineContract(unittest.TestCase):
 def test_order_patch_is_before_windows_installer_and_js_patches(self):
  s=(ROOT/'.github/workflows/nova_build.yml').read_text(encoding='utf-8')
  anchors=['Expand-Archive','python .github/ci/royallab_order_route_patch.py',
           'python .github/ci/royallab_lab_print_patch.py',
           'python .github/ci/royallab_typed_input_patch.py',
           'python .github/ci/royallab_lab_a4_css_patch.py']
  for a in anchors:self.assertEqual(s.count(a),1,a)
  self.assertEqual(sorted(s.index(a) for a in anchors),[s.index(a) for a in anchors])
  self.assertIn("if ($LASTEXITCODE -ne 0) { throw 'Royal Lab order API patch rejected; installer blocked' }",s)
  self.assertIn("test_royallab_clinical_binding_integration.py",s)
  self.assertIn("test_royallab_order_route_patch.py",s)
 def test_no_pharmacy_print_patch_in_royal_lab_patch(self):
  p=(ROOT/'.github/ci/royallab_order_route_patch.py').read_text(encoding='utf-8')
  self.assertNotIn('pharmacy/static/',p)
  self.assertNotIn('hospital_lab_lines SET',p)
if __name__=='__main__':unittest.main()
