"""Read-only original Royal Lab sibling-form evidence for blocked NOVA clinical tests.

This is NOT test merging, type inference, patient validation or clinical
approval. A source TestID with no linked analytes must retain its separate
identity. These explicitly audited potential relatives may only help humans
prepare reviewed templates. No source option IDs are transplanted.
"""
from hospital.royallab_native_catalog_store import effective_source_form, test_form

# All entries have individually identified original Royal Lab IDs; this is
# intentionally not a fuzzy name-matching/auto-migration algorithm.
# 287/292 and 336/337 have the same source name but MAY use different methods.
# 320/101 are the five-part CBC lineage, NOT the three-part CBC screenshot (21).
# O1/O139 source entries 288/289/291 may be child targets of the cholera cassette.
SIBLING_REFERENCES = {
    "287": [("292", "same_original_name", "Confirm whether this uses the same O1/O139 antigen cassette.")],
    "288": [("292", "possible_parent_components", "O1 may be a result of the parent assay, not a separately billable test.")],
    "289": [("292", "possible_parent_components", "O139 may be a parent-assay component; also compare source ID 291.")],
    "291": [("292", "possible_parent_components", "A second O139 ID; investigate duplicate/parent relationship.")],
    "320": [("101", "five_part_cbc", "Verify the exact five-part hematology analyzer before selecting the 26-field template.")],
    "336": [("337", "same_name_distinct_assays", "The original sibling mixes genotyping, screen and CLIA: select the specific method first."),
            ("249", "related_other_assay", "This source ICT assay is not automatically equivalent to HCV genotyping or screening.")],
    "347": [("309", "same_original_name", "Confirm rapid kit IgG/IgM targets; this is NOT the Widal titre assay.")],
    "353": [("29", "related_specimen_panel", "Body fluid panel varies with fluid type, not necessarily this unspecified test."),
            ("30", "related_specimen_panel", "Confirm fluid specimen and ordered analysis panel before reuse.")],
    "368": [("316", "same_original_name", "Verify 25-hydroxy versus 1,25-dihydroxy method and analyzer-specific unit.")],
    "369": [("251", "related_other_assay", "Dengue Virus and rapid ICT may measure different markers (NS1/IgM/IgG).")],
    "391": [("89", "vitamin_b12_equivalent_name", "Confirm serum B12 analyzer/assay and reported unit."),
            ("315", "vitamin_b12_equivalent_name", "Alternative source B12 profile row: compare method and units.")],
    "352": [("274", "related_timed_sampling", "FBS is only one possible curve time point; do not assume a fixed schedule."),
            ("275", "related_timed_sampling", "One-hour postprandial source test is a related method, not the whole curve."),
            ("276", "related_timed_sampling", "Two-hour postprandial source test is a related method, not the whole curve.")],
}
INACTIVE = (False, 0, "False", "false", "0")
SUGGESTABLE = frozenset(("text", "number", "select"))
MAX_VISIBLE_FIELDS = 120


def _safe_fields(source):
    result = []
    for field in source.get("fields", []):
        if not isinstance(field, dict) or field.get("active") in INACTIVE:
            continue
        kind = field.get("kind")
        label = str(field.get("label") or "").strip()
        format_id = str(field.get("source_format_id") or "").strip()
        if not label or not format_id or format_id.startswith("ANALYTE-") or not field.get("types"):
            continue
        if kind not in SUGGESTABLE:
            continue  # Mixed/related formats need manual method-specific review.
        choices = []
        if kind == "select":
            options = [x for x in field.get("options", []) if isinstance(x, dict)
                       and x.get("active") not in INACTIVE]
            values = [(str(x.get("id") or "").strip(),
                       str(x.get("label") or "").strip()) for x in options]
            if (not values or any(not identity or not text for identity,text in values)
                or len({identity for identity,text in values}) != len(values)
                or len({text.casefold() for identity,text in values}) != len(values)):
                continue
            choices = [text for identity,text in values]
        result.append({
            "source_format_id": format_id,
            "source_analyte_id": str(field.get("source_analyte_id") or ""),
            "label": label, "kind": kind,
            "unit": str(field.get("unit") or ""),
            "option_labels": choices,
            "source_proven_for_target": False,
            "target_can_save_results": False,
        })
        if len(result) >= MAX_VISIBLE_FIELDS:
            break
    return result


def sibling_review_options(conn, catalog_id, source_test_id):
    """Provide explicitly mapped source-form evidence, never modify the target.

    Even if the sibling is entry-ready, its result fields cannot be considered
    source-proven *for the missing target test*. No form is adopted automatically.
    """
    target = str(source_test_id)
    out = []
    for related_id, relation, caution in SIBLING_REFERENCES.get(target, ()):
        try:
            # Original archive, not another locally approved form or patient data.
            source = test_form(conn, catalog_id, related_id)
            effective = effective_source_form(source)
        except (KeyError, ValueError):
            continue
        fields = _safe_fields(effective)
        out.append({
            "related_source_test_id": related_id,
            "related_original_name": str(source.get("name") or ""),
            "relation": relation,
            "method_warning": caution,
            "source_field_count": len(source.get("fields", [])),
            "candidate_field_count": len(fields),
            "fields": fields,
            "review_flags": list(effective.get("review_flags") or []),
            "same_test_identity": False,
            "requires_assay_confirmation": True,
            "requires_independent_approval": True,
            "ready_for_patient_results": False,
            "can_auto_import_to_target": False,
        })
    return out
