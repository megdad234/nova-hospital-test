"""Strict, side-effect-free bridge to NOVA's existing lab.save_values contract.

Caller must supply reviewed source-format -> existing hospital_lab_lines ID mapping.
No schema changes, no writes, no bypass of payment/version/publish checks.
"""
from royallab_result_preview import validate_preview

def prepare_nova_save_payload(form,entered,source_to_line,item_id,expected_version):
    if not isinstance(source_to_line,dict):raise ValueError("Reviewed line mapping required")
    checked=validate_preview(form,entered)
    if not checked["all_valid"]:raise ValueError("Unresolved or invalid Royal Lab results")
    if not isinstance(item_id,int) or item_id<=0:raise ValueError("Invalid NOVA order item")
    if not isinstance(expected_version,int) or expected_version<0:raise ValueError("Invalid result version")
    if not set(entered).issubset(source_to_line):raise ValueError("Missing reviewed NOVA line mapping")
    line_ids=list(source_to_line.values())
    if any(not isinstance(x,int) or x<=0 for x in line_ids) or len(set(line_ids))!=len(line_ids):
        raise ValueError("Ambiguous NOVA line mapping")
    values=[]
    for source_id in entered:
        entry=checked["results"][source_id]
        if entry["status"]=="empty":value=""
        elif entry["status"].startswith("valid"):value=str(entry["value"])
        else:raise ValueError("Unreviewed field")
        if len(value)>4000:raise ValueError("NOVA result value too long")
        values.append({"line_id":source_to_line[source_id],"value":value})
    return {"item_id":item_id,"expected_version":expected_version,
            "values":values,"publish":False,"source":"manual",
            "reason":"Royal Lab reviewed field mapping — draft only"}
