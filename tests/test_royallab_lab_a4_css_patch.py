import pathlib,sys,unittest,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/".github"/"ci"))
from royallab_lab_a4_css_patch import patch
class A4CssTests(unittest.TestCase):
 def test_scoped_to_lab_and_preserves_existing_css(self):
  with zipfile.ZipFile(ROOT/"NOVA_Hospital_GitHub_Ready_Source.zip") as z:
   before=z.read("hospital/static/style.css").decode("utf-8-sig")
  after=patch(before)
  self.assertTrue(after.startswith(before))
  self.assertIn("body.printing-lab #print-area .print-patient{break-inside:avoid-page",after)
  self.assertIn("thead{display:table-header-group}",after)
  self.assertIn(".lab-print-group th",after)
  self.assertNotIn("body.printing-lab #print-area .bill-print",after[len(before):])
  with self.assertRaises(RuntimeError):patch(after)
if __name__=="__main__":unittest.main()
