"""Fail-closed Royal Lab source-form loader for explicitly reviewed NOVA items.

Never infers a mapping from a name, does not grant clinical approval, and
requires the saved NOVA test identity to match the bound item.
"""
import json
from hospital.royallab_catalog_preview import test_form

def load_reviewed_bindings(conn,items,batch_id):
    if type(batch_id) is not int or batch_id<=0:return {}
    tables={r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if 'royal_lab_approved_item_bindings' not in tables:return {}
    required={'item_id','batch_id','nova_test_id','source_test_id','reviewed','reviewed_by','reviewed_at'}
    columns={r[1] for r in conn.execute('PRAGMA table_info(royal_lab_approved_item_bindings)')}
    if not required.issubset(columns):return {}
    out={}
    for item in items:
        if not isinstance(item,dict) or type(item.get('id')) is not int:continue
        row=conn.execute("""SELECT b.source_test_id,b.reviewed,b.nova_test_id,
                                   b.reviewed_by,b.reviewed_at,i.test_id
            FROM royal_lab_approved_item_bindings b
            JOIN hospital_order_items i ON i.id=b.item_id
            WHERE b.item_id=? AND b.batch_id=?""",(item['id'],batch_id)).fetchone()
        if not row or row[1]!=1 or type(row[2]) is not int or row[2]!=row[5]:continue
        if not row[3] or not row[4] or str(row[0]).strip()=='':continue
        if item.get('test_id') is not None and item['test_id']!=row[2]:continue
        try:
            form=test_form(conn,batch_id,row[0])
            if form.get('review_flags') or str(form.get('source_test_id'))!=str(row[0]):continue
            out[item['id']]={'item_id':item['id'],'reviewed':True,'form':form}
        except (ValueError,KeyError,TypeError,json.JSONDecodeError):
            continue
    return out
