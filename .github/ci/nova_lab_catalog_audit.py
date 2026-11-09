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
    parse_warnings = []
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "TESTS" for t in node.targets):
            try:
                tests = list(ast.literal_eval(node.value))
            except (ValueError, TypeError, SyntaxError) as exc:
                parse_warnings.append("TESTS assignment: " + type(exc).__name__)
            break
    # Seed extensions may use TESTS.extend; inspect only literal arguments, never execute source.
    for node in tree.body:
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            node = node.value
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) and node.func.value.id == "TESTS" and node.func.attr == "extend" and node.args:
            try:
                tests.extend(ast.literal_eval(node.args[0]))
            except (ValueError, TypeError, SyntaxError) as exc:
                parse_warnings.append("TESTS.extend: " + type(exc).__name__)
    if not any(isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "TESTS" for t in node.targets) for node in tree.body):
        parse_warnings.append("TESTS assignment missing")
    rows = []
    priority_details = {}
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
        if code in ("GTT", "MALARIA", "URINE", "STOOL", "CBC"):
            priority_details.setdefault(code, []).append({"name": name, "category": category, "parameter_definitions": [list(p) if isinstance(p, (tuple, list)) else repr(p) for p in params]})
    counts = collections.Counter(row["code"] for row in rows)
    return {
        "catalogue_file": str(path),
        "parse_warnings": parse_warnings,
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
        "priority_template_details": priority_details,
        "review_required": bool(parse_warnings or malformed_tests or empty_parameter_tests or duplicate_parameter_codes or malformed_parameters or any(n > 1 for n in counts.values()) or any(code not in counts for code in ("GTT", "MALARIA", "URINE", "STOOL", "CBC")) or any(r["generic_result_only"] and r["code"] in ("GTT", "MALARIA", "URINE", "STOOL", "CBC") for r in rows)),
        "note": "Static source inspection only. Runtime database may contain additional or locally modified tests."
    }

if __name__ == "__main__":
    report = audit()
    out = ROOT / "lab_catalog_audit.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("LAB_AUDIT:", report["parsed_tests"], "tests,", len(report["generic_result_tests"]), "generic-only")
    print("LAB_AUDIT_PARSE_WARNINGS:", report["parse_warnings"])
    print("LAB_AUDIT_EMPTY_PANELS:", report["empty_parameter_tests"])
    print("LAB_AUDIT_DUPLICATE_PARAMETER_CODES:", report["duplicate_parameter_codes"])
    print("LAB_AUDIT_PRIORITY_GENERIC:", report["priority_generic_only"])
    print("LAB_AUDIT_MISSING_PRIORITY:", report["missing_priority_codes"])
    print("LAB_AUDIT_REVIEW_REQUIRED:", report["review_required"])
    lines = [
        "# NOVA Laboratory Catalogue — Read-only Review",
        "",
        "Generated from extracted source; not from patient records.",
        "",
        f"- Parsed tests: {report['parsed_tests']}",
        f"- Manual review required: {report['review_required']}",
        f"- Unparseable declarations: {len(report['parse_warnings'])}",
        f"- Malformed test entries: {len(report['malformed_tests'])}",
        f"- Duplicate test codes: {len(report['duplicate_codes'])}",
        f"- Empty panels: {len(report['empty_parameter_tests'])}",
        f"- Duplicate parameter codes within panels: {len(report['duplicate_parameter_codes'])}",
        f"- Generic-result-only tests: {len(report['generic_result_tests'])}",
        "",
        "## Priority tests",
        "",
        "| Test code | Status | Defined parameter codes |",
        "|---|---|---|",
    ]
    for code in ("GTT", "MALARIA", "URINE", "STOOL", "CBC"):
        entries = [r for r in report["all_tests"] if r["code"] == code]
        if not entries:
            lines.append(f"| {code} | MISSING | — |")
            continue
        for entry in entries:
            status = "GENERIC ONLY" if entry["generic_result_only"] else ("EMPTY" if not entry["parameters"] else "DEFINED — verify clinically")
            fields = ", ".join(entry["parameter_codes"]) or "—"
            lines.append(f"| {code} | {status} | {fields} |")
    lines += ["", "## Other findings", ""]
    for key in ("parse_warnings", "malformed_tests", "duplicate_codes", "empty_parameter_tests", "duplicate_parameter_codes", "malformed_parameter_codes"):
        lines.append(f"- {key}: {json.dumps(report[key], ensure_ascii=False)}")
    lines += ["", "## Important", "", "A defined field is not proof of clinical correctness. Review each template against approved laboratory forms before changing existing results.", ""]
    summary = ROOT / "lab_catalog_review.md"
    summary.write_text("\\n".join(lines), encoding="utf-8")
    print("LAB_AUDIT_REPORT:", out)
    print("LAB_AUDIT_REVIEW:", summary)
