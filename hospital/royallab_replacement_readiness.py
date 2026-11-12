"""Non-destructive replacement-catalog readiness checks.

NOVA's original lab catalogue must never be shown as the Royal Lab catalogue.
This guard is for runtime startup and integration tests, not patient migration.
"""
from hospital.royallab_native_catalog_api import catalog_response, form_response

def verify_replacement_catalog(conn):
    catalog = catalog_response(conn, limit=500)
    tests = catalog["tests"]
    if catalog["total"] != 367 or len(tests) != 367:
        raise RuntimeError("Royal Lab replacement catalog must expose exactly 367 tests")
    ids = [str(t["source_test_id"]) for t in tests]
    if len(set(ids)) != 367:
        raise RuntimeError("Duplicate Royal Lab test identifiers")
    fields = 0
    choices = 0
    missing = []
    for test in tests:
        form = form_response(conn, test["source_test_id"])["test"]
        for field in form.get("fields", []):
            fields += 1
            if field.get("source_format_id") is None:
                missing.append((test["source_test_id"], field.get("label")))
            choices += len(field.get("options") or [])
    if fields < 1000 or choices == 0:
        raise RuntimeError("Royal Lab forms or dropdown options are incomplete")
    return {
        "source": "RoyalLabDB.bak",
        "replacement_catalog_ready": True,
        "tests": 367,
        "fields": fields,
        "dropdown_choices": choices,
        "fields_without_source_format_id": len(missing),
        "legacy_nova_name_matching": False,
        "printing_modified": False,
    }
