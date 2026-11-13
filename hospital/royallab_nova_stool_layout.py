"""Presentation-only improvements for original Royal Lab STOOL GENERAL ANALYSIS.

Grounded in recovered RoyalLabDB.bak TestID 8:
- Macroscopy: Colour, Consistency, Reaction, Mucous, Blood.
- Microscopy: cells, cysts, ova, flagellates, trophozoites, both 'Others'
  source formats, yeast and undigested materials.
- The two separate 'Others' result formats are distinct, not duplicates.
No source option, code, test identity, patient finding, reference value,
result status, price, or stored clinical row is changed here.
"""
import sqlite3

TEST_CODE="ROYAL-8"
MACRO=frozenset({"302","67","411","593","590"})
MICRO=frozenset({"1786","1787","73","307","594","76","310",
                 "896","1778","1777"})
KNOWN=MACRO|MICRO
CUSTOM_LABELS={
    "310":"Others (Listed Findings)",
    "896":"Others (Additional Notes)",
}


def display_order_detail(conn,detail):
    """Add grouping + disambiguated labels only to active, unreported stool UI."""
    if not isinstance(conn,sqlite3.Connection) or not isinstance(detail,dict):
        return detail
    if not isinstance(detail.get("items"),list):
        return detail
    tables={r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    if not {"hospital_order_items","hospital_lab_tests"}.issubset(tables):
        return detail
    columns={r[1] for r in conn.execute("PRAGMA table_info(hospital_order_items)")}
    if not {"id","test_id","result_status","result_version"}.issubset(columns):
        return detail
    out={**detail,"items":[]}
    for item in detail["items"]:
        if not isinstance(item,dict) or type(item.get("id")) is not int:
            out["items"].append(item)
            continue
        row=conn.execute("""SELECT t.code,i.result_status,i.result_version
            FROM hospital_order_items i JOIN hospital_lab_tests t
              ON t.id=i.test_id WHERE i.id=?""",(item["id"],)).fetchone()
        if (not row or row[0]!=TEST_CODE or
                row[1] in ("approved","published") or (row[2] or 0)>0):
            # Old approved reports are kept byte-for-byte in their returned
            # representation; their archived values/labels are untouched.
            out["items"].append(item)
            continue
        clone={**item,"lines":[]}
        for source in item.get("lines",[]):
            line=dict(source)
            code=str(line.get("code") or "")
            if code.startswith("ROYAL_FMT_"):
                fid=code[len("ROYAL_FMT_"):]
                if fid in KNOWN:
                    if not str(line.get("section_name") or "").strip():
                        line["section_name"]="Macroscopy" if fid in MACRO else "Microscopy"
                    if fid in CUSTOM_LABELS and str(line.get("name") or "").strip().casefold()=="others":
                        # Make the distinction clear WITHOUT changing the
                        # underlying NOVA parameter label or result value.
                        line["source_label"]=line["name"]
                        line["name"]=CUSTOM_LABELS[fid]
            clone["lines"].append(line)
        out["items"].append(clone)
    return out
