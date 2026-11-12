"""Guard in-app laboratory template editing and independent approval UI.

No patient results or medical values are built into the repair interface.
"""
import pathlib
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "hospital/static/royallab-native-picker.js"


class ClinicalReviewUIContractTests(unittest.TestCase):
    def test_repair_panel_can_edit_originally_missing_lab_fields(self):
        js = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("review/propose", js)
        self.assertIn("review/approve", js)
        self.assertIn("review/suggestion/", js)
        self.assertIn("تعبئة الحقول من المصدر", js)
        self.assertIn("review/history/", js)
        self.assertIn("review/details/", js)
        self.assertIn("source_test_id: reviewSelect.value", js)
        self.assertIn("entry_status === 'requires_review'", js)
        self.assertIn("kind === 'select'", js)
        self.assertIn("choicesText.split(/\\r?\\n/)", js)
        self.assertIn("form_hash: data.form_hash", js)
        self.assertIn("form_hash !== latest.form_hash", js)
        self.assertIn("أضف حقلاً واحداً على الأقل", js)
        self.assertIn("مراجعة مستقلة", js)

    def test_safe_dom_and_original_result_guard_remain(self):
        js = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn(".innerHTML", js)
        self.assertNotIn("document.write(", js)
        self.assertIn("control.dataset.sourceFormatId", js)
        self.assertIn("saveButton.disabled = !formReady", js)
        self.assertIn("selectedSerial !== requestSerial", js)


if __name__=="__main__":
    unittest.main()
