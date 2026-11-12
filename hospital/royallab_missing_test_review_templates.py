"""Review-only source-missing laboratory templates, NOT patient result forms.

For source tests with no analyte rows, publicly documented laboratory test
types can help the laboratory director build an appropriate local template.
Never infer assay methods, manufacturer answer lists, units, reference ranges,
or automatically activate these definitions.
"""
from hospital.royallab_field_adapter import build_fields

# A candidate is never an operational result field until local clinical review.
# Empty lists indicate that the source name is too ambiguous to suggest fields.
CANDIDATE_FIELDS = {
    "287": [], "288": [], "289": [], "291": [],
    "320": [
        ("WBC", "number"), ("RBC", "number"), ("Hemoglobin", "number"),
        ("Hematocrit", "number"), ("Platelet count", "number"),
        ("Neutrophils", "number"), ("Lymphocytes", "number"),
        ("Monocytes", "number"), ("Eosinophils", "number"),
        ("Basophils", "number"),
    ],
    "336": [],  # HCV antibody vs RNA must be identified first.
    "339": [], "340": [],  # Unclear test name or HSV assay method.
    "341": [("ADA", "number")],  # Specimen, method and unit still unknown.
    "343": [], "344": [],  # Allergy panel composition / assay unknown.
    "347": [],  # Local ICT kit determines antigens and permissible choices.
    "352": [],  # Time points depend on the actual glucose-curve protocol.
    "353": [],  # Fluid type and required panel unknown.
    "368": [("Vitamin D measurement", "number")],  # 25-OH vs 1,25 unresolved.
    "369": [],  # NS1 vs IgM/IgG vs combined RDT unknown.
    "378": [],  # RPL abbreviation ambiguous in recovered source.
    "391": [("Vitamin B12 measurement", "number")],
    "346": [("Fructose qualitative observation", "text")],
    "351": [("Blood ammonia measurement", "number")],
}

REFERENCES = {
    "336": "https://www.cdc.gov/hepatitis-c/hcp/diagnosis-testing/index.html",
    "369": "https://www.who.int/publications/i/item/9789240016096",
    "320": "https://hl7.org/fhir/observation-definitions.html",
    "368": "https://hl7.org/fhir/observation-definitions.html",
    "391": "https://hl7.org/fhir/observation-definitions.html",
    "351": "https://hl7.org/fhir/observation-definitions.html",
}


def build_review_proposals(library):
    """Produce ONLY non-operative proposals from exact source identifiers."""
    tests = build_fields(library)["tests"]
    output = []
    for test in tests:
        if test["fields"] or "no_source_analytes" not in test["review_flags"]:
            continue
        source_id = test["source_id"]
        # No clinically undocumented choice list, unit or normal range is copied.
        fields = [{"label": label, "suggested_kind": kind, "unit": None,
                   "options": None, "reference_ranges": None}
                  for label, kind in CANDIDATE_FIELDS.get(source_id, [])]
        output.append({
            "source_test_id": source_id,
            "original_source_name": test["name"],
            "suggested_fields": fields,
            "status": "proposed_for_local_lab_review",
            "requires_assay_specification": True,
            "requires_laboratory_director_approval": True,
            "can_save_patient_results": False,
            "can_publish": False,
            "provenance": "public_guidance_candidate_not_legacy_source",
            "reference": REFERENCES.get(source_id),
        })
    return output
