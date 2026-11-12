"""Extract laboratory-result COLUMN identities from historical database exports.

NO patient rows, names, result values, dates, order keys, or identifiers are read.
Use on the original Recovery output/configuration_tables directory. Source test
and analyte relationships are checked by exact IDs, NEVER by similar names.
"""
import csv
import json
import pathlib
import re
from hospital.royallab_field_adapter import build_fields

RESULT_COLUMN = re.compile(r"^AnalyteResult_([0-9]+)_([0-9]+)$")
FILE_NAME = re.compile(r"^dbo__Test_([0-9]+)\.csv$")


def historical_headers(directory, library):
    """Audit only the first (header) CSV record of each historical test export."""
    directory = pathlib.Path(directory)
    original = build_fields(library)
    tests = {str(t["source_id"]): t for t in original["tests"]}
    # Includes missing-test source analytes so their identity stays explicit.
    analytes = {str(x["analyte_id"]): str(x.get("test_id") or "")
                for x in library.get("analytes", [])}
    observed = {}
    unknown = []
    for path in sorted(directory.glob("dbo__Test_*.csv")):
        match = FILE_NAME.fullmatch(path.name)
        if not match:
            continue
        test_id = match.group(1)
        # Only the first line is opened/read. Patient rows never leave storage.
        with path.open("r", encoding="utf-8-sig", newline="") as fh:
            header = fh.readline(250_000)
        if not header or not header.endswith(("\n", "\r")):
            raise ValueError("Missing or oversized clinical result header: " + path.name)
        columns = next(csv.reader([header]))
        if len(columns) != len(set(columns)):
            raise ValueError("Duplicate historical result columns: " + path.name)
        links = []
        for name in columns:
            m = RESULT_COLUMN.fullmatch(name)
            if m is None:
                continue
            analyte_id, format_id = m.groups()
            expected_test = analytes.get(analyte_id)
            link = {"analyte_id": analyte_id, "source_format_id": format_id,
                    "analyte_in_source": expected_test is not None,
                    "test_id_consistent": expected_test == test_id}
            links.append(link)
            if expected_test is None or expected_test != test_id:
                unknown.append({"source_test_id": test_id, **link})
        observed[test_id] = {
            "source_test_exists": test_id in tests,
            "source_test_name": tests.get(test_id, {}).get("name"),
            "historical_format_columns": links,
        }
    return {"exported_test_count": len(observed),
            "matched_column_count": sum(
                sum(x["test_id_consistent"] for x in t["historical_format_columns"])
                for t in observed.values()),
            "unmatched_historical_columns": unknown,
            "historical_test_schemas": observed,
            "patient_rows_read": 0,
            "patient_values_exported": False,
            "clinical_approval": False}


def recovery_for_blocked(directory, library):
    """Identify precisely which blocked tests have original historical headers."""
    from hospital.royallab_native_catalog_store import effective_source_form, is_non_lab_service
    from hospital.royallab_native_result_drafts import validate_source_form
    source = historical_headers(directory, library)
    blocked = []
    for test in build_fields(library)["tests"]:
        form = effective_source_form({
            "source_test_id": test["source_id"], "name": test["name"],
            "source_department_id": str(test["source"].get("LaboratoryID") or ""),
            "review_flags": test["review_flags"], "fields": test["fields"]})
        if is_non_lab_service(form):
            continue
        try:
            validate_source_form(form)
        except ValueError as exc:
            history = source["historical_test_schemas"].get(test["source_id"])
            blocked.append({
                "source_test_id": test["source_id"],
                "source_test_name": test["name"],
                "block_reason": str(exc),
                "has_historical_result_header": history is not None,
                "historical_analyte_format_columns": (
                    history["historical_format_columns"] if history else []),
            })
    return {
        "blocked_tests": blocked, "blocked_count": len(blocked),
        "historically_evidenced_blocked_count": sum(
            x["has_historical_result_header"] for x in blocked),
        "source_provenance": "Royallab-Recovery:49724fa445d7043276abe4e443c403d3f592bfa5",
        "patient_rows_read": 0, "patient_values_exported": False,
        "clinical_approval": False,
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        raise SystemExit("Usage: python -m hospital.royallab_historical_schema_audit <config-tables-dir> <library.json>")
    library = json.loads(pathlib.Path(sys.argv[2]).read_text(encoding="utf-8-sig"))
    print(json.dumps(recovery_for_blocked(sys.argv[1], library),
                     ensure_ascii=False, indent=2))
