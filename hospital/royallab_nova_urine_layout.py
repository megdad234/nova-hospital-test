"""Source-verified display-only grouping for Royal Lab urine (TestID 7).

The original source has TWO result formats for Crystals (type/grade), Cast
(type/grade), and Others (grade/free text). It also has an active S.Gravity
analyte without a result-format link alongside the original preset format.
These are distinct source identities, not repeated copies to delete.

This overlay never touches database rows, result values, option lists, units,
normal ranges, billing, printing, or a previously edited/approved order.
"""
import sqlite3

TEST_CODE = "ROYAL-7"
MACRO = frozenset({
    "ROYAL_FMT_554",   # Colour
    "ROYAL_FMT_290",   # Protein
    "ROYAL_FMT_2054",  # Sugar
    "ROYAL_FMT_5",     # Ketones
    "ROYAL_FMT_6",     # Bilirubin
    "ROYAL_FMT_2052",  # S.Gravity preset values
    "ROYAL_FMT_732",   # Nitrite
    "ROYAL_FMT_735",   # Urobilinogin
    "ROYAL_FMT_736",   # PH
    "ROYAL_ANALYTE_472",  # S.Gravity has NO result format in source
})
MICRO = frozenset({
    "ROYAL_FMT_851",   # Pus Cells (free text)
    "ROYAL_FMT_1774",  # R.B.Cs (free text)
    "ROYAL_FMT_297",   # Crystals: type
    "ROYAL_FMT_727",   # Crystals: grade
    "ROYAL_FMT_744",   # Mucous Threads
    "ROYAL_FMT_745",   # Cast: type
    "ROYAL_FMT_746",   # Cast: grade
    "ROYAL_FMT_748",   # Epithelial Cells
    "ROYAL_FMT_850",   # Comment (free text)
    "ROYAL_FMT_555",   # Others: grade
    "ROYAL_FMT_409",   # Others: free text
    "ROYAL_FMT_1004",  # Bacteria
    "ROYAL_FMT_1005",  # Yeast
})
DISPLAY_NAMES = {
    "ROYAL_FMT_297": ("Crystals", "Crystals (Type)"),
    "ROYAL_FMT_727": ("Crystals", "Crystals (Grade)"),
    "ROYAL_FMT_745": ("Cast", "Cast (Type)"),
    "ROYAL_FMT_746": ("Cast", "Cast (Grade)"),
    "ROYAL_FMT_555": ("Others", "Others (Grade)"),
    "ROYAL_FMT_409": ("Others", "Others (Additional Notes)"),
    "ROYAL_FMT_2052": ("S.Gravity", "S.Gravity (Preset)"),
    "ROYAL_ANALYTE_472": ("S.Gravity", "S.Gravity (Free Text — Unlinked Source Format)"),
}


def display_order_detail(conn, detail):
    """Add presentation metadata for editable, pristine ROYAL-7 orders only."""
    if not isinstance(conn, sqlite3.Connection) or not isinstance(detail, dict):
        return detail
    if not isinstance(detail.get("items"), list):
        return detail
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    if not {"hospital_order_items", "hospital_lab_tests"}.issubset(tables):
        return detail
    columns = {r[1] for r in conn.execute("PRAGMA table_info(hospital_order_items)")}
    if not {"id", "test_id", "result_status", "result_version"}.issubset(columns):
        return detail
    out = {**detail, "items": []}
    for item in detail["items"]:
        if not isinstance(item, dict) or type(item.get("id")) is not int:
            out["items"].append(item)
            continue
        row = conn.execute("""SELECT t.code, i.result_status, i.result_version
              FROM hospital_order_items i JOIN hospital_lab_tests t
              ON t.id=i.test_id WHERE i.id=?""", (item["id"],)).fetchone()
        if (not row or row[0] != TEST_CODE or row[1] in ("approved", "published")
                or (row[2] or 0) > 0):
            out["items"].append(item)
            continue
        clone = {**item, "lines": []}
        for source in item.get("lines", []):
            if not isinstance(source, dict):
                clone["lines"].append(source)
                continue
            line = dict(source)
            code = str(line.get("code") or "")
            if code in MACRO | MICRO:
                if not str(line.get("section_name") or "").strip():
                    line["section_name"] = "Macroscopy" if code in MACRO else "Microscopy"
                if code in DISPLAY_NAMES:
                    original, friendly = DISPLAY_NAMES[code]
                    if str(line.get("name") or "").strip().casefold() == original.casefold():
                        line["source_label"] = line["name"]
                        line["name"] = friendly
            clone["lines"].append(line)
        out["items"].append(clone)
    return out
