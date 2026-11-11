import pathlib,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"hospital"))
from royallab_lab_a4_preview import render_lab_a4_preview
class LabA4Tests(unittest.TestCase):
 def test_portrait_header_and_results_same_document(self):
  html=render_lab_a4_preview({"patient":{"name":"Patient One"},"order":{"id":23,"created_at":"2026-11-11"},
   "items":[{"test_name":"Malaria","result_status":"approved","lines":[{"name":"Parasite","value":"Negative","unit":"","reference_range":""}]}]})
  self.assertIn("size:A4 portrait",html)
  self.assertIn("Patient One",html)
  self.assertIn("Negative",html)
  self.assertLess(html.index("Patient One"),html.index("Negative"))
  self.assertNotIn("تقرير جزئي",html)
  self.assertIn("tr{break-inside:avoid;page-break-inside:avoid}",html)
 def test_long_test_table_can_span_pages_without_splitting_rows(self):
  html=render_lab_a4_preview({"patient_name":"Patient","items":[{"result_status":"approved",
   "test_name":"Extended Panel","lines":[{"name":"Parameter "+str(i),"value":str(i),"unit":"mg/L","reference_range":""} for i in range(150)]}]})
  self.assertIn(".test{margin-bottom:6mm;break-inside:auto;page-break-inside:auto}",html)
  self.assertIn("thead{display:table-header-group}",html)
  self.assertIn("break-after:avoid-page",html)
  self.assertEqual(html.count("<tr>"),151)
 def test_original_nova_report_flat_fields(self):
  html=render_lab_a4_preview({"order_no":"LAB-100","patient_name":"Ahmed Ali",
   "patient_no":"P-20","age_years":35,"gender":"male","print_time":"2026-11-11",
   "brand":{"hospital_name":"NOVA Hospital","lab_title":"نتائج المعمل"},
   "items":[{"result_status":"approved","test_name":"CBC",
             "lines":[{"name":"Hemoglobin","value":"13.2","unit":"g/dL","reference_range":"12-16"}]}]})
  for term in ("LAB-100","Ahmed Ali","P-20","NOVA Hospital","نتائج المعمل","Hemoglobin","13.2","g/dL"):
   self.assertIn(term,html)
 def test_reject_unapproved_and_escape_untrusted_content(self):
  with self.assertRaises(PermissionError):
   render_lab_a4_preview({"items":[{"result_status":"draft"}]})
  html=render_lab_a4_preview({"patient":{"name":"<script>alert(1)</script>"},"items":[{"result_status":"approved","test_name":"Test","lines":[]}]})
  self.assertNotIn("<script>",html)
  self.assertIn("&lt;script&gt;",html)
if __name__=="__main__":unittest.main()
