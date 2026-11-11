"""Read-only NOVA order-detail Royal Lab integration gate.

No database writes or new route. Only explicit reviewed item-to-form bindings are
eligible for typed metadata. Never infer matches from a test name.
"""
from hospital.royallab_nova_order_detail_types import attach_reviewed_types

def reviewed_order_detail(conn,order_detail,bindings):
    if not isinstance(order_detail,dict) or not isinstance(bindings,dict):
        raise ValueError("Order detail and explicit reviewed bindings required")
    items=order_detail.get("items")
    if not isinstance(items,list):raise ValueError("NOVA order detail items missing")
    item_ids=[i.get("id") for i in items if isinstance(i,dict)]
    if len(item_ids)!=len(items) or any(type(x) is not int or x<=0 for x in item_ids):
        raise ValueError("Invalid NOVA order item identifiers")
    if len(set(item_ids))!=len(item_ids):raise ValueError("Duplicate NOVA order item")
    selected={}
    for item in items:
        entry=bindings.get(item["id"])
        if not isinstance(entry,dict):continue
        if entry.get("item_id")!=item["id"] or entry.get("reviewed") is not True:
            continue
        form=entry.get("form")
        if isinstance(form,dict) and form.get("source_test_id") is not None:
            selected[item["id"]]=form
    return {**order_detail,"items":attach_reviewed_types(conn,items,selected)}
