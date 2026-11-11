import pathlib,sys,unittest,zipfile
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/".github"/"ci"))
from royallab_lab_print_patch import patch_lab_print_js
class LabPrintPatchTests(unittest.TestCase):
 def test_exact_original_nova_lab_print_only(self):
  p=pathlib.Path(__file__).resolve().parents[1]/"NOVA_Hospital_GitHub_Ready_Source.zip"
  with zipfile.ZipFile(p) as z:
   before=z.read("hospital/static/app.js").decode("utf-8-sig")
  after=patch_lab_print_js(before)
  self.assertNotIn("تقرير جزئي — توجد فحوصات أخرى",after)
  self.assertIn("async function printReport(id)",after)
  self.assertIn("window.print()",after)
  self.assertIn("lab/report/",after)
  self.assertEqual(before.count("تقرير جزئي — توجد فحوصات أخرى"),1)
  self.assertEqual(len(before)-len(after),len(before[before.index("${d.partial?"):before.index("':''}",before.index("${d.partial?"))+4]))
 def test_fails_closed_on_unexpected_source(self):
  with self.assertRaises(RuntimeError):patch_lab_print_js("other JS")
if __name__=="__main__":unittest.main()
