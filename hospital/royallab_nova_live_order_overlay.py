"""Attach only reviewed Royal Lab metadata to NOVA's existing order-detail response.

The original response is preserved unless an explicitly reviewed source binding
exists. This function never creates bindings or writes clinical records.
"""
from royallab_nova_binding_loader import load_reviewed_bindings
from royallab_nova_order_detail_gate import reviewed_order_detail

def overlay_order_detail(conn,detail,role):
    if role not in ('admin','lab'):return detail
    if not isinstance(detail,dict) or not isinstance(detail.get('items'),list):return detail
    items=detail['items']
    if not items:return detail
    tables={r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if 'royal_lab_approved_item_bindings' not in tables:return detail
    columns={r[1] for r in conn.execute('PRAGMA table_info(royal_lab_approved_item_bindings)')}
    if not {'item_id','batch_id','reviewed'}.issubset(columns):return detail
    ids=[x.get('id') for x in items if isinstance(x,dict)]
    if len(ids)!=len(items) or any(type(i) is not int or i<=0 for i in ids):return detail
    placeholders=','.join('?' for _ in ids)
    rows=conn.execute('SELECT item_id,batch_id FROM royal_lab_approved_item_bindings WHERE reviewed=1 AND item_id IN ('+placeholders+')',ids).fetchall()
    by_batch={}
    for item_id,batch_id in rows:
        if type(batch_id) is int and batch_id>0:
            by_batch.setdefault(batch_id,[]).append(next(x for x in items if x['id']==item_id))
    bindings={}
    for batch_id,selected in by_batch.items():
        bindings.update(load_reviewed_bindings(conn,selected,batch_id))
    if not bindings:return detail
    return reviewed_order_detail(conn,detail,bindings)
