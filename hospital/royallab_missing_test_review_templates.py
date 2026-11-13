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
    "369": "https://www.who.int/publications/i/item/B09394",
    "320": "https://hl7.org/fhir/observation-definitions.html",
    "368": "https://medlineplus.gov/lab-tests/vitamin-d-test/",
    "391": "https://hl7.org/fhir/observation-definitions.html",
    "351": "https://medlineplus.gov/lab-tests/ammonia-levels/",
}


def build_review_proposals(library):
    """Produce ONLY non-operative proposals from exact source identifiers."""
    from hospital.royallab_native_catalog_store import is_non_lab_service
    tests = build_fields(library)["tests"]
    output = []
    for test in tests:
        if test["fields"] or "no_source_analytes" not in test["review_flags"]:
            continue
        if is_non_lab_service({"fields": [], "source_department_id": str(test["source"].get("LaboratoryID") or "")}):
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


# Exactly the 20 clinical source tests with NO source analyte definitions as of
# the audited 2026-11-12 original catalogue. Every entry is an advisory,
# method-selection question, NOT an operational answer set or normal range.
# Sources establish clinical concepts only; local IFU and professional review
# remain mandatory for actual choices, units, limits and specimens.
REVIEW_EVIDENCE = {
    "287": ("Vibrio cholerae Ag", "Confirm stool antigen RDT versus culture/PCR and the manufacturer's O1/O139 cassette layout.",
            "https://www.cdc.gov/cholera/php/laboratories/cholera-clinical-detection.html"),
    "288": ("O1", "Confirm whether O1 is a component of the cholera parent test, not an independently orderable patient test.",
            "https://www.cdc.gov/yellow-book/hcp/travel-associated-infections-diseases/cholera.html"),
    "289": ("O139", "Confirm whether this O139 row is an assay component or a standalone test; distinguish original duplicated identifiers.",
            "https://www.cdc.gov/yellow-book/hcp/travel-associated-infections-diseases/cholera.html"),
    "291": ("O139", "Same clinical name as another source row: compare the exact source test IDs and local assay before using either.",
            "https://www.cdc.gov/cholera/php/laboratories/cholera-clinical-detection.html"),
    "320": ("CBC 5-part", "Confirm the exact hematology analyzer's exported fields, units and five differential populations; do not assume a 3-part panel.",
            "https://medlineplus.gov/lab-tests/blood-differential/"),
    "336": ("HCV", "First choose anti-HCV antibody screening or HCV RNA NAT; they use different fields and interpretation.",
            "https://www.cdc.gov/hepatitis-c/hcp/diagnosis-testing/"),
    "339": ("Hemocytine", "Source label has unclear clinical identity; obtain original request slip or assay documentation before defining any field.",
            ""),
    "340": ("Herpes", "Determine HSV-1/HSV-2 NAAT versus type-specific serology and specimen. HSV IgM is not recommended as a routine source-independent fallback.",
            "https://www.cdc.gov/std/treatment-guidelines/herpes.htm"),
    "341": ("ADA", "Confirm ADA specimen (e.g. pleural fluid), method and reporting unit with the actual laboratory protocol.",
            "https://www.mayocliniclabs.com/test-catalog/overview/75664"),
    "343": ("Food Panel Profile", "Specify exact individual-allergen or pooled reagent panel and analyzer; identical panel names may measure different food allergens.",
            "https://labmed.uw.edu/test-guide/view/LFODP"),
    "344": ("Food Panel 2", "This name is not a unique panel: the Mayo Food Panel 2 and other labs have different allergen membership. Confirm local manufacturer's exact list.",
            "https://www.mayocliniclabs.com/test-catalog/overview/86207"),
    "347": ("ICT for typhoid", "Confirm the kit antigen/antibody principle and whether IgM, IgG, or combined results are actually supplied.",
            "https://www.cdc.gov/yellow-book/hcp/travel-associated-infections-diseases/typhoid-and-paratyphoid-fever.html"),
    "352": ("Blood Sugar Curve", "Identify fasting, 1-hour, 2-hour and optional additional time points from the actual local protocol; the NOVA GTT with urine glucose form is a separate test.",
            "https://www.niddk.nih.gov/health-information/professionals/clinical-tools-patient-management/diabetes/diabetes-prediabetes"),
    "353": ("Blood Fluid Analysis", "Specify the exact body fluid and ordered biochemistry, cell-count or microbiology panel before selecting result fields.",
            "https://labmed.uw.edu/test-guide/view/CSFC"),
    "368": ("Vitamin D", "Confirm whether the method measures 25-hydroxyvitamin D or 1,25-dihydroxyvitamin D; they are different laboratory tests.",
            "https://www.mayocliniclabs.com/test-catalog/overview/8822"),
    "369": ("Dengue ICT", "Confirm manufacturer's NS1, IgM, IgG cassette targets, timing and permissible invalid results.",
            "https://www.who.int/publications/i/item/B09394"),
    "378": ("RPL", "Ambiguous legacy abbreviation; require the original laboratory name and method.",
            ""),
    "391": ("Vitamin B12", "Confirm quantitative serum assay, analyzer and reporting unit; verify reagent-specific limits.",
            "https://www.mayocliniclabs.com/test-catalog/Overview/9154"),
    "346": ("Fructose qualitative", "Confirm whether the specimen is semen, and whether the kit really uses a qualitative result.",
            "https://www.mayocliniclabs.com/test-catalog/overview/92187"),
    "351": ("Blood Ammonia", "This is quantitative plasma ammonia, but analyzer unit, age group and time-sensitive EDTA/plasma handling must be confirmed locally.",
            "https://www.mayocliniclabs.com/test-catalog/Overview/35130"),
}

# Additional 7 blocked clinical-source rows; these are SOURCE-IDENTITY review
# questions, not instructions to reactivate legacy analytes.
REVIEW_EVIDENCE.update({
    "14": ("ICT for Malaria",
           "Identify exact HRP2/pLDH or other rapid kit lines. Original microscopy Density/Stage/Type selections do not define ICT results.",
           "https://www.who.int/teams/global-malaria-programme/case-management/diagnosis/rapid-diagnostic-tests"),
    "60": ("HbA1c",
           "Original source has inactive parameters. Verify analyzer and NGSP (%) versus IFCC (mmol/mol) output; do not reactivate them automatically.",
           "https://ngsp.org/ifcc.asp"),
    "237": ("ALT",
            "Original result field is inactive; verify assay U/L and analyzer-specific reference interval, preserving historical field evidence.",
            "https://medlineplus.gov/lab-tests/alt-blood-test/"),
    "239": ("G.G.T",
            "Original GGT result field is inactive; verify local serum assay and unit with the installed analyzer.",
            "https://medlineplus.gov/lab-tests/gamma-glutamyl-transferase-ggt-test/"),
    "263": ("CSF for C/S",
            "An original analyte has no verified source label. Use specimen, Gram stain, culture, organism/susceptibility information from the actual lab workflow; never label a missing source field from guesswork.",
            "https://labmed.uw.edu/test-guide/view/CSFC"),
    "290": ("O 1",
            "Incomplete source result format and inactive field; verify whether this is the O1 component of source cholera antigen/culture assay.",
            "https://www.cdc.gov/cholera/php/laboratories/cholera-clinical-detection.html"),
    "310": ("Sample Collection Services",
            "This appears to be an operational service: do not demand laboratory analyte results to clear the clinical blocked-test count; confirm non-reportable service classification.",
            "https://docs.openelisci.org/en/latest/OEGlobal_AdminManual_2024/"),
})
