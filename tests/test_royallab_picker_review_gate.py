"""Regression guard for the lab browser's fail-closed draft editor.

This checks the deployed source contract without a JavaScript runtime.
"""
from pathlib import Path
import unittest

PICKER = Path(__file__).resolve().parents[1] / "hospital" / "static" / "royallab-native-picker.js"

class PickerReviewGateTests(unittest.TestCase):
    def test_reviewed_source_only_enables_draft_entry(self):
        script = PICKER.read_text(encoding="utf-8")
        self.assertIn("Array.isArray(data.test.review_flags)", script)
        self.assertIn("if (reviewFlags.length)", script)
        self.assertIn("new Set(fieldIds).size !== fieldIds.length", script)
        self.assertIn("fields.some(function (f)", script)
        self.assertIn("saveButton.disabled = true;", script)
        self.assertIn("let formReady = false;", script)
        self.assertIn("let saving = false;", script)
        self.assertIn("if (!formReady || saving) return;", script)
        self.assertIn("saveButton.disabled = !formReady;", script)
        self.assertNotIn("saveButton.disabled = !picker.value || !detail.querySelector", script)
        self.assertIn("selectedSerial !== requestSerial", script)
        self.assertIn("if (serial !== requestSerial) return;", script)

if __name__ == "__main__":
    unittest.main()
