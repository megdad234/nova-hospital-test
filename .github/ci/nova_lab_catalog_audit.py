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
    malformed_parameters = []
    duplicate_parameter_codes = {}
    empty_parameter_tests = []
    malformed_tests = []
    for item in tests:
        if not isinstance(item, (tuple, list)) or len(item) < 5:
            malformed_tests.append(repr(item)[:160])
            continue
        code, name, category = str(item[0]), str(item[1]), str(item[2])
        params = item[4] if isinstance(item[4], (list, tuple)) else []
        if any(not isinstance(p, (tuple, list)) or len(p) == 0 for p in params):
            malformed_parameters.append(code)
        parameter_codes = [str(p[0]).strip() for p in params if isinstance(p, (tuple, list)) and p]
        repeated = sorted(code for code, count in collections.Counter(parameter_codes).items() if count > 1)
        if repeated:
            duplicate_parameter_codes[code] = repeated
        if not params:
            empty_parameter_tests.append(code)
        generic = (len(params) == 1 and isinstance(params[0], (tuple, list)) and len(params[0]) > 0 and str(params[0][0]).strip().upper() == "RESULT")
        rows.append({"code": code, "name": name, "category": category, "parameters": len(params), "generic_result_only": generic, "parameter_codes": parameter_codes})
    counts = collections.Counter(row["code"] for row in rows)
    return {
        "catalogue_file": str(path),
        "parsed_tests": len(rows),
        "malformed_tests": malformed_tests,
        "empty_parameter_tests": sorted(set(empty_parameter_tests)),
        "duplicate_parameter_codes": duplicate_parameter_codes,
        "malformed_parameter_codes": sorted(set(malformed_parameters)),
        "duplicate_codes": sorted(code for code, count in counts.items() if count > 1),
        "generic_result_tests": [r for r in rows if r["generic_result_only"]],
        "missing_priority_codes": [code for code in ("GTT", "MALARIA", "URINE", "STOOL", "CBC") if code not in counts],
        "priority_generic_only": [r["code"] for r in rows if r["generic_result_only"] and r["code"] in ("GTT", "MALARIA", "URINE", "STOOL", "CBC")],
        "all_tests": rows,
        "review_required": bool(malformed_tests or empty_parameter_tests or duplicate_parameter_codes or malformed_parameters or any(n > 1 for n in counts.values()) or any(code not in counts for code in ("GTT", "MALARIA", "URINE", "STOOL", "CBC")) or any(r["generic_result_only"] and r["code"] in ("GTT", "MALARIA", "URINE", "STOOL", "CBC") for r in rows)),
        "note": "Static source inspection only. Runtime database may contain additional or locally modified tests."
    }

if __name__ == "__main__":
    report = audit()
    out = ROOT / "lab_catalog_audit.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("LAB_AUDIT:", report["parsed_tests"], "tests,", len(report["generic_result_tests"]), "generic-only")
    print("LAB_AUDIT_EMPTY_PANELS:", report["empty_parameter_tests"])
    print("LAB_AUDIT_DUPLICATE_PARAMETER_CODES:", report["duplicate_parameter_codes"])
    print("LAB_AUDIT_PRIORITY_GENERIC:", report["priority_generic_only"])
    print("LAB_AUDIT_MISSING_PRIORITY:", report["missing_priority_codes"])
    print("LAB_AUDIT_REVIEW_REQUIRED:", report["review_required"])
    print("LAB_AUDIT_REPORT:", out)
