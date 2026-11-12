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

    def test_source_codes_are_not_visible_but_ids_remain_bound(self):
        html=render_form({"source_test_id":"ROYAL-001", "name":"ROYAL-001 CBC",
            "fields":[{"source_format_id":"F4", "label":"ROYAL-002 WBC", "kind":"select",
                       "unit":"", "options":[{"id":"1","label":"ROYAL-003 Positive","active":True}]}]})
        self.assertIn('data-source-test-id="ROYAL-001"',html)
        self.assertIn('data-source-format-id="F4"',html)
        self.assertIn('<h2>CBC</h2>',html)
        self.assertIn('>WBC</span>',html)
        self.assertIn('>Positive</option>',html)
        self.assertNotIn('>ROYAL-',html)

    def test_unknown_field_is_review_only(self):
        html=render_form({"source_test_id":"8","name":"Test","fields":[
            {"source_format_id":"F3","label":"Unclear","kind":"unknown"}]})
        self.assertIn("يتطلب مراجعة",html)
        self.assertNotIn('name="royal_F3"',html)

if __name__=="__main__":
    unittest.main()
