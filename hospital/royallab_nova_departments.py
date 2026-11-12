"""NOVA display departments for the original Royal Lab source catalogue.

The original Royal Lab dbo.Laboratory is not a reliable clinical taxonomy:
source group 1 is called 'Diabetes Profile' but contains LFT, RFT and many
biochemistry assays; group 3 is called '1 h.pp' but contains CBC and coagulation.
Likewise group 21 is called 'CBC' but comprises non-laboratory urology services.
These original group labels and IDs are preserved as provenance, while the
NOVA UI gets a conservative department derived ONLY from the source group.
This module never classifies by a fuzzy test-name match or alters clinical forms.

Source: megdad234/Royallab-Recovery (recovered-results),
output/configuration_tables/dbo__Laboratory.csv and dbo__Test.csv.
"""

# Original dbo.LaboratoryID -> original dbo.Laboratory.Name as recovered.
ORIGINAL_LAB_GROUPS = {
    "1": "Diabetes Profile",
    "2": "Renal Function Test(RFT)",
    "3": "1 h.pp",
    "4": "الأحياء الدقيقة",
    "8": "الهرمونات",
    "9": "الأحياء الجزيئية",
    "10": "المناعة",
    "11": "بنك الدم",
    "12": "العيادات",
    "13": "التمريض",
    "14": "الأشعة والموجات",
    "15": "الأسنان",
    "16": "الصيدلية",
    "17": "البوابة",
    "18": "العمليات الجراحية",
    "19": "عمليات النساء والتوليد",
    "20": "عمليــات جراحة العـظـام",
    "21": "CBC",  # actually urological operations in dbo.Test; NOT CBC
    "22": "عمليات مناظير الجراحيــة",
    "23": "عمليات تخصصيـة جراحة الاطفال",
    "24": "عمليات الاذن والانف والحنجرة",
    "25": "عمليات الولادات الطبيعية",
    "26": "الإحصاء",
    "27": "العلاج الطبيعي",
    "35": "Vivrio Cholerae Ag",
    "43": "Vibrio Cholerae Ag",
    "47": "ALP",
    "49": "Tropnin",
    "53": "Nt-Pro-BNP",
    "54": "التزريع",
}

# Display taxonomy deliberately does not repeat the misleading raw group names.
# Match the ORIGINAL NOVA seed categories (hospital/lab_catalog.py TESTS
# positional tuple category), NOT newly translated Arabic department labels.
DISPLAY_DEPARTMENTS = {
    "1": "Chemistry",
    "2": "Parasitology",
    "3": "Hematology",
    "4": "Microbiology",
    "8": "Hormones",
    "9": "Microbiology",  # no new molecular department until original catalog proves it
    "10": "Immunology",
    "11": "Blood bank",
    "35": "Microbiology",
    "43": "Microbiology",
    "47": "Chemistry",
    "49": "Chemistry",
    "53": "Chemistry",
    "54": "Microbiology",
}
# Where recovered dbo.Laboratory groups lump unrelated tests together,
# use audited source TestID exceptions rather than a fuzzy name heuristic.
SOURCE_TEST_DEPARTMENT_OVERRIDES = {
    "7": "Urinalysis",
    "8": "Parasitology",
    "13": "Parasitology",
    "14": "Parasitology",
    "21": "Hematology",
    "22": "Coagulation",
    "73": "Blood bank",
    "76": "Parasitology",
    "78": "Urinalysis",
    "81": "Urinalysis",
    "84": "Parasitology",
    "87": "Parasitology",
    "95": "Urinalysis",
    "101": "Hematology",
    "115": "Serology",
    "57": "Serology",
    "58": "Serology",
    "59": "Serology",
    "69": "Tumor markers",
    "309": "Serology",
    "347": "Serology",
    "369": "Serology",
}
NON_LAB_GROUP_IDS = frozenset(str(x) for x in range(12, 28))
# This is a source bookkeeping group, not a clinical lab department.
NON_LAB_LABEL = "Non-laboratory services"
UNKNOWN_LABEL = "Uncategorized - Review"
# EXACT previous NOVA-import Arabic categories only. Never overwrite any
# other administrator-created labels.
PREVIOUS_AUTO_ARABIC_CATEGORIES = frozenset((
    "الكيمياء الحيوية", "أمراض الدم والتخثر",
    "التحاليل العامة والطفيليات", "الأحياء الدقيقة والسيرولوجيا",
    "المزارع والأحياء الدقيقة", "الهرمونات", "المناعة",
    "الأحياء الجزيئية", "بنك الدم", "خدمات غير معملية",
))

DEPARTMENT_SCHEMA = """
CREATE TABLE IF NOT EXISTS royal_lab_nova_department_metadata (
    nova_test_id INTEGER PRIMARY KEY,
    source_test_id TEXT NOT NULL,
    source_department_id TEXT NOT NULL,
    original_department_name TEXT NOT NULL,
    nova_display_department TEXT NOT NULL,
    assignment_kind TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_royal_lab_nova_departments_source
    ON royal_lab_nova_department_metadata(source_department_id);
"""


def for_source_test(test):
    """Display label and historical provenance, no source data mutations."""
    if not isinstance(test, dict):
        raise ValueError("Expected source test metadata")
    original_id = str(test.get("source_department_id") or "").strip()
    original_label = ORIGINAL_LAB_GROUPS.get(original_id, "")
    if original_id in DISPLAY_DEPARTMENTS:
        category = SOURCE_TEST_DEPARTMENT_OVERRIDES.get(
            str(test.get("source_test_id") or ""), DISPLAY_DEPARTMENTS[original_id])
        kind = "conservative_lab_source_group"
    elif original_id in NON_LAB_GROUP_IDS:
        # Do not call these assays or silently remove an existing orderable row.
        category = NON_LAB_LABEL
        kind = "non_lab_source_service"
    else:
        category = UNKNOWN_LABEL
        kind = "unrecognized_source_group"
    return {
        "source_test_id": str(test.get("source_test_id") or ""),
        "source_department_id": original_id,
        "original_department_name": original_label,
        "category": category,
        "assignment_kind": kind,
    }


def verify_original_departments(catalog):
    """Audit full extracted data without assuming a lab method from test name."""
    tests = catalog.get("tests", []) if isinstance(catalog, dict) else []
    if len(tests) != 367:
        raise ValueError("The 367 source test records are required")
    missing = [t.get("source_test_id") for t in tests
               if str(t.get("source_department_id") or "").strip()
               not in ORIGINAL_LAB_GROUPS]
    if missing:
        raise ValueError("Unknown Royal Lab source group for TestIDs: " +
                         ", ".join(str(x) for x in missing[:12]))
    results = [for_source_test(t) for t in tests]
    return {
        "test_count": len(results),
        "clinical_groups": len({r["category"] for r in results
                                if r["assignment_kind"] == "conservative_lab_source_group"}),
        "unknown": sum(r["assignment_kind"] == "unrecognized_source_group" for r in results),
        "non_lab_services_retained": sum(r["assignment_kind"] == "non_lab_source_service" for r in results),
    }
