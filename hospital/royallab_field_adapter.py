"""Translate Royal Lab source result formats into NOVA input field definitions.
No medical inference, no guessed dropdown options, no database mutations.
"""
from collections import Counter

def build_fields(library):
    if not isinstance(library,dict):raise ValueError("Royal Lab source must be a JSON object")
    tests=library.get("tests",[])
    analytes=library.get("analytes",[])
    if len(tests)!=367 or len(analytes)!=1245:raise ValueError("Royal Lab source is incomplete")
    by_test={str(t["TestID"]):{"source_id":str(t["TestID"]),"name":t.get("Name",""),"source":t,"fields":[],"review_flags":[]} for t in tests}
    detached=[]
    for a in analytes:
        tid=str(a.get("test_id",""))
        formats=a.get("result_formats",[])
        fields=[]
        for f in formats:
            kinds=set(f.get("types") or [])
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
            else:kind="unknown"
            if kind=="select_or_text" and ("DoubleResultFormat" in kinds or "IntegerResultFormat" in kinds):
                kind="select_or_number"
            fields.append({"source_analyte_id":str(a["analyte_id"]),"source_format_id":str(f.get("id","")),
                "label":(str(f.get("title") or "").strip() or str(a.get("name") or "").strip()),"kind":kind,
                "types":sorted(kinds),"unit":f.get("unit") or "","options":options,
                "numeric_ranges":a.get("numeric_ranges",[]),"text_ranges":a.get("text_ranges",[]),
                "required":a.get("required"),"active":a.get("active"),
                "source_analyte":a})
        if not fields:
            fields=[{"source_analyte_id":str(a["analyte_id"]),"source_format_id":None,
                "label":a.get("name",""),"kind":"unknown","options":[],
                "unit":"","numeric_ranges":a.get("numeric_ranges",[]),"text_ranges":a.get("text_ranges",[]),
                "source_analyte":a}]
        if tid in by_test:by_test[tid]["fields"].extend(fields)
        else:detached.append({"source_test_id":tid,"analyte":a,"fields":fields})
    for test in by_test.values():
        if not test["fields"]:test["review_flags"].append("no_source_analytes")
        if any(f["kind"]=="unknown" for f in test["fields"]):test["review_flags"].append("unknown_result_format")
        if any(f["kind"]=="related" for f in test["fields"]):test["review_flags"].append("related_result_format_requires_ui_support")
        if any(f["kind"].startswith("select_or_") for f in test["fields"]):test["review_flags"].append("mixed_format_requires_combobox")
    return {"tests":list(by_test.values()),"detached_analytes":detached,
            "field_kinds":dict(Counter(f["kind"] for t in by_test.values() for f in t["fields"]))}
