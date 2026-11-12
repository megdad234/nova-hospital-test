"""Audit the bundled NOVA laboratory source without changing patient or catalog data.

Run: python -m hospital.royallab_catalog_audit
Output: JSON counts and per-test review flags; no clinical approval implied.
"""
import json
from collections import Counter
from pathlib import Path
from hospital.royallab_field_adapter import build_fields
from hospital.royallab_native_catalog_store import effective_source_form, is_non_lab_service
from hospital.royallab_native_result_drafts import validate_source_form

SOURCE = Path(__file__).resolve().parent / "royallab_source" / "nova_lab_library.json"

def audit(path=SOURCE):
    library = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    result = build_fields(library)
    tests = result["tests"]
    ready = []
    blocked = []
    services = []
    unresolved_field_evidence = []
    excluded_inactive_count = 0
    excluded_blank_placeholder_count = 0
    live_flags = Counter()
    for test in tests:
        active_form = effective_source_form({
            "source_test_id": test["source_id"], "name": test["name"],
            "source_department_id": str(test["source"].get("LaboratoryID") or ""),
            "review_flags": list(test["review_flags"]), "fields": test["fields"]
        })
        if is_non_lab_service(active_form):
            services.append({"source_test_id": test["source_id"], "name": test["name"],
                             "source_department_id": active_form["source_department_id"]})
            continue
        excluded_inactive_count += active_form.get("excluded_inactive_source_fields", 0)
        excluded_blank_placeholder_count += active_form.get("excluded_blank_placeholder_options", 0)
        live_flags.update(active_form.get("review_flags", []))
        try:
            validate_source_form(active_form)
        except ValueError as exc:
            evidence = []
            for field in active_form.get("fields", []):
                if not isinstance(field, dict):
                    continue
                options = field.get("options") or []
                invalid_options = [{"id": str(o.get("id") or ""),
                                    "order": o.get("order"), "active": o.get("active")}
                                   for o in options if isinstance(o, dict) and
                                   not str(o.get("label") or "").strip()]
                kinds = field.get("types") or []
                fallback = (not kinds or str(field.get("source_format_id") or "").startswith("ANALYTE-")
                            or ("ColoseEndedResultFormat" in kinds and not options))
                if invalid_options or fallback or not str(field.get("label") or "").strip():
                    evidence.append({"source_format_id": str(field.get("source_format_id")),
                                     "source_analyte_id": str(field.get("source_analyte_id")),
                                     "field_name": str(field.get("label") or ""),
                                     "kind": field.get("kind"), "source_types": kinds,
                                     "missing_format": bool(fallback),
                                     "blank_options": invalid_options})
            if evidence:
                unresolved_field_evidence.append({
                    "source_test_id": test["source_id"], "name": test["name"], "fields": evidence})
            blocked.append({"source_test_id": test["source_id"], "name": test["name"],
                            "reason": str(exc), "review_flags": active_form.get("review_flags", []),
                            "active_field_count": len(active_form.get("fields", []))})
        else:
            ready.append({"source_test_id": test["source_id"], "name": test["name"],
                          "active_field_count": len(active_form["fields"])})
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
                     "kind": f["kind"], "types": f.get("types", []), "option_count": len(f.get("options", []))}
                    for f in t["fields"]]}
        for t in tests if any(term in str(t["name"]).casefold() for term in focus_terms)
    ]
    # Diagnose orphan source IDs against the full source test set, without guessing relationships.
    source_ids = {str(t["source_id"]) for t in tests}
    source_names = {str(t["source_id"]): str(t["name"]) for t in tests}
    flags = Counter(flag for t in tests for flag in t["review_flags"])
    detached_by_test = Counter(str(x["source_test_id"]) for x in result["detached_analytes"])
    detached_details = [
        {"source_test_id": test_id, "analyte_count": count,
         "source_test_exists": test_id in source_ids,
         "source_test_name": source_names.get(test_id),
         "analytes": [{"source_analyte_id": str(x["analyte"].get("analyte_id", "")),
                       "name": str(x["analyte"].get("name", ""))}
                      for x in result["detached_analytes"] if str(x["source_test_id"]) == test_id]}
        for test_id, count in sorted(detached_by_test.items())
    ]
    # Classify actionable repair work without assuming that a missing relationship
    # can be reconstructed from a similar clinical name.
    review_by_cause = {}
    for t in tests:
        for flag in t["review_flags"]:
            review_by_cause.setdefault(flag, []).append({
                "source_test_id": t["source_id"], "name": t["name"],
                "field_count": len(t["fields"])
            })
    return {
        "repair_queue_by_cause": dict(sorted(review_by_cause.items())),
        "non_lab_service_count": len(services),
        "non_lab_services": services,
        "unresolved_field_evidence": unresolved_field_evidence,
        "clinical_test_count": len(ready) + len(blocked),
        "runtime_ready_test_count": len(ready),
        "runtime_blocked_test_count": len(blocked),
        "runtime_ready_tests": ready,
        "runtime_blocked_tests": blocked,
        "active_review_flags": dict(sorted(live_flags.items())),
        "inactive_fields_excluded_from_entry": excluded_inactive_count,
        "blank_source_placeholders_excluded_from_entry": excluded_blank_placeholder_count,
        "test_count": len(tests),
        "source_analyte_count": len(library.get("analytes", [])),
        "source_result_field_count": sum(len(t["fields"]) for t in tests),
        "detached_analyte_count": len(result["detached_analytes"]),
        "detached_source_test_groups": detached_details,
        "orphan_groups_missing_source_test": sum(not x["source_test_exists"] for x in detached_details),
        "tests_without_analytes": [
            {"source_test_id": t["source_id"], "name": t["name"]}
            for t in tests if not t["fields"]
        ],
        "field_kinds": result["field_kinds"],
        "tests_requiring_review": len(flagged),
        "review_flags": dict(sorted(flags.items())),
        "flagged_tests": flagged,
        "priority_test_forms": focus,
        "clinical_approval": False,
    }

if __name__ == "__main__":
    print(json.dumps(audit(), ensure_ascii=False, indent=2))
