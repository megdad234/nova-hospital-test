"""Verify a complete, authentic Royal Lab source bundle before building NOVA.

This is a source-integrity preflight, NOT a clinical approval or live activation.
"""
import argparse,hashlib,json,pathlib
def verify(library_path,options_path):
    lb=pathlib.Path(library_path).read_bytes()
    ob=pathlib.Path(options_path).read_bytes()
    library=json.loads(lb.decode("utf-8-sig"))
    options=json.loads(ob.decode("utf-8-sig"))
    tests=library.get("tests")
    analytes=library.get("analytes")
    if not isinstance(tests,list) or len(tests)!=367:raise ValueError("Royal Lab 367-test source missing or incomplete")
    if not isinstance(analytes,list) or len(analytes)!=1245:raise ValueError("Royal Lab 1245-analyte source missing or incomplete")
    if not isinstance(options,list) or len(options)!=2551:raise ValueError("Royal Lab 2551 unresolved options missing")
    ids=[str(t["TestID"]) for t in tests]
    if len(set(ids))!=367:raise ValueError("Duplicate Royal Lab test identifiers")
    aids=[str(a["analyte_id"]) for a in analytes]
    if len(set(aids))!=1245:raise ValueError("Duplicate Royal Lab analyte identifiers")
    return {"tests":367,"analytes":1245,"unlinked_options":2551,
            "source_sha256":hashlib.sha256(lb+b"\\0"+ob).hexdigest(),
            "clinical_approved":False,"live_bindings_created":0}
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--library",required=True)
    p.add_argument("--unlinked",required=True)
    a=p.parse_args()
    print(json.dumps(verify(a.library,a.unlinked),ensure_ascii=False))
