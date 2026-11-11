"""Conservative Royal Lab -> NOVA test mapping proposal; never activates tests.

Exact normalized names only, unique on BOTH sides. No fuzzy medicine/clinical
equivalence is inferred. All ambiguity is surfaced for human review.
"""
import re,unicodedata

def canonical_name(value):
    if not isinstance(value,str):return ""
    text=unicodedata.normalize("NFKC",value).casefold()
    text=re.sub(r"[\u064b-\u065f\u0670]","",text)
    text=re.sub(r"[^\w]+"," ",text,flags=re.UNICODE)
    return " ".join(text.split())

def propose_test_matches(conn,source_tests):
    if not isinstance(source_tests,list):raise ValueError("Source test list required")
    rows=conn.execute("SELECT id,name FROM hospital_lab_tests").fetchall()
    by_name={}
    for tid,name in rows:
        key=canonical_name(name)
        if key:by_name.setdefault(key,[]).append(int(tid))
    source_names={}
    for test in source_tests:
        if not isinstance(test,dict):raise ValueError("Invalid source test")
        sid=str(test.get("source_test_id") or "")
        name=test.get("name")
        if not sid or not isinstance(name,str):raise ValueError("Invalid source test identity")
        key=canonical_name(name)
        if key:source_names.setdefault(key,[]).append(sid)
    proposals=[];review=[]
    for test in source_tests:
        sid=str(test["source_test_id"]);name=test["name"]
        key=canonical_name(name)
        targets=by_name.get(key,[])
        source_ids=source_names.get(key,[])
        if not key:reason="empty_name"
        elif len(source_ids)!=1:reason="duplicate_source_name"
        elif len(targets)==0:reason="no_exact_nova_name"
        elif len(targets)!=1:reason="duplicate_nova_name"
        elif test.get("review_flags"):reason="source_review_flags"
        else:reason=None
        if reason:
            review.append({"source_test_id":sid,"name":name,"reason":reason,
                           "candidate_nova_test_ids":targets})
        else:
            proposals.append({"source_test_id":sid,"nova_test_id":targets[0],
                              "name":name,"approved":False})
    return {"proposals":proposals,"review_required":review,"writes":False,
            "clinical_approval":False,"live_bindings_created":0}
