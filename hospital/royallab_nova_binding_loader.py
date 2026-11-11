"""Fail-closed reviewed Royal Lab form bindings from isolated staging.

No automatic approval, no guessing by test name. A separate signed/approved
mapping table must exist before any form is exposed.
"""
import json
from royallab_catalog_preview import test_form

def load_reviewed_bindings(conn,items,batch_id):
    """Return explicit reviewed bindings only; missing table means legacy UI."""
    if type(batch_id) is not int or batch_id<=0:return {}
    tables={r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if 'royal_lab_approved_item_bindings' not in tables:return {}
    out={}
    for item in items:
        if not isinstance(item,dict) or type(item.get('id')) is not int:continue
        row=conn.execute("""SELECT source_test_id,reviewed,source_test_code
            FROM royal_lab_approved_item_bindings
            WHERE item_id=? AND batch_id=?""",(item['id'],batch_id)).fetchone()
        if not row or row[1]!=1:continue
        if not isinstance(row[2],str) or not row[2].strip():continue
        try:
            form=test_form(conn,batch_id,row[0])
            if form.get('review_flags'):continue
            out[item['id']]={'item_id':item['id'],'reviewed':True,'form':form}
        except (ValueError,KeyError,TypeError,json.JSONDecodeError):
            continue
    return out
