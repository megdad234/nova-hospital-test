"""NOVA supplier price-list import: CSV/XLSX to review rows, no writes.

Uses openpyxl already installed in the Windows build environment.
PDF is deliberately rejected unless a separate reliable table extractor
can prove row/column structure.
"""
import csv
import io
from nova_price_list_preview import money

ALIASES = {
    "name": ("name", "trade name", "product", "item", "اسم الصنف", "الاسم التجاري", "الصنف", "الدواء"),
    "purchase_price": ("purchase price", "price", "unit price", "السعر", "سعر الشراء", "سعر"),
    "strength": ("strength", "dose", "dosage", "التركيز", "العيار"),
    "pack": ("pack", "package", "pack size", "العبوة", "حجم العبوة"),
    "manufacturer": ("manufacturer", "company", "الشركة", "الشركة المصنعة"),
    "form": ("form", "dosage form", "الشكل", "الشكل الدوائي"),
    "barcode": ("barcode", "باركود"),
}
MAX_ROWS = 20000
MAX_BYTES = 8 * 1024 * 1024

def _header(value):
    return " ".join(str(value or "").strip().casefold().split())

def _map(headers):
    result = {}
    for i, heading in enumerate(headers):
        key = _header(heading)
        for field, names in ALIASES.items():
            if key in names:
                if field in result:
                    raise ValueError("Duplicate mapped column: " + field)
                result[field] = i
    if "name" not in result or "purchase_price" not in result:
        raise ValueError("Trade name and purchase price columns required")
    return result

def _rows(records):
    it = iter(records)
    try:
        header = next(it)
    except StopIteration:
        raise ValueError("Empty price list")
    mapping = _map(header)
    output = []
    for line, cells in enumerate(it, 2):
        if line > MAX_ROWS + 1:
            raise ValueError("Too many rows")
        def value(field):
            idx = mapping.get(field)
            return str(cells[idx] if idx is not None and idx < len(cells) and cells[idx] is not None else "").strip()
        name = value("name")
        if not name:
            continue
        row = {"line": line, "name": name, "purchase_price": money(value("purchase_price"))}
        for field in ("strength", "pack", "manufacturer", "form", "barcode"):
            row[field] = value(field)
        output.append(row)
    return output

def parse_file(filename, content):
    if not isinstance(content, bytes) or len(content) > MAX_BYTES:
        raise ValueError("Invalid file or size limit exceeded")
    ext = str(filename).lower().rsplit(".", 1)[-1]
    if ext == "csv":
        try:
            decoded = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            decoded = content.decode("cp1256")
        return _rows(csv.reader(io.StringIO(decoded)))
    if ext == "xlsx":
        from openpyxl import load_workbook
        workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        try:
            if len(workbook.sheetnames) != 1:
                raise ValueError("Choose a single-sheet workbook")
            return _rows(workbook.active.iter_rows(values_only=True))
        finally:
            workbook.close()
    raise ValueError("Only CSV and XLSX are supported; PDF needs verified extraction")
