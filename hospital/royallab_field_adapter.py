"""Translate Royal Lab source result formats into NOVA input field definitions.
No medical inference, no guessed dropdown options, no database mutations.
"""
from collections import Counter
from hospital.royallab_source_numeric_format_map import (DOUBLE_RESULT_FORMAT_IDS, INTEGER_RESULT_FORMAT_IDS)

def build_fields(library):
    if not isinstance(library,dict):raise ValueError("Royal Lab source must be a JSON object")
    tests=library.get("tests",[])
    analytes=library.get("analytes",[])
    if len(tests)!=367 or len(analytes)!=1245:raise ValueError("Royal Lab source is incomplete")
    ids=[str(t["TestID"]) for t in tests]
    if len(set(ids))!=len(ids):raise ValueError("duplicate source test IDs")
    analyte_ids=[str(a.get("analyte_id")) for a in analytes]
    if len(set(analyte_ids))!=len(analyte_ids):raise ValueError("duplicate source analyte IDs")
    by_test={str(t["TestID"]):{"source_id":str(t["TestID"]),"name":t.get("Name",""),"source":t,"fields":[],"review_flags":[]} for t in tests}
    detached=[]
    for a in analytes:
        tid=str(a.get("test_id",""))
        formats=a.get("result_formats",[])
        fields=[]
        for f in formats:
            kinds=set(f.get("types") or [])
            # The extracted JSON knows OpenEndedResultFormat but omitted its
            # Double/Integer subtype. Restore ONLY source-proven subtype IDs
            # from the original database relationship tables. Do not coerce
            # explicitly string or dropdown formats into numbers.
            original_format_id=str(f.get("id") or "")
            if ("OpenEndedResultFormat" in kinds and
                    "StringResultFormat" not in kinds and
                    "ColoseEndedResultFormat" not in kinds):
                if original_format_id in DOUBLE_RESULT_FORMAT_IDS:
                    kinds.add("DoubleResultFormat")
                elif original_format_id in INTEGER_RESULT_FORMAT_IDS:
                    kinds.add("IntegerResultFormat")
            options=[{"id":str(o.get("id","")),"label":o.get("label",""),"active":o.get("active"),"order":o.get("order"),"is_normal":o.get("is_normal")} for o in f.get("options",[])]
            if "ColoseEndedResultFormat" in kinds and options and ({"StringResultFormat","OpenEndedResultFormat","DoubleResultFormat","IntegerResultFormat"} & kinds):
                kind="select_or_text"
            elif "ColoseEndedResultFormat" in kinds and options:
                kind="select"
            elif "DoubleResultFormat" in kinds or "IntegerResultFormat" in kinds:
                kind="number"
            elif "StringResultFormat" in kinds or "OpenEndedResultFormat" in kinds:
                kind="text"
            elif "RelatedResultFormat" in kinds:
                kind="related"
            else:kind="text"  # Source lacks a usable result format; retain as editable free text, never infer clinical ranges/options.
            if kind=="select_or_text" and ("DoubleResultFormat" in kinds or "IntegerResultFormat" in kinds):
                kind="select_or_number"
            fields.append({"source_analyte_id":str(a["analyte_id"]),"source_format_id":str(f.get("id") or ("ANALYTE-" + str(a["analyte_id"]) + "-FORMAT-" + str(len(fields)))),
                "label":(str(f.get("title") or "").strip() or str(a.get("name") or "").strip()),"kind":kind,
                "types":sorted(kinds),"unit":f.get("unit") or "","options":options,
                "numeric_ranges":a.get("numeric_ranges",[]),"text_ranges":a.get("text_ranges",[]),
                "required":a.get("required"),"active":a.get("active"),
                "source_analyte":a})
        if not fields:
            fields=[{"source_analyte_id":str(a["analyte_id"]),"source_format_id":"ANALYTE-" + str(a["analyte_id"]),
                "label":a.get("name",""),"kind":"text","options":[],
                "unit":"","numeric_ranges":a.get("numeric_ranges",[]),"text_ranges":a.get("text_ranges",[]),
                "source_analyte":a,"types":[],"required":a.get("required"),"active":a.get("active")}]
        if tid in by_test:by_test[tid]["fields"].extend(fields)
        else:detached.append({"source_test_id":tid,"analyte":a,"fields":fields})
    for test in by_test.values():
        if not test["fields"]:test["review_flags"].append("no_source_analytes")
        if any(str(f["source_format_id"]).startswith("ANALYTE-") or not f["types"] or ("ColoseEndedResultFormat" in f["types"] and not f["options"]) for f in test["fields"]):test["review_flags"].append("source_format_missing_or_incomplete_free_text_fallback")
        format_ids=[str(f["source_format_id"]) for f in test["fields"]]
        if len(format_ids)!=len(set(format_ids)):test["review_flags"].append("duplicate_source_format_ids")
        if any(not str(f.get("label") or "").strip() for f in test["fields"]):test["review_flags"].append("missing_source_field_label")
        if any(f.get("active") in (False,0,"False","false","0") for f in test["fields"]):test["review_flags"].append("inactive_source_field")
        if any(f["kind"].startswith("select") and (not f.get("options") or any(not str(o.get("id") or "").strip() for o in f["options"]) or len({str(o["id"]) for o in f["options"]})!=len(f["options"])) for f in test["fields"]):test["review_flags"].append("missing_or_duplicate_source_option_ids")
        if any(f["kind"].startswith("select") and any(not str(o.get("label") or "").strip() for o in f.get("options",[])) for f in test["fields"]):test["review_flags"].append("missing_source_option_label")
        if any(f["kind"]=="unknown" for f in test["fields"]):test["review_flags"].append("unknown_result_format")
        if any(f["kind"]=="related" for f in test["fields"]):test["review_flags"].append("related_result_format_requires_ui_support")
        if any(f["kind"].startswith("select_or_") for f in test["fields"]):test["review_flags"].append("mixed_format_requires_combobox")
    return {"tests":list(by_test.values()),"detached_analytes":detached,
            "field_kinds":dict(Counter(f["kind"] for t in by_test.values() for f in t["fields"]))}
