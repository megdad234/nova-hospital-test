"""Smoke test REAL pinned Royal Lab data in disposable SQLite, never patient DB."""
import json,pathlib,sqlite3,sys
ROOT=pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from hospital.royallab_native_catalog_store import install_file,list_tests,test_form
from hospital.royallab_field_adapter import build_fields
from hospital.royallab_native_result_drafts import save_draft,load_draft
from hospital.royallab_replacement_readiness import verify_replacement_catalog
from hospital.royallab_existing_catalog_replacement import replace_catalog
def run(root=ROOT):
 root=pathlib.Path(root)
 path=root/'hospital/royallab_source/nova_lab_library.json'
 lib=json.loads(path.read_text(encoding='utf-8-sig'))
 mapped=build_fields(lib)
 with sqlite3.connect(':memory:') as db:
  cid=install_file(db,path)
  tests=list_tests(db,cid)
  if len(tests)!=367:raise RuntimeError('Real Royal Lab catalog import incomplete')
  readiness=verify_replacement_catalog(db)
  db.execute("CREATE TABLE hospital_lab_tests(id INTEGER PRIMARY KEY,code TEXT UNIQUE,name TEXT,active INTEGER DEFAULT 1)")
  db.execute("CREATE TABLE hospital_lab_parameters(id INTEGER PRIMARY KEY,test_id INTEGER,code TEXT,name TEXT,unit TEXT)")
  db.execute("INSERT INTO hospital_lab_tests(code,name) VALUES('OLD-NOVA','Legacy')")
  replacement=replace_catalog(db,lib,approved=True)
  if replacement['active_royal_lab_tests']!=367:
   raise RuntimeError("Royal Lab NOVA table replacement incomplete")
  if db.execute("SELECT active FROM hospital_lab_tests WHERE code='OLD-NOVA'").fetchone()[0]!=0:
   raise RuntimeError("Old NOVA test still active")
  metadata_count=db.execute("SELECT COUNT(*) FROM royal_lab_nova_parameter_metadata").fetchone()[0]
  if metadata_count<1000:
   raise RuntimeError("Royal Lab original parameter metadata incomplete")
  replace_catalog(db,lib,approved=True)
  if db.execute("SELECT COUNT(*) FROM hospital_lab_tests WHERE code LIKE 'ROYAL-%'").fetchone()[0]!=367:
   raise RuntimeError("Royal Lab NOVA table replacement is not idempotent")
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
         'real_catalog_dropdown_draft_roundtrip':exercised,
         'replacement_readiness':readiness,
         'synthetic_nova_table_replacement':True,
         'nova_parameter_metadata_count':metadata_count}
if __name__=='__main__':print(json.dumps(run(),ensure_ascii=False,indent=2))
