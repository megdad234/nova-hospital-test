import pathlib,sys,unittest,zipfile,re
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
  self.assertIn("lab-print-group",after)
  self.assertIn("section_name",after)
  self.assertIn("flatMap((x,idx,visible)",after)
  self.assertEqual(after.count("async function printReport(id)"),1)
 def test_batch04_grouped_report_removes_only_partial_notice(self):
  notice='\u0024{d.partial?\'<p class="small">تقرير جزئي — توجد فحوصات أخرى لم تُنشر بعد.</p>\':\'\'}'
  source='async function printReport(id){const html=`<tr class="nova-lab-section"><th>Macroscopy</th></tr>'+notice+'`;window.print()}'
  updated=patch_lab_print_js(source)
  self.assertNotIn('تقرير جزئي',updated)
  self.assertIn('nova-lab-section',updated)
  self.assertIn('window.print()',updated)
 def test_actual_batch04_generated_print_template(self):
  root=pathlib.Path(__file__).resolve().parents[1]
  batch=(root/'.github/ci/nova_batch04_lab_reception.py').read_text(encoding='utf-8')
  match=re.search(r'async function printReport\\(id\\)\\{.*?window\\.print\\(\\);.*?\\}\\s*\\}"""\\)',batch,re.S)
  self.assertIsNotNone(match)
  template=match.group(0).split('"""')[0].replace('@{','${').replace('~','`')
  output=patch_lab_print_js(template)
  self.assertNotIn('تقرير جزئي',output)
  self.assertIn('nova-lab-section',output)
  self.assertIn('window.print()',output)
 def test_fails_closed_on_unexpected_source(self):
  with self.assertRaises(RuntimeError):patch_lab_print_js("other JS")
if __name__=="__main__":unittest.main()
