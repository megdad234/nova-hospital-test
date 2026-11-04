"""Safety checks for the read-only NOVA price-list preview helpers."""
import importlib.util
import pathlib
import unittest

PATH = pathlib.Path(__file__).with_name("nova_price_list_preview.py")
spec = importlib.util.spec_from_file_location("nova_price_list_preview", PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class PriceListPreviewTests(unittest.TestCase):
    def test_preserve_existing_markup(self):
        self.assertEqual(mod.proposed_sale(2000, 2600, 2500), 3250)
    def test_optional_global_markup(self):
        self.assertEqual(mod.proposed_sale(2000, 2600, 2500, 25), 3125)
    def test_unknown_old_purchase_requires_review(self):
        self.assertIsNone(mod.proposed_sale(0, 2600, 2500))
    def test_csv_preview_does_not_touch_inventory(self):
        rows = mod.parse_csv("الدواء,الشراء\nدواء A,2500\n", "الدواء", "الشراء")
        self.assertEqual(rows[0]["purchase_price"], 2500)
    def test_reject_bad_prices(self):
        for value in ("NaN", "-1", "1.5", "1000000000001"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    mod.money(value)

if __name__ == "__main__":
    unittest.main()
