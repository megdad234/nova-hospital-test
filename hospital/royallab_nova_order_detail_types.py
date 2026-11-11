"""Read-only, fail-closed typed field metadata attachment to NOVA order detail.

Caller must provide reviewed, explicitly associated source forms for each order item.
No source form or failed review => leave original NOVA result lines untouched.
"""
from hospital.royallab_nova_typed_form_contract import reviewed_order_form
def attach_reviewed_types(conn,items,reviewed_forms):
    if not isinstance(items,list) or not isinstance(reviewed_forms,dict):
        raise ValueError("NOVA items and reviewed form map required")
    out=[]
    for item in items:
        if not isinstance(item,dict):raise ValueError("Invalid NOVA order item")
        clone={**item,"lines":[dict(line) for line in item.get("lines",[])]}
        # Require exact numeric item identity; never trust a caller-provided label.
        item_id=item.get("id")
        form=reviewed_forms.get(item_id) if type(item_id) is int else None
        if form is not None:
            try:
                typed=reviewed_order_form(conn,item_id,form)
                by_id={field["line_id"]:field for field in typed["fields"]}
                for line in clone["lines"]:
                    definition=by_id.get(line.get("id"))
                    if definition:
                        line["royal_lab_field"]={"kind":definition["kind"],
                            "options":definition["options"]}
            except (ValueError,KeyError,TypeError):
                pass  # Fail closed to original text fields, never block legacy orders.
        out.append(clone)
    return out
