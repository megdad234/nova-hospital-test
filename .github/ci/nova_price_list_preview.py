"""NOVA price-list preparation: pure, read-only pricing calculations.

This module intentionally performs NO database writes. Integrate only after
validating final pharmacy schema, permissions and purchase-cost semantics.
"""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import csv
import io
import re
import unicodedata

MAX_PRICE = 1_000_000_000_000

def normalized_name(value):
    s = unicodedata.normalize("NFKC", str(value or "")).casefold()
    s = re.sub(r"[\u064b-\u065f\u0670]", "", s)
    s = s.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    return re.sub(r"[^\w]+", "", s, flags=re.UNICODE)

def money(value):
    try:
        d = Decimal(str(value).replace(",", "").strip())
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError("Invalid price")
    if not d.is_finite() or d < 0 or d > MAX_PRICE:
        raise ValueError("Price out of range")
    if d != d.to_integral_value():
        raise ValueError("SDG prices must be whole numbers")
    return int(d)

def proposed_sale(old_purchase, old_sale, new_purchase, override_markup=None):
    new = money(new_purchase)
    if override_markup is not None:
        pct = Decimal(str(override_markup))
        if not pct.is_finite() or pct < 0 or pct > 1000:
            raise ValueError("Invalid markup")
        result = Decimal(new) * (1 + pct / 100)
    else:
        old = money(old_purchase)
        sale = money(old_sale)
        if old <= 0:
            return None  # Must review manually: no trustworthy prior purchase
        result = Decimal(new) * Decimal(sale) / Decimal(old)
    rounded = int(result.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    if not 0 < rounded <= MAX_PRICE:
        raise ValueError("Proposed sale price out of range")
    return rounded

def parse_csv(text, name_column, purchase_column):
    """Read an uploaded CSV into an immutable preview; never create purchases."""
    reader = csv.DictReader(io.StringIO(text.lstrip("\ufeff")))
    if not reader.fieldnames or name_column not in reader.fieldnames or purchase_column not in reader.fieldnames:
        raise ValueError("Required columns missing")
    result = []
    for line, row in enumerate(reader, 2):
        name = str(row.get(name_column) or "").strip()
        if not name:
            continue
        result.append({"line": line, "name": name, "key": normalized_name(name),
                       "purchase_price": money(row.get(purchase_column))})
    return result
