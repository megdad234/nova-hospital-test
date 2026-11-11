"""Check the exact sequence of Windows lab UI and print patches in isolation."""
import pathlib,subprocess,sys,tempfile,unittest,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'.github/ci'))
from royallab_lab_print_patch import patch_lab_print_js as print_patch
from royallab_typed_input_patch import patch as typed_patch
class CombinedUiTests(unittest.TestCase):
 def test_real_source_print_and_typed_patches_compile_and_keep_save(self):
  with zipfile.ZipFile(ROOT/'NOVA_Hospital_GitHub_Ready_Source.zip') as z:
   original=z.read('hospital/static/app.js').decode('utf-8-sig')
  after=typed_patch(print_patch(original))
  self.assertIn('function royalLabInput(',after)
  self.assertIn('royalLabInput(x)',after)
  self.assertIn("await api('lab/values',{item_id:",after)
  self.assertEqual(after.count("await api('lab/values',{item_id:"),original.count("await api('lab/values',{item_id:"))
  self.assertNotIn("تقرير جزئي — توجد فحوصات أخرى لم تُجهز للطباعة.",after)
  with tempfile.TemporaryDirectory() as td:
   p=pathlib.Path(td)/'app.js';p.write_text(after,encoding='utf-8')
   result=subprocess.run(['node','--check',str(p)],capture_output=True,text=True)
   self.assertEqual(result.returncode,0,result.stderr)
if __name__=='__main__':unittest.main()
