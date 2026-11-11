"""Offline Royal Lab configuration importer for NOVA.
Usage: python .github/ci/royallab_import_offline.py --database COPY.db --library nova_lab_library.json --unlinked unlinked_options.json
NEVER run against a production database. Creates only royal_lab_* staging tables.
"""
import argparse,hashlib,json,pathlib,sqlite3,sys
ROOT=pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"hospital"))
from royallab_staging import stage,verify
from royallab_field_adapter import build_fields

def run(database,library_path,unlinked_path):
    db=pathlib.Path(database).resolve()
    if not db.exists():raise ValueError("Database must already exist; use a disposable copy")
    lib_bytes=pathlib.Path(library_path).read_bytes()
    opt_bytes=pathlib.Path(unlinked_path).read_bytes()
    library=json.loads(lib_bytes.decode("utf-8-sig"))
    unlinked=json.loads(opt_bytes.decode("utf-8-sig"))
    mapped=build_fields(library)
    if len(mapped["tests"])!=367:raise ValueError("Missing Royal Lab tests")
    if len(unlinked)!=2551:raise ValueError("Missing unresolved options")
    digest=hashlib.sha256(lib_bytes+b"\\0"+opt_bytes).hexdigest()
    with sqlite3.connect(db) as conn:
        batch=stage(conn,library,unlinked,digest)
        counts=verify(conn,batch)
    return {"batch_id":batch,"sha256":digest,"counts":counts,
        "detached_analytes":len(mapped["detached_analytes"]),"field_kinds":mapped["field_kinds"]}
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--database",required=True)
    p.add_argument("--library",required=True)
    p.add_argument("--unlinked",required=True)
    a=p.parse_args()
    print(json.dumps(run(a.database,a.library,a.unlinked),ensure_ascii=False,indent=2))
