"""Smoke test REAL pinned Royal Lab data in disposable SQLite, never patient DB."""
import json,pathlib,sqlite3,sys
ROOT=pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from hospital.royallab_native_catalog_store import install_file,list_tests,test_form
from hospital.royallab_field_adapter import build_fields
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
  if not count:raise RuntimeError('Real Royal Lab forms contain no fields')
 return {'source_test_count':len(tests),'field_count':count,
         'kinds':kinds,'live_patient_results_written':False,
         'installed_windows_dropdowns_verified':False}
if __name__=='__main__':print(json.dumps(run(),ensure_ascii=False,indent=2))
