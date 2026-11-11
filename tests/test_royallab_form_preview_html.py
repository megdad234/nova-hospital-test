import pathlib,sqlite3,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"hospital"))
from royallab_staging import stage
from royallab_form_preview_html import render_preview
class HtmlPreviewTests(unittest.TestCase):
 def test_rtl_safe_noninteractive_preview(self):
  with sqlite3.connect(":memory:") as c:
   tests=[{"TestID":str(i),"Name":"Test "+str(i)} for i in range(367)]
   tests[0]["Name"]='<script>alert(1)</script>'
   analytes=[{"analyte_id":str(i),"test_id":str(i%367),"name":"Field "+str(i),
    "result_formats":[{"id":str(i),"title":"Field","types":["ColoseEndedResultFormat"],
      "options":[{"id":"x","label":"<img src=x onerror=alert(1)>"}]}]} for i in range(1245)]
   unlinked=[{"ColoseEndedResultOptionID":str(i),"reason":"unlinked"} for i in range(2551)]
   batch=stage(c,{"tests":tests,"analytes":analytes},unlinked,"test-html")
   before=c.total_changes
   page=render_preview(c,batch,"0")
   self.assertIn('dir="rtl"',page)
   self.assertIn('&lt;script&gt;',page)
   self.assertNotIn('<script>alert(1)</script>',page)
   self.assertIn('&lt;img src=x onerror=alert(1)&gt;',page)
   self.assertNotIn('<img src=x onerror=alert(1)>',page)
   self.assertNotIn('<form',page)
   self.assertNotIn('<button',page)
   self.assertIn('disabled',page)
   self.assertEqual(before,c.total_changes)
if __name__=="__main__":unittest.main()
