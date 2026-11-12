"""Inspect NOVA's existing laboratory tables before replacing catalogue rows.

Read-only. No schema assumptions, no writes, no changes to pharmacy or printing.
The output exposes only schema metadata, never patient data.
"""
import json
import sqlite3

TABLES = ("hospital_lab_tests", "hospital_lab_parameters", "hospital_lab_lines",
          "hospital_orders", "hospital_order_items")

def inspect_existing_lab(conn):
    if not isinstance(conn, sqlite3.Connection):
        raise TypeError("SQLite connection required")
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    report = {"tables": {}, "missing": [], "patient_values_read": False,
              "schema_modified": False}
    for name in TABLES:
        if name not in tables:
            report["missing"].append(name)
            continue
        columns = [{"name": row[1], "type": row[2], "not_null": bool(row[3]),
                    "default": row[4], "primary_key": bool(row[5])}
                   for row in conn.execute("PRAGMA table_info(" + name + ")")]
        fks = [{"from": row[3], "to_table": row[2], "to_column": row[4]}
               for row in conn.execute("PRAGMA foreign_key_list(" + name + ")")]
        indexes = [{"name": row[1], "unique": bool(row[2])}
                   for row in conn.execute("PRAGMA index_list(" + name + ")")]
        report["tables"][name] = {"columns": columns, "foreign_keys": fks,
                                   "indexes": indexes}
    report["ready_for_mapping"] = not report["missing"]
    return report

def inspect_file(db_path):
    from pathlib import Path
    path = Path(db_path)
    if not path.is_file():
        raise FileNotFoundError("NOVA database not found")
    uri = path.resolve().as_uri() + "?mode=ro"
    with sqlite3.connect(uri, uri=True) as conn:
        return inspect_existing_lab(conn)

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--database", required=True)
    a = p.parse_args()
    print(json.dumps(inspect_file(a.database), ensure_ascii=False, indent=2))
