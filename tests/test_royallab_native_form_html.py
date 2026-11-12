import unittest
from hospital.royallab_native_form_html import render_form

class NativeFormHtmlTests(unittest.TestCase):
    def test_dropdown_number_and_escaping(self):
        html = render_form({"source_test_id":"7","name":"CBC <script>",
            "fields":[{"source_format_id":"F1","label":"Malaria <img>",
                       "kind":"select","unit":"","options":[
                         {"id":"1","label":"Positive","active":True},
                         {"id":"2","label":"Negative","active":True},
                         {"id":"3","label":"Inactive","active":False}]},
                      {"source_format_id":"F2","label":"Count","kind":"number","unit":"cells"}]})
        self.assertIn('dir="rtl"', html)
        self.assertIn('value="1"', html)
        self.assertIn('value="2"', html)
        self.assertNotIn("Inactive", html)
        self.assertIn('type="number"', html)
        self.assertIn('&lt;script&gt;', html)
        self.assertNotIn('<script>', html)
        self.assertIn('&lt;img&gt;', html)

    def test_unknown_field_is_review_only(self):
        html=render_form({"source_test_id":"8","name":"Test","fields":[
            {"source_format_id":"F3","label":"Unclear","kind":"unknown"}]})
        self.assertIn("يتطلب مراجعة",html)
        self.assertNotIn('name="royal_F3"',html)

if __name__=="__main__":
    unittest.main()
