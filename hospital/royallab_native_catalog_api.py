"""Read-only native Royal Lab catalogue endpoints for NOVA integration.

No matching to obsolete NOVA test names; source TestID is the only identity.
The API exposes the original reference ranges and option IDs verbatim.
"""
import json,sqlite3,re
from hospital.royallab_native_catalog_store import list_tests,clinical_test_form
from hospital.royallab_native_result_form import validate_result_values
from hospital.royallab_native_form_html import render_form

def _visible_name(value):
 return re.sub(r'\bROYAL[\s_-]*\d+\b','',str(value),flags=re.I).strip()

def _public_form(form):
 # Keep source IDs for exact order/result binding, but strip legacy codes from labels.
 public={**form,'name':_visible_name(form.get('name',''))}
 public['fields']=[]
 for field in form.get('fields',[]):
  clean={**field,'label':_visible_name(field.get('label',''))}
  clean['options']=[{**option,'label':_visible_name(option.get('label',''))}
                    for option in field.get('options',[])]
  public['fields'].append(clean)
 return public

def current_catalog_id(conn):
 if not conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='royal_lab_native_catalogs'").fetchone():
  raise LookupError("Royal Lab original catalog has not been installed")
 row=conn.execute("SELECT id FROM royal_lab_native_catalogs ORDER BY id DESC LIMIT 1").fetchone()
 if not row:raise LookupError("Royal Lab original catalog has not been installed")
 return row[0]

def catalog_response(conn,search="",limit=500):
 if not isinstance(search,str):raise ValueError("Search must be text")
 if not isinstance(limit,int) or not 1<=limit<=500:raise ValueError("Invalid limit")
 cid=current_catalog_id(conn)
 # Show the whole source catalogue while identifying forms that are genuinely
 # writable. Never present billing-only or incomplete source rows as ready tests.
 from hospital.royallab_native_result_drafts import validate_source_form
 items=[]
 for source in list_tests(conn,cid):
  form=clinical_test_form(conn,cid,source["source_test_id"])
  try:
   validate_source_form(form)
   is_ready=True
  except ValueError:
   is_ready=False
  items.append({**source,"name":_visible_name(source["name"]),"result_entry_ready":is_ready})
 if search.strip():
  q=search.strip().casefold()
  items=[t for t in items if q in t["name"].casefold()]
 return {"catalog_id":cid,"source":"RoyalLabDB.bak","total":len(items),
         "ready_for_result_entry":sum(bool(x["result_entry_ready"]) for x in items),
         "tests":items[:limit]}

def form_response(conn,source_test_id):
 cid=current_catalog_id(conn)
 form=_public_form(clinical_test_form(conn,cid,source_test_id))
 return {"catalog_id":cid,"source":"RoyalLabDB.bak","test":form,"form_html":render_form(form)}

def validate_response(conn,source_test_id,values):
 form=form_response(conn,source_test_id)["test"]
 if form.get("review_flags") or not form.get("fields"):
  raise ValueError("Source laboratory test requires review before validating results")
 return {"source_test_id":form["source_test_id"],"validated_values":validate_result_values(form,values)}
