"""Audit the bundled NOVA laboratory source without changing patient or catalog data.

Run: python -m hospital.royallab_catalog_audit
Output: JSON counts and per-test review flags; no clinical approval implied.
"""
import json
from collections import Counter
from pathlib import Path
from hospital.royallab_field_adapter import build_fields

SOURCE = Path(__file__).resolve().parent / "royallab_source" / "nova_lab_library.json"

def audit(path=SOURCE):
    library = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    result = build_fields(library)
    tests = result["tests"]
    flagged = [
        {"source_test_id": t["source_id"], "name": t["name"],
         "review_flags": t["review_flags"], "field_count": len(t["fields"])}
        for t in tests if t["review_flags"]
    ]
    focus_terms = ("cbc", "urine", "stool", "malaria", "blood film", "ict")
    focus = [
        {"source_test_id": t["source_id"], "name": t["name"],
         "field_count": len(t["fields"]),
         "review_flags": t["review_flags"],
         "fields": [{"id": f["source_format_id"], "name": f["label"],
                     "kind": f["kind"], "option_count": len(f.get("options", []))}
                    for f in t["fields"]]}
        for t in tests if any(term in str(t["name"]).casefold() for term in focus_terms)
    ]
    flags = Counter(flag for t in tests for flag in t["review_flags"])
    return {
        "test_count": len(tests),
        "source_analyte_count": len(library.get("analytes", [])),
        "source_result_field_count": sum(len(t["fields"]) for t in tests),
        "detached_analyte_count": len(result["detached_analytes"]),
        "field_kinds": result["field_kinds"],
        "tests_requiring_review": len(flagged),
        "review_flags": dict(sorted(flags.items())),
        "flagged_tests": flagged,
        "priority_test_forms": focus,
        "clinical_approval": False,
    }

if __name__ == "__main__":
    print(json.dumps(audit(), ensure_ascii=False, indent=2))
