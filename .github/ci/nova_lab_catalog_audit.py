"""Read-only NOVA lab catalogue audit, run after source ZIP extraction and patches.

Does not open a patient database or change prices, test results, or approval flow.
"""
from pathlib import Path
import ast
import collections
import json

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "hospital" / "lab_catalog.py"

def audit(path=CATALOG):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    tests = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "TESTS" for t in node.targets):
            try:
                tests = list(ast.literal_eval(node.value))
            except (ValueError, TypeError):
                pass
            break
    # Seed extensions may use TESTS.extend; inspect only literal arguments, never execute source.
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) and node.func.value.id == "TESTS" and node.func.attr == "extend" and node.args:
            try:
                tests.extend(ast.literal_eval(node.args[0]))
            except (ValueError, TypeError):
                pass
    rows = []
    for item in tests:
        if not isinstance(item, (tuple, list)) or len(item) < 5:
            continue
        code, name, category = str(item[0]), str(item[1]), str(item[2])
        params = item[4] if isinstance(item[4], (list, tuple)) else []
        generic = len(params) == 1 and str(params[0][0]).upper() == "RESULT"
        rows.append({"code": code, "name": name, "category": category, "parameters": len(params), "generic_result_only": generic})
    counts = collections.Counter(row["code"] for row in rows)
    return {
        "catalogue_file": str(path),
        "parsed_tests": len(rows),
        "duplicate_codes": sorted(code for code, count in counts.items() if count > 1),
        "generic_result_tests": [r for r in rows if r["generic_result_only"]],
        "missing_priority_codes": [code for code in ("GTT", "MALARIA", "URINE", "STOOL", "CBC") if code not in counts],
        "all_tests": rows,
        "note": "Static source inspection only. Runtime database may contain additional or locally modified tests."
    }

if __name__ == "__main__":
    report = audit()
    out = ROOT / "lab_catalog_audit.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("LAB_AUDIT:", report["parsed_tests"], "tests,", len(report["generic_result_tests"]), "generic-only")
    print("LAB_AUDIT_REPORT:", out)
