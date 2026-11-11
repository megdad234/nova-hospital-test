"""Guarded draft-only orchestration for Royal Lab and existing NOVA lab.

This is not an HTTP endpoint and is not activated in the hospital UI.
The caller supplies NOVA's existing lab.save_values callable and an authorized actor.
"""
from royallab_nova_line_mapping import verify_line_mapping
from royallab_nova_save_bridge import prepare_nova_save_payload

def save_reviewed_draft(conn,actor,form,entered,source_to_line,item_id,expected_version,save_values):
    if not callable(save_values):raise ValueError("NOVA save_values callable required")
    if not isinstance(actor,dict) or type(actor.get("id")) is not int or actor["id"]<=0:
        raise ValueError("Authenticated NOVA actor required")
    mapping=verify_line_mapping(conn,item_id,source_to_line)
    if not mapping["verified"] or mapping["clinical_approval"]:
        raise ValueError("Invalid draft mapping state")
    payload=prepare_nova_save_payload(form,entered,source_to_line,item_id,expected_version)
    if payload["publish"] is not False or payload["source"]!="manual":
        raise ValueError("Draft-only NOVA save required")
    return save_values(conn,actor,payload)
