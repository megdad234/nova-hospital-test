"""Attach only reviewed Royal Lab metadata to NOVA's existing order-detail response.

The original response is preserved unless an explicitly reviewed source binding
exists. This function never creates bindings or writes clinical records.
"""
from hospital.royallab_nova_binding_loader import load_reviewed_bindings
from hospital.royallab_nova_order_detail_gate import reviewed_order_detail
from hospital.royallab_existing_line_overlay import overlay_existing_order_lines

def overlay_order_detail(conn,detail,role):
    if role not in ('admin','lab'):return detail
    # Original NOVA result screen, direct imported Royal Lab parameter IDs.
    detail=overlay_existing_order_lines(conn,detail)
    from hospital.nova_lab_local_tests import overlay_order_detail as _local_overlay
    detail=_local_overlay(conn,detail)
    from hospital.royallab_nova_gtt_photo_reconciliation import overlay_order_detail as _gtt_overlay
    detail=_gtt_overlay(conn,detail)
    from hospital.royallab_nova_ict_malaria_reconciliation import overlay_order_detail as _ict_overlay
    detail=_ict_overlay(conn,detail)
    # Organize original TestID 8 stool fields using source-verified
    # format IDs; do not change their result inputs or archived reports.
    from hospital.royallab_nova_stool_layout import display_order_detail as _stool_display
    detail=_stool_display(conn,detail)
    if not isinstance(detail,dict) or not isinstance(detail.get('items'),list):return detail
    items=detail['items']
    if not items:return detail
    tables={r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if 'royal_lab_approved_item_bindings' not in tables:return detail
    columns={r[1] for r in conn.execute('PRAGMA table_info(royal_lab_approved_item_bindings)')}
    if not {'item_id','batch_id','reviewed','clinical_approved'}.issubset(columns):return detail
    ids=[x.get('id') for x in items if isinstance(x,dict)]
    if len(ids)!=len(items) or any(type(i) is not int or i<=0 for i in ids):return detail
    placeholders=','.join('?' for _ in ids)
    rows=conn.execute('SELECT item_id,batch_id FROM royal_lab_approved_item_bindings WHERE reviewed=1 AND clinical_approved=1 AND item_id IN ('+placeholders+')',ids).fetchall()
    by_batch={}
    for item_id,batch_id in rows:
        if type(batch_id) is int and batch_id>0:
            by_batch.setdefault(batch_id,[]).append(next(x for x in items if x['id']==item_id))
    bindings={}
    for batch_id,selected in by_batch.items():
        bindings.update(load_reviewed_bindings(conn,selected,batch_id))
    if not bindings:return detail
    return reviewed_order_detail(conn,detail,bindings)

def diagnose_royallab_visibility(conn, detail):
    """Read-only, patient-safe explanation of why typed Royal Lab fields are absent.

    Does not expose patient values, names, or result text.
    """
    if not isinstance(detail, dict) or not isinstance(detail.get("items"), list):
        return {"status": "invalid_order_detail", "items": []}
    tables={r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    required={"royal_lab_import_batches","royal_lab_source_tests",
              "royal_lab_approved_item_bindings"}
    missing=sorted(required-tables)
    if missing:
        return {"status":"source_or_bindings_not_installed",
                "missing_tables":missing,"items":[]}
    out=[]
    for item in detail["items"]:
        if not isinstance(item,dict) or type(item.get("id")) is not int:
            continue
        row=conn.execute("""SELECT reviewed,clinical_approved,batch_id
            FROM royal_lab_approved_item_bindings WHERE item_id=?
            ORDER BY clinical_approved DESC,reviewed DESC LIMIT 1""",
            (item["id"],)).fetchone()
        if row is None: reason="no_item_binding"
        elif row[0]!=1: reason="review_pending"
        elif row[1]!=1: reason="clinical_approval_pending"
        else: reason="approved_binding_present_check_field_mapping"
        out.append({"item_id":item["id"],"reason":reason})
    return {"status":"checked","items":out,"writes":False}
