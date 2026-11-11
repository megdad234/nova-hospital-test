"""Compose strict source-format resolution with NOVA's existing draft saver.

Caller must supply the authorized NOVA lab.save_values function. No new endpoint.
"""
from royallab_nova_order_line_resolver import resolve_order_lines
from royallab_nova_draft_service import save_reviewed_draft

def save_resolved_review_draft(conn,actor,form,entered,item_id,expected_version,save_values):
    if not isinstance(form,dict) or not isinstance(form.get("fields"),list):
        raise ValueError("Reviewed Royal Lab form required")
    resolution=resolve_order_lines(conn,item_id,form["fields"])
    if not resolution["ready"] or len(resolution["source_to_line"])!=len(form["fields"]):
        raise ValueError("Every source field must map to an active NOVA result line")
    return save_reviewed_draft(conn,actor,form,entered,resolution["source_to_line"],
                               item_id,expected_version,save_values)
