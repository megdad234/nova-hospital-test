"""User-defined NOVA lab tests: review-controlled and independent of Royal Lab source.

The original 367 Royal Lab rows are immutable. Local tests live in the existing
NOVA laboratory test/parameter tables with an explicit NOVA-LOCAL identity.
Changes to a test with recorded orders are refused; copy it to a new version
instead of changing historical clinical definitions. No patient rows are read
or copied outside the local NOVA database.
"""
import hashlib
import json
import re
import sqlite3
from decimal import Decimal, InvalidOperation

SCHEMA = """
CREATE TABLE IF NOT EXISTS nova_lab_local_tests (
 id INTEGER PRIMARY KEY,
 nova_test_id INTEGER UNIQUE,
 code TEXT NOT NULL UNIQUE,
 section TEXT NOT NULL DEFAULT '',
 approved_revision INTEGER NOT NULL DEFAULT 0,
 approved_form_json TEXT,
 approved_form_hash TEXT,
 approved_by INTEGER,
 updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS nova_lab_local_proposals (
 id INTEGER PRIMARY KEY,
 local_id INTEGER,
 state TEXT NOT NULL DEFAULT 'pending'
     CHECK(state IN ('pending','approved','rejected')),
 proposed_by INTEGER NOT NULL,
 proposed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 approved_by INTEGER,
 reviewed_at TEXT,
 name TEXT NOT NULL,
 price TEXT NOT NULL,
 section TEXT NOT NULL,
 form_json TEXT NOT NULL,
 form_hash TEXT NOT NULL,
 method TEXT NOT NULL,
 evidence TEXT NOT NULL,
 rationale TEXT NOT NULL,
 attestation TEXT,
 FOREIGN KEY(local_id) REFERENCES nova_lab_local_tests(id)
);
CREATE INDEX IF NOT EXISTS idx_nova_local_proposals
 ON nova_lab_local_proposals(local_id,state);
CREATE TABLE IF NOT EXISTS nova_lab_local_fields (
 nova_parameter_id INTEGER PRIMARY KEY,
 local_id INTEGER NOT NULL,
 key TEXT NOT NULL,
 kind TEXT NOT NULL,
 options_json TEXT NOT NULL,
 reference_json TEXT NOT NULL,
 approved_revision INTEGER NOT NULL,
 UNIQUE(local_id,key),
 FOREIGN KEY(local_id) REFERENCES nova_lab_local_tests(id)
);
"""
KINDS = {"text", "number", "select"}
CODE_PREFIX = "NOVA-LOCAL-"
PARAM_PREFIX = "NLOCAL_"

# This is an unapproved transcription of the Al Sharq Hospital laboratory paper
# GTT-with-urine-glucose form supplied by the user, NOT a Royal Lab source assay.
# The pictured chart contains fasting, 1-hour, 2-hour blood and urine glucose.
# No assay-specific glucose load, pregnancy protocol, reference interval,
# diagnosis thresholds, laboratory method or hospital price were provided.
# A separate administrator must confirm those details before activation.
GTT_URINE_NAME = "Glucose Tolerance Test (GTT) with Urine Glucose"
GTT_URINE_TEMPLATE_ID = "gtt-urine-0-1-2h"
GTT_URINE_OPTIONS = ["Negative", "Trace", "+1", "+2", "+3", "+4"]


def gtt_urine_template():
    """Prefill the existing NOVA local-test editor, never create a live test.

    Patient name, sex, age, date, doctor and file number come from NOVA's
    existing patient/order records; they are intentionally not duplicated.
    """
    fields = [
        {"key": "glucose_load", "label": "Glucose Load",
         "kind": "number", "unit": "g"},
        {"key": "specimen", "label": "Specimen",
         "kind": "select", "options": ["Plasma", "Serum"]},
        {"key": "method_recorded", "label": "Method",
         "kind": "text", "unit": ""},
    ]
    for time_key, display in (
        ("fasting", "Fasting (0 hour)"),
        ("one_hour", "1 Hour"),
        ("two_hours", "2 Hours"),
    ):
        fields.append({"key": "blood_" + time_key,
                       "label": display + " - Blood Glucose",
                       "kind": "number", "unit": "mg/dL"})
        fields.append({"key": "urine_" + time_key,
                       "label": display + " - Urine Glucose",
                       "kind": "select", "options": list(GTT_URINE_OPTIONS),
                       "unit": ""})
    fields.extend([
        {"key": "interpretation", "label": "Interpretation",
         "kind": "text", "unit": ""},
        {"key": "comments", "label": "Comments",
         "kind": "text", "unit": ""},
    ])
    normalized = _fields(fields)
    return {
        "template_id": GTT_URINE_TEMPLATE_ID,
        "name": GTT_URINE_NAME,
        "section": "Chemistry",
        "price": None,  # never invent a charge in Sudanese pounds
        "fields": normalized,
        "method": "",
        "evidence": "",
        "rationale": "Transcribed from the photographed Al Sharq Hospital laboratory GTT with urine glucose form.",
        "state": "suggestion_only",
        "ready_for_patient_results": False,
        "reference_ranges_verified": False,
        "clinical_warning": (
            "Confirm glucose load, assay method, patient-specific protocol, "
            "lab charge and reference/interpretation criteria independently; "
            "the photograph does not certify clinical thresholds."
        ),
    }



def init(conn):
    if not isinstance(conn, sqlite3.Connection):
        raise TypeError("SQLite NOVA connection required")
    # sqlite3.executescript() silently commits an existing NOVA transaction.
    # Each schema statement is DDL with IF NOT EXISTS, so execute it without
    # crossing the caller's transaction boundary.
    for statement in SCHEMA.split(";"):
        if statement.strip():
            conn.execute(statement)


def _actor(actor, admin=False):
    if not isinstance(actor, dict) or type(actor.get("id")) is not int or actor["id"] <= 0:
        raise PermissionError("Authenticated laboratory operator required")
    if actor.get("role") not in ("lab", "admin"):
        raise PermissionError("Laboratory permission required")
    if admin and actor.get("role") != "admin":
        raise PermissionError("Independent administrator required")
    return actor["id"]


def _text(value, title, lo=1, hi=240):
    if not isinstance(value, str) or not lo <= len(value.strip()) <= hi:
        raise ValueError("Invalid " + title)
    return value.strip()


def _money(value):
    try:
        number = Decimal(str(value))
    except (ValueError, InvalidOperation, TypeError):
        raise ValueError("Valid test price required") from None
    if not number.is_finite() or not Decimal("0") < number <= Decimal("1000000000000"):
        raise ValueError("Test must have an explicit positive price")
    if number != number.to_integral_value():
        raise ValueError("NOVA lab prices must be whole Sudanese pounds")
    return str(int(number))


def _fields(raw):
    if not isinstance(raw, list) or not 1 <= len(raw) <= 120:
        raise ValueError("Test needs 1-120 result fields")
    output = []
    keys = set()
    for entry in raw:
        if not isinstance(entry, dict):
            raise ValueError("Invalid field definition")
        key = _text(entry.get("key"), "field key", 1, 24)
        if not re.fullmatch(r"[a-z][a-z0-9_]*", key):
            raise ValueError("Field key must be stable Latin letters/digits")
        if key in keys:
            raise ValueError("Duplicate result field key")
        keys.add(key)
        label = _text(entry.get("label"), "result field name", 2, 140)
        kind = entry.get("kind")
        if kind not in KINDS:
            raise ValueError("Unknown result field type")
        unit = entry.get("unit", "")
        if not isinstance(unit, str) or len(unit.strip()) > 40:
            raise ValueError("Invalid result unit")
        options = entry.get("options", [])
        if not isinstance(options, list) or len(options) > 100:
            raise ValueError("Invalid selectable options")
        labels = [_text(option, "select option", 1, 120) for option in options]
        if len({s.casefold() for s in labels}) != len(labels):
            raise ValueError("Duplicate select labels")
        if kind == "select" and not labels:
            raise ValueError("Dropdown requires documented choices")
        if kind != "select" and labels:
            raise ValueError("Only dropdowns may contain choices")
        reference = entry.get("reference", "")
        reference_source = entry.get("reference_source", "")
        if not isinstance(reference, str) or len(reference.strip()) > 500:
            raise ValueError("Invalid reference text")
        if not isinstance(reference_source, str) or len(reference_source.strip()) > 500:
            raise ValueError("Invalid reference evidence")
        if reference.strip() and len(reference_source.strip()) < 8:
            raise ValueError("Reference interval requires method-specific source evidence")
        output.append({"key": key, "label": label, "kind": kind,
                       "unit": unit.strip(), "options": labels,
                       "reference": reference.strip(),
                       "reference_source": reference_source.strip(),
                       "required": entry.get("required") is True})
    return output


def _has_orders(conn, nova_test_id):
    if not nova_test_id:
        return False
    exists = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='hospital_order_items'").fetchone()
    return bool(exists and conn.execute(
        "SELECT 1 FROM hospital_order_items WHERE test_id=? LIMIT 1", (nova_test_id,)).fetchone())


def _hash(data):
    return hashlib.sha256(json.dumps(data, ensure_ascii=False,
                         sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def propose(conn, actor, *, local_id=None, name, section, price, fields,
            method, evidence, rationale):
    user = _actor(actor)
    init(conn)
    if local_id is not None and (type(local_id) is not int or local_id <= 0):
        raise ValueError("Invalid local test identifier")
    if local_id:
        row = conn.execute("SELECT nova_test_id FROM nova_lab_local_tests WHERE id=?",
                           (local_id,)).fetchone()
        if row is None:
            raise KeyError("NOVA local test not found")
        if _has_orders(conn, row[0]):
            raise ValueError("This test has historical orders; create a new test version instead")
    name = _text(name, "test name", 2, 160)
    section = _text(section, "test section", 2, 100)
    # The new GTT template is a named local assay, distinct from Royal Lab's
    # Blood Sugar Curve; reject repeat submissions of the same exact GTT form.
    # This does not apply to other user-defined test families.
    if local_id is None and name.casefold() == GTT_URINE_NAME.casefold():
        # The real Royal Lab G.T.T TestID 240 has now been reconciled to the
        # photographed worksheet. Do not sell a duplicate second GTT form.
        installed = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE name='royal_lab_nova_gtt_photo_provenance'"
        ).fetchone()
        if installed and conn.execute(
            "SELECT 1 FROM hospital_lab_tests WHERE code='ROYAL-240' AND active=1"
        ).fetchone():
            raise ValueError("G.T.T already exists with the reviewed blood/urine worksheet")
        existing = conn.execute("""SELECT 1 FROM hospital_lab_tests
            WHERE LOWER(TRIM(name))=LOWER(TRIM(?)) LIMIT 1""", (name,)).fetchone()
        proposed = conn.execute("""SELECT 1 FROM nova_lab_local_proposals
            WHERE state='pending' AND LOWER(TRIM(name))=LOWER(TRIM(?))
            LIMIT 1""", (name,)).fetchone()
        if existing or proposed:
            raise ValueError("GTT with urine glucose already exists or awaits independent review")
    price = _money(price)
    data = _fields(fields)
    method = _text(method, "laboratory method", 4, 300)
    evidence = _text(evidence, "manufacturer / protocol evidence", 8, 600)
    rationale = _text(rationale, "review rationale", 8, 600)
    payload = {"fields": data}
    digest = _hash(payload)
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    with conn:
        cur = conn.execute("""INSERT INTO nova_lab_local_proposals
          (local_id,proposed_by,name,price,section,form_json,form_hash,method,evidence,rationale)
          VALUES (?,?,?,?,?,?,?,?,?,?)""",
          (local_id,user,name,price,section,serialized,digest,method,evidence,rationale))
    return {"proposal_id": cur.lastrowid, "state": "pending",
            "form_hash": digest, "test_active": False if not local_id else None}


def _columns(conn, table):
    return {x[1] for x in conn.execute("PRAGMA table_info(" + table + ")")}


def _sync_approved(conn, local_id, nova_test_id, code, name, price, section, form, revision):
    tests = _columns(conn, "hospital_lab_tests")
    params = _columns(conn, "hospital_lab_parameters")
    if not {"id", "code", "name", "price", "active"}.issubset(tests):
        raise RuntimeError("NOVA lab tests schema incompatible with local test management")
    if not {"id", "test_id", "code", "name", "unit", "active"}.issubset(params):
        raise RuntimeError("NOVA lab parameter schema incompatible")
    if nova_test_id is None:
        cols = ["code","name","price","active"]
        vals = [code,name,int(price),1]
        if "category" in tests:
            cols.append("category")
            vals.append(section)
        cur = conn.execute("INSERT INTO hospital_lab_tests (" +
                           ",".join(cols)+") VALUES ("+",".join("?" for _ in vals)+")",vals)
        nova_test_id = cur.lastrowid
    else:
        existing = conn.execute("SELECT code FROM hospital_lab_tests WHERE id=?",
                                (nova_test_id,)).fetchone()
        if not existing or existing[0] != code:
            raise RuntimeError("Local test identity changed")
        fields = ["name=?","price=?","active=1"]
        values = [name,int(price)]
        if "category" in tests:
            fields.append("category=?")
            values.append(section)
        conn.execute("UPDATE hospital_lab_tests SET "+",".join(fields)+" WHERE id=?",
                     (*values,nova_test_id))
    keys = set()
    for order,field in enumerate(form["fields"]):
        param_code = PARAM_PREFIX + str(local_id) + "_" + field["key"]
        keys.add(param_code)
        row = conn.execute("""SELECT id FROM hospital_lab_parameters
            WHERE test_id=? AND code=?""", (nova_test_id,param_code)).fetchone()
        # Populate original NOVA result reference and order columns when present.
        # Never infer a reference range: this is signed local evidence only.
        extras = {}
        if "reference_all" in params:
            extras["reference_all"] = field["reference"]
        if "sort_order" in params:
            extras["sort_order"] = order
        if row:
            parameter_id = row[0]
            assignment = ["name=?","unit=?","active=1"] + [k+"=?" for k in extras]
            conn.execute("UPDATE hospital_lab_parameters SET "+",".join(assignment)+" WHERE id=?",
                         (field["label"],field["unit"],*extras.values(),parameter_id))
        else:
            cols = ["test_id","code","name","unit","active"] + list(extras)
            vals = [nova_test_id,param_code,field["label"],field["unit"],1] + list(extras.values())
            cur = conn.execute("INSERT INTO hospital_lab_parameters (" +
                       ",".join(cols)+") VALUES ("+",".join("?" for _ in vals)+")",vals)
            parameter_id = cur.lastrowid
        conn.execute("""INSERT INTO nova_lab_local_fields(
            nova_parameter_id,local_id,key,kind,options_json,reference_json,approved_revision)
            VALUES (?,?,?,?,?,?,?)
            ON CONFLICT(nova_parameter_id) DO UPDATE SET
            kind=excluded.kind,options_json=excluded.options_json,
            reference_json=excluded.reference_json,approved_revision=excluded.approved_revision""",
            (parameter_id,local_id,field["key"],field["kind"],
             json.dumps(field["options"],ensure_ascii=False),
             json.dumps({"reference":field["reference"],
                         "source":field["reference_source"]},ensure_ascii=False),revision))
    for old_id,old_code in conn.execute(
        "SELECT id,code FROM hospital_lab_parameters WHERE test_id=? AND code LIKE ?",
        (nova_test_id, PARAM_PREFIX+str(local_id)+"_%")).fetchall():
        if old_code not in keys:
            conn.execute("UPDATE hospital_lab_parameters SET active=0 WHERE id=?",(old_id,))
            conn.execute("DELETE FROM nova_lab_local_fields WHERE nova_parameter_id=?",(old_id,))
    return nova_test_id


def approve(conn, actor, proposal_id, form_hash, *, attestation):
    reviewer = _actor(actor, admin=True)
    if type(proposal_id) is not int or proposal_id <= 0:
        raise ValueError("Invalid review proposal")
    attestation = _text(attestation, "independent assay attestation", 12, 800)
    init(conn)
    conn.execute("SAVEPOINT nova_local_approve")
    try:
        row = conn.execute("""SELECT id,local_id,state,proposed_by,name,price,section,
                    form_json,form_hash FROM nova_lab_local_proposals WHERE id=?""",
                           (proposal_id,)).fetchone()
        if not row:
            raise KeyError("Missing lab proposal")
        _,local_id,state,author,name,price,section,payload,stored_hash = row
        if state != "pending" or stored_hash != form_hash:
            raise ValueError("Proposal already reviewed or changed")
        if author == reviewer:
            raise PermissionError("Clinical template requires a different reviewer")
        form = json.loads(payload)
        if _hash(form) != stored_hash or _fields(form.get("fields")) != form.get("fields"):
            raise ValueError("Proposed form content changed")
        if local_id:
            old = conn.execute("""SELECT nova_test_id,code,approved_revision FROM
                        nova_lab_local_tests WHERE id=?""",(local_id,)).fetchone()
            if not old:
                raise KeyError("Missing local catalogue entry")
            nova_test_id,code,last_revision = old
            if _has_orders(conn,nova_test_id):
                raise ValueError("Existing orders freeze the result template")
        else:
            code = CODE_PREFIX + str(proposal_id)
            cur = conn.execute("INSERT INTO nova_lab_local_tests(code) VALUES(?)", (code,))
            local_id = cur.lastrowid
            nova_test_id = None
            last_revision = 0
        if not name or not section:
            raise ValueError("Incomplete clinical form name or department")
        version = last_revision+1
        nova_test_id = _sync_approved(conn,local_id,nova_test_id,code,name,price,section,form,version)
        conn.execute("""UPDATE nova_lab_local_tests SET nova_test_id=?,approved_revision=?,
                    section=?,approved_form_json=?,approved_form_hash=?,approved_by=?,
                    updated_at=CURRENT_TIMESTAMP WHERE id=?""",
                    (nova_test_id,version,section,payload,stored_hash,reviewer,local_id))
        conn.execute("""UPDATE nova_lab_local_proposals SET state='approved',
                    approved_by=?,reviewed_at=CURRENT_TIMESTAMP,attestation=?
                    WHERE id=? AND state='pending'""",(reviewer,attestation,proposal_id))
        conn.execute("RELEASE nova_local_approve")
    except Exception:
        conn.execute("ROLLBACK TO nova_local_approve")
        conn.execute("RELEASE nova_local_approve")
        raise
    return {"state":"approved","local_id":local_id,"nova_test_id":nova_test_id,
            "revision":version,"code":code,"patient_results_approved":False}


def list_local(conn):
    init(conn)
    entries = conn.execute("""SELECT l.id,l.nova_test_id,l.code,l.approved_revision,
               t.name,t.price,t.active,l.approved_form_hash,l.section
               FROM nova_lab_local_tests l JOIN hospital_lab_tests t ON t.id=l.nova_test_id
               ORDER BY t.name""").fetchall()
    return [{"local_id":r[0],"nova_test_id":r[1],"code":r[2],
             "revision":r[3],"name":r[4],"price":r[5],"active":bool(r[6]),
             "form_hash":r[7],"section":r[8],"has_orders":_has_orders(conn,r[1])} for r in entries]


def local_form(conn, local_id):
    init(conn)
    if type(local_id) is not int or local_id <= 0:
        raise ValueError("Invalid NOVA local test")
    row = conn.execute("""SELECT l.id,l.nova_test_id,l.approved_revision,
        l.approved_form_json,l.approved_form_hash,t.name,t.price,l.section
        FROM nova_lab_local_tests l JOIN hospital_lab_tests t ON l.nova_test_id=t.id
        WHERE l.id=?""", (local_id,)).fetchone()
    if not row:
        raise KeyError("Unknown NOVA local test")
    form = json.loads(row[3])
    if _hash(form) != row[4]:
        raise ValueError("Approved local form was modified")
    return {"local_id":row[0],"nova_test_id":row[1],"revision":row[2],
            "name":row[5],"price":row[6],"section":row[7], "fields":form["fields"],
            "has_orders":_has_orders(conn,row[1])}


def proposals(conn):
    init(conn)
    rows = conn.execute("""SELECT id,local_id,state,proposed_by,name,price,section,
                      form_json,form_hash,method,evidence,rationale
                      FROM nova_lab_local_proposals ORDER BY id DESC LIMIT 150""").fetchall()
    return [{"proposal_id":r[0],"local_id":r[1],"state":r[2],"proposed_by":r[3],
             "name":r[4],"price":r[5],"section":r[6],"fields":json.loads(r[7])["fields"],
             "form_hash":r[8],"method":r[9],"evidence":r[10],"rationale":r[11]}
             for r in rows]


def restore_active(conn):
    """Only reenable approved LOCAL tests following Royal Lab catalogue refresh.

    Never reenable legacy NOVA test rows and never change original Royal tests.
    This must run *after* source catalogue's legacy deactivation and integrity gate.
    """
    if "nova_lab_local_tests" not in {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}:
        return 0
    rows = conn.execute("""SELECT l.nova_test_id,l.code,l.section FROM nova_lab_local_tests l
        WHERE l.approved_revision>0 AND l.nova_test_id IS NOT NULL""").fetchall()
    supports_category = "category" in _columns(conn,"hospital_lab_tests")
    count = 0
    for test_id,code,section in rows:
        actual = conn.execute("SELECT code FROM hospital_lab_tests WHERE id=?",(test_id,)).fetchone()
        if not actual or actual[0]!=code or not code.startswith(CODE_PREFIX):
            raise RuntimeError("Local test identity drift; refusing unexpected activation")
        # Backfill ONLY legacy Other/blank local-test categories. Preserve
        # administrator edits and never classify or alter the Royal catalogue.
        if supports_category and section:
            conn.execute("""UPDATE hospital_lab_tests SET active=1,
                    category=CASE
                      WHEN LOWER(TRIM(COALESCE(category,''))) IN ('','other')
                      THEN ? ELSE category END WHERE id=?""",(section,test_id))
        else:
            conn.execute("UPDATE hospital_lab_tests SET active=1 WHERE id=?",(test_id,))
        count+=1
    return count


def overlay_order_detail(conn, detail):
    """Enrich NOVA's original existing result lines with local types/options."""
    if not isinstance(detail,dict) or not isinstance(detail.get("items"),list):
        return detail
    if "nova_lab_local_fields" not in {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}:
        return detail
    result = {**detail, "items":[]}
    for original in detail["items"]:
        clone={**original,"lines":[dict(x) for x in original.get("lines",[])]}
        item_id=original.get("id")
        if type(item_id) is not int:
            result["items"].append(clone)
            continue
        test=conn.execute("""SELECT t.code FROM hospital_order_items i
           JOIN hospital_lab_tests t ON t.id=i.test_id WHERE i.id=?""",(item_id,)).fetchone()
        if not test or not str(test[0]).startswith(CODE_PREFIX):
            result["items"].append(clone)
            continue
        for line in clone["lines"]:
            param_id=line.get("parameter_id")
            if type(param_id) is not int:
                code=line.get("code")
                if not isinstance(code,str) or not code.startswith(PARAM_PREFIX):
                    continue
                rr=conn.execute("""SELECT p.id FROM hospital_lab_parameters p
                    JOIN hospital_order_items i ON i.test_id=p.test_id
                    WHERE i.id=? AND p.code=?""",(item_id,code)).fetchall()
                if len(rr)!=1:continue
                param_id=rr[0][0]
            row=conn.execute("""SELECT f.kind,f.options_json,f.reference_json
                FROM nova_lab_local_fields f
                JOIN hospital_lab_parameters p ON p.id=f.nova_parameter_id
                JOIN hospital_order_items i ON i.test_id=p.test_id
                WHERE i.id=? AND p.id=? AND p.active=1""",(item_id,param_id)).fetchone()
            if not row:continue
            opts=json.loads(row[1]);reference=json.loads(row[2])
            line["royal_lab_field"]={"kind":row[0],"options":opts,
                                    "reference":reference.get("reference","")}
        result["items"].append(clone)
    return result


def validate_save_payload(conn, data):
    """Server-side validation before the original paid-order save function.

    Does not alter original payment, approval, version or publish semantics.
    """
    if not isinstance(data,dict) or type(data.get("item_id")) is not int:
        return
    if "nova_lab_local_fields" not in {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}:
        return
    item_id=data["item_id"]
    row=conn.execute("""SELECT t.code FROM hospital_order_items i
          JOIN hospital_lab_tests t ON t.id=i.test_id WHERE i.id=?""",(item_id,)).fetchone()
    if not row or not str(row[0]).startswith(CODE_PREFIX):
        return
    values=data.get("values")
    if not isinstance(values,list):
        raise ValueError("Local test results require structured line values")
    for value in values:
        if not isinstance(value,dict) or type(value.get("line_id")) is not int:
            raise ValueError("Invalid local test result line")
        line=conn.execute("""SELECT l.code FROM hospital_lab_lines l
                  WHERE l.id=? AND l.item_id=?""",(value["line_id"],item_id)).fetchone()
        if not line:
            raise ValueError("Result line does not belong to this NOVA order")
        param_id=None
        if param_id is None:
            q=conn.execute("""SELECT p.id FROM hospital_lab_parameters p
                      JOIN hospital_order_items i ON i.test_id=p.test_id
                      WHERE i.id=? AND p.code=?""",(item_id,line[0])).fetchall()
            if len(q)!=1:
                raise ValueError("Local test result mapping is incomplete")
            param_id=q[0][0]
        meta=conn.execute("""SELECT kind,options_json FROM nova_lab_local_fields
                     WHERE nova_parameter_id=?""",(param_id,)).fetchone()
        if meta is None:
            raise ValueError("Unreviewed local test result field")
        v=value.get("value")
        if v is None or v=="":
            continue
        if not isinstance(v,str) or len(v)>4000:
            raise ValueError("Invalid local result value")
        if meta[0]=="select" and v not in json.loads(meta[1]):
            raise ValueError("Result is not a documented dropdown choice")
        if meta[0]=="number":
            try:
                n=Decimal(v.strip())
            except (ValueError,InvalidOperation):
                raise ValueError("Numeric result required") from None
            if not n.is_finite():
                raise ValueError("Finite numeric result required")
