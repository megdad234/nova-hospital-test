"""Read-only NOVA lab catalogue audit, run after source ZIP extraction and patches.

Does not open a patient database or change prices, test results, or approval flow.
"""
from pathlib import Path
import ast
import collections
import json
import csv

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "hospital" / "lab_catalog.py"

def resolve_static(node, symbols):
    """Resolve literal catalogue declarations without importing or executing code."""
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        if node.id not in symbols:
            raise ValueError("unresolved static name: " + node.id)
        return symbols[node.id]
    if isinstance(node, (ast.List, ast.Tuple)):
        values = []
        for part in node.elts:
            if isinstance(part, ast.Starred):
                values.extend(resolve_static(part.value, symbols))
            else:
                values.append(resolve_static(part, symbols))
        return tuple(values) if isinstance(node, ast.Tuple) else values
    if isinstance(node, ast.Dict):
        return {resolve_static(k, symbols): resolve_static(v, symbols)
                for k, v in zip(node.keys, node.values)}
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return resolve_static(node.left, symbols) + resolve_static(node.right, symbols)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        v = resolve_static(node.operand, symbols)
        if type(v) in (int, float):
            return -v
    raise ValueError("non-literal expression: " + type(node).__name__)


def audit(path=CATALOG):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    tests = []
    parse_warnings = []
    declared = False
    symbols = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            names = [t.id for t in node.targets if isinstance(t, ast.Name)]
            if not names:
                continue
            try:
                value = resolve_static(node.value, symbols)
                for name in names:
                    symbols[name] = value
                if "TESTS" in names:
                    declared = True
                    tests = list(value)
            except (ValueError, TypeError, SyntaxError) as exc:
                if "TESTS" in names:
                    declared = True
                    parse_warnings.append("TESTS assignment: " + type(exc).__name__)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.value is not None:
            try:
                symbols[node.target.id] = resolve_static(node.value, symbols)
            except (ValueError, TypeError, SyntaxError):
                pass
    # Seed extensions may use TESTS.extend; inspect only literal arguments, never execute source.
    for node in tree.body:
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            node = node.value
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) and node.func.value.id == "TESTS" and node.func.attr == "extend" and node.args:
            try:
                tests.extend(ast.literal_eval(node.args[0]))
            except (ValueError, TypeError, SyntaxError) as exc:
                parse_warnings.append("TESTS.extend: " + type(exc).__name__)
    if not declared:
        parse_warnings.append("TESTS assignment missing")
    rows = []
    priority_details = {}
    malformed_parameters = []
    duplicate_parameter_codes = {}
    empty_parameter_tests = []
    malformed_tests = []
    blank_parameter_labels = {}
    blank_parameter_codes = {}
    for item in tests:
        if not isinstance(item, (tuple, list)) or len(item) < 5:
            malformed_tests.append(repr(item)[:160])
            continue
        code, name, category = str(item[0]), str(item[1]), str(item[2])
        params = item[4] if isinstance(item[4], (list, tuple)) else []
        if not isinstance(item[4], (list, tuple)):
            malformed_parameters.append(code)
        if any(not isinstance(p, (tuple, list)) or len(p) < 2 for p in params):
            malformed_parameters.append(code)
        parameter_codes = [str(p[0]).strip() for p in params if isinstance(p, (tuple, list)) and p]
        blank_labels = [str(p[0]) for p in params if isinstance(p, (tuple, list)) and len(p) >= 2 and not str(p[1]).strip()]
        if blank_labels:
            blank_parameter_labels[code] = blank_labels
        blank_codes = [str(p[1]) if len(p) > 1 else "" for p in params if isinstance(p, (tuple, list)) and (not p or not str(p[0]).strip())]
        if blank_codes:
            blank_parameter_codes[code] = blank_codes
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
        "blank_parameter_labels": blank_parameter_labels,
        "blank_parameter_codes": blank_parameter_codes,
        "generic_result_tests": [r for r in rows if r["generic_result_only"]],
        "missing_priority_codes": [code for code in ("GTT", "MALARIA", "URINE", "STOOL", "CBC") if code not in counts],
        "priority_generic_only": [r["code"] for r in rows if r["generic_result_only"] and r["code"] in ("GTT", "MALARIA", "URINE", "STOOL", "CBC")],
        "all_tests": rows,
        "priority_template_details": priority_details,
        "review_required": bool(parse_warnings or malformed_tests or empty_parameter_tests or duplicate_parameter_codes or malformed_parameters or blank_parameter_labels or blank_parameter_codes or any(n > 1 for n in counts.values()) or any(code not in counts for code in ("GTT", "MALARIA", "URINE", "STOOL", "CBC")) or any(r["generic_result_only"] and r["code"] in ("GTT", "MALARIA", "URINE", "STOOL", "CBC") for r in rows)),
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
    for key in ("parse_warnings", "malformed_tests", "duplicate_codes", "empty_parameter_tests", "duplicate_parameter_codes", "malformed_parameter_codes", "blank_parameter_labels", "blank_parameter_codes"):
        lines.append(f"- {key}: {json.dumps(report[key], ensure_ascii=False)}")
    lines += ["", "## Important", "", "A defined field is not proof of clinical correctness. Review each template against approved laboratory forms before changing existing results.", ""]
    summary = ROOT / "lab_catalog_review.md"
    summary.write_text("\n".join(lines), encoding="utf-8")
    # Editable review worksheet, deliberately not an automatic clinical template migration.
    # One row per existing field so a laboratory reviewer can check units,
    # reference intervals and intended input types before any code changes.
    sheet = ROOT / "lab_field_review.csv"
    with sheet.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["test_code", "test_name", "category", "field_code",
                         "field_name", "unit", "reference_range",
                         "review_status", "reviewer_notes"])
        for test_code, definitions in report["priority_template_details"].items():
            for definition in definitions:
                for field in definition["parameter_definitions"]:
                    if not isinstance(field, list):
                        continue
                    values = [str(v) if v is not None else "" for v in field]
                    values += [""] * max(0, 5 - len(values))
                    status = "REVIEW REQUIRED"
                    if not values[0].strip() or not values[1].strip():
                        status = "MISSING FIELD CODE OR LABEL"
                    writer.writerow([test_code, definition["name"], definition["category"],
                                     values[0], values[1], values[2], values[3], status, ""])
    print("LAB_FIELD_REVIEW:", sheet)
    print("LAB_AUDIT_REPORT:", out)
    print("LAB_AUDIT_REVIEW:", summary)
