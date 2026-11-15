"""Evidence-limited laboratory worksheet *suggestions* for NOVA (2026-11-15).

The user supplied a handwritten assay list: U/S-HCG, TFT, VDRL, ICT Brucella,
ICT Dengue, CRP, ICT HBsAg/HIV/HCV and Vitamin D. Check original RoyalLabDB
identities before exposing any options. This module NEVER installs a live
result field, mutates source entries, infers reagent-specific ranges or creates
tests. Method candidates require the EXISTING NOVA two-person review.

Non-interchangeable source identities:
  58: Widal for Brucella (titres) != an ICT Brucella kit (NO source ICT row).
  251: Dengue virus results != 369: ICT Dengue (NO source analytes).
  317: standalone CRP has analyte 1304 but NO source ResultFormat;
       qualitative Latex and quantitative mg/L are distinct method choices.
  38: TFT has five numeric source fields and conflicting FT4 references;
       316: Vitamin D numeric, 368: different empty source row.
"""
from copy import deepcopy

CHOICES = ["Positive", "Negative"]


def _field(key, label, kind="select", options=None, unit=""):
    if kind not in ("text", "number", "select"):
        raise ValueError("Unrecognized suggested field type")
    return {"key":key,"label":label,"kind":kind,"unit":unit,
            "options":list(options if options is not None else
                           (CHOICES if kind=="select" else [])),
            "reference":"","reference_source":"","required":False}


def _variant(identifier, label, fields, warning):
    return {"variant_id":identifier,"label":label,
            "fields":deepcopy(fields),
            "warning":warning,
            "source_proven":False,
            "ready_for_patient_results":False,
            "requires_kit_and_method_verification":True,
            "requires_independent_approval":True}


def review_method_variants(source_test_id):
    """Advisory alternatives for specific SOURCE-INCOMPLETE catalog tests only."""
    source_id=str(source_test_id)
    if source_id=="317":  # C.Reactive Protien, analyte 1304 has no ResultFormat
        return [
            _variant("crp-qualitative-latex","CRP Qualitative (Latex)",
                     [_field("crp_result","CRP (Qualitative)")],
                     "Only if the actual Latex/rapid kit uses these qualitative labels. "
                     "Confirm reagent procedure, any titer fields and whether the method is qualitative."),
            _variant("crp-quantitative-mg-l","CRP Quantitative (mg/L)",
                     [_field("crp_value","CRP (Quantitative)","number",unit="mg/L")],
                     "Use mg/L ONLY when the local analyzer really reports mg/L. "
                     "Do not reuse source CRP 317's malformed range or any Latex options."),
        ]
    if source_id=="369":  # 'ict for dange fever', no original analytes
        return [
            _variant("dengue-ns1-only","Dengue ICT — NS1-only kit",
                     [_field("ns1","NS1 Ag")],
                     "Select only when the cassette has an NS1 antigen line; document kit, timing and invalid cassette procedure."),
            _variant("dengue-igm-igg","Dengue ICT — IgM/IgG kit",
                     [_field("igm","Dengue IgM"),_field("igg","Dengue IgG")],
                     "Select only when the cassette reports both IgM and IgG independently. Do not assume NS1."),
            _variant("dengue-combined","Dengue ICT — NS1/IgM/IgG kit",
                     [_field("ns1","NS1 Ag"),_field("igm","Dengue IgM"),
                      _field("igg","Dengue IgG")],
                     "Use only if the manufacturer's cassette reports all THREE lines separately. "
                     "Invalid cassette is not a Negative result."),
        ]
    if source_id=="368":  # lowercase vitamin d, with no source analytes
        return [
            _variant("vitamin-d-25oh","Vitamin D — 25-OH (quantitative)",
                     [_field("vitamin_d","25-OH Vitamin D","number")],
                     "Only if the exact test measures 25-OH vitamin D. Set unit and "
                     "age/method-specific reference from the actual analyzer, not by copying 316."),
            _variant("vitamin-d-125oh","Vitamin D — 1,25-(OH)2 (quantitative)",
                     [_field("vitamin_d","1,25-(OH)2 Vitamin D","number")],
                     "Different analyte from 25-OH; confirm the kit and unit; do not copy 316."),
        ]
    return []


def brucella_ict_local_templates():
    """Genuine ICT Brucella is ABSENT from RoyalLabDB; use NOVA-LOCAL review.

    Variants are kit-dependent starting points, NOT source-derived definitions.
    No fixed price, reference interval, or implicit patient activation.
    """
    variants = [
        _variant("brucella-ict-combined","ICT Brucella — combined/total Ab",
                 [_field("brucella_ab","Brucella Ab (ICT)")],
                 "Only if the manufacturer reports ONE combined result; "
                 "do not substitute Widal B. abortus/B. melitensis titre fields."),
        _variant("brucella-ict-igm-igg","ICT Brucella — separate IgM and IgG",
                 [_field("brucella_igm","Brucella IgM"),
                  _field("brucella_igg","Brucella IgG")],
                 "Only if the cassette reports separate IgM/IgG lines. "
                 "Confirm manufacturer, method, specimen and invalid test rules."),
    ]
    result = {
        "template_group":"ict-brucella",
        "name":"ICT for Brucella",
        "section":"Serology",
        "price":None,
        "method":"",
        "evidence":"",
        "rationale":"Handwritten laboratory request; no matching original Royal Lab ICT Brucella TestID.",
        "state":"suggestion_only",
        "ready_for_patient_results":False,
        "reference_ranges_verified":False,
        "requires_independent_approval":True,
        "must_not_replace_source_test_id":"58",
        "source_archive_has_brucella_ict":False,
        "warning":"Choose only the kit-confirmed layout, supply a real price and protocol, "
                  "and use existing separate administrator approval. Widal for Brucella "
                  "(TestID 58) must remain unchanged.",
        "variants":variants,
    }
    return deepcopy(result)


def review_variant_candidates(source_test_id):
    """Render-friendly review choices: no signed-off source identity claimed."""
    output=[]
    for variant in review_method_variants(source_test_id):
        output.append({**variant,"fields":[{
            "label":f["label"],"kind":f["kind"],"unit":f["unit"],
            "option_labels":list(f["options"]),"source_proven":False,
        } for f in variant["fields"]]})
    return output
