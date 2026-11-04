"""NOVA CSV/XLSX importer regression tests."""
import io
import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).parent))
from nova_price_list_import import parse_file

class ImportTests(unittest.TestCase):
    def test_arabic_csv(self):
        rows=parse_file("list.csv", "الاسم التجاري,سعر الشراء,التركيز,العبوة\nMobizal,2500,15mg,10 tabs\n".encode())
        self.assertEqual(rows[0]["purchase_price"],2500)
        self.assertEqual(rows[0]["strength"],"15mg")
    def test_missing_required_columns(self):
        with self.assertRaises(ValueError):
            parse_file("list.csv",b"name,qty\nDrug,10")
    def test_pdf_is_not_silently_parsed(self):
        with self.assertRaises(ValueError):
            parse_file("list.pdf",b"%PDF-1.4")
    def test_reject_negative_price(self):
        with self.assertRaises(ValueError):
            parse_file("list.csv",b"name,price\nDrug,-1")
    def test_xlsx(self):
        from openpyxl import Workbook
        wb=Workbook()
        wb.active.append(["Trade Name","Purchase Price","Strength"])
        wb.active.append(["Drug",1234,"20mg"])
        buf=io.BytesIO()
        wb.save(buf)
        rows=parse_file("list.xlsx",buf.getvalue())
        self.assertEqual(rows[0]["purchase_price"],1234)

if __name__=="__main__":
    unittest.main()
