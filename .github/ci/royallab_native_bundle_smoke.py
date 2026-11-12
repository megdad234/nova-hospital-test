"""Smoke test REAL pinned Royal Lab data in disposable SQLite, never patient DB."""
import json,pathlib,sqlite3,sys
ROOT=pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from hospital.royallab_native_catalog_store import install_file,list_tests,test_form
from hospital.royallab_field_adapter import build_fields
from hospital.royallab_native_result_drafts import save_draft,load_draft
def run(root=ROOT):
 root=pathlib.Path(root)
 path=root/'hospital/royallab_source/nova_lab_library.json'
 lib=json.loads(path.read_text(encoding='utf-8-sig'))
 mapped=build_fields(lib)
 with sqlite3.connect(':memory:') as db:
  cid=install_file(db,path)
  tests=list_tests(db,cid)
  if len(tests)!=367:raise RuntimeError('Real Royal Lab catalog import incomplete')
  count=0;kinds={}
  for t in tests:
   form=test_form(db,cid,t['source_test_id'])
   for f in form['fields']:
    count+=1;kinds[f['kind']]=kinds.get(f['kind'],0)+1
  if count<1000:raise RuntimeError('Real Royal Lab source has too few fields')
  if kinds.get('select',0)+kinds.get('select_or_text',0)+kinds.get('select_or_number',0)<1:raise RuntimeError('Real Royal Lab dropdowns missing')
  exercised=False
  for t in tests:
   form=test_form(db,cid,t['source_test_id'])
   for field in form['fields']:
    if field['kind']!='select' or field.get('source_format_id') is None:continue
    active=[o for o in field.get('options',[]) if o.get('active') not in (False,0,'False','false','0')]
    if not active:continue
    fid=field['source_format_id']
    value=str(active[0]['id'])
    save_draft(db,'SYNTHETIC-ORDER',t['source_test_id'],{fid:value})
    reopened=load_draft(db,'SYNTHETIC-ORDER',t['source_test_id'])
    if reopened is None or reopened['values'].get(fid)!=value:
     raise RuntimeError('Real Royal Lab dropdown save/reopen failed')
    exercised=True
    break
   if exercised:break
  if not exercised:raise RuntimeError('No real Royal Lab active dropdown available for draft smoke test')
 return {'source_test_count':len(tests),'field_count':count,
         'kinds':kinds,'live_patient_results_written':False,
         'installed_windows_dropdowns_verified':False,
         'real_catalog_dropdown_draft_roundtrip':exercised}
if __name__=='__main__':print(json.dumps(run(),ensure_ascii=False,indent=2))
