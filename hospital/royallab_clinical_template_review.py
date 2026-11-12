"""Two-person, audit-trailed review of source-incomplete NOVA laboratory forms.

Source data is immutable. Proposed clinical fields are never active until an
independent authorized reviewer records the local method and signs off. This
does not approve patient results, publish them or invent reference ranges.
"""
import hashlib
import json
import sqlite3

SCHEMA = """CREATE TABLE IF NOT EXISTS royal_lab_template_reviews (
 catalog_id INTEGER NOT NULL,
 source_test_id TEXT NOT NULL,
 revision INTEGER NOT NULL,
 state TEXT NOT NULL CHECK(state IN ('pending','approved')),
 form_json TEXT NOT NULL,
 form_hash TEXT NOT NULL,
 method TEXT NOT NULL,
 evidence TEXT NOT NULL,
 rationale TEXT NOT NULL,
 proposed_by INTEGER NOT NULL,
 approved_by INTEGER,
 proposed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 approved_at TEXT,
 PRIMARY KEY(catalog_id,source_test_id,revision),
 FOREIGN KEY(catalog_id) REFERENCES royal_lab_native_catalogs(id)
)"""

KINDS = {"text", "number", "select"}
MAX_FIELDS = 120
MAX_CHOICES = 100


def _actor(actor, *, approval=False):
    if not isinstance(actor, dict) or type(actor.get("id")) is not int or actor["id"] <= 0:
        raise PermissionError("Authenticated reviewer required")
    if actor.get("role") not in ("lab", "admin"):
        raise PermissionError("Lab staff or administrators only")
    if approval and actor.get("role") != "admin":
        raise PermissionError("Template activation requires authorized administrator")
    return actor["id"]


def _note(value, name, minimum=4, maximum=600):
    if not isinstance(value, str) or not minimum <= len(value.strip()) <= maximum:
        raise ValueError(name + " must identify the documented local laboratory method")
    return value.strip()


def _validated_form(source_form, specifications):
    if not isinstance(specifications, list) or not 1 <= len(specifications) <= MAX_FIELDS:
        raise ValueError("Reviewed template needs 1 to 120 fields")
    source_id = str(source_form["source_test_id"])
    fields = []
    seen = set()
    for number, entry in enumerate(specifications, 1):
        if not isinstance(entry, dict):
            raise ValueError("Invalid template field")
        key = entry.get("key")
        if not isinstance(key, str) or not 1 <= len(key) <= 36 or not all(
                c.isascii() and (c.isalnum() or c in "_-") for c in key):
            raise ValueError("Stable alphanumeric source field key required")
        if key in seen:
            raise ValueError("Duplicate reviewed field identity")
        seen.add(key)
        label = _note(entry.get("label"), "Field label", 2, 140)
        kind = entry.get("kind")
        if kind not in KINDS:
            raise ValueError("Only documented text, number or select fields allowed")
        unit = entry.get("unit") or ""
        if not isinstance(unit, str) or len(unit) > 40:
            raise ValueError("Invalid documented unit")
        options = entry.get("options", [])
        if not isinstance(options, list) or len(options) > MAX_CHOICES:
            raise ValueError("Invalid reviewed source choices")
        if kind == "select" and not options:
            raise ValueError("Dropdown must have documented choices")
        if kind != "select" and options:
            raise ValueError("Non-dropdown cannot contain source choices")
        safe_options = []
        option_keys = set()
        option_labels = set()
        for choice in options:
            if not isinstance(choice, dict):
                raise ValueError("Invalid reviewed dropdown choice")
            opt_key = _note(choice.get("key"), "Option identity", 1, 64)
            opt_label = _note(choice.get("label"), "Option label", 1, 140)
            if opt_key in option_keys or opt_label.casefold() in option_labels:
                raise ValueError("Duplicate source dropdown choices")
            option_keys.add(opt_key)
            option_labels.add(opt_label.casefold())
            safe_options.append({
                "id": "REVIEW-" + source_id + "-" + key + "-" + opt_key,
                "label": opt_label, "active": True, "order": len(safe_options) + 1,
            })
        # No normality or clinical reference range is fabricated here.
        fields.append({
            "source_analyte_id": "REVIEW-" + source_id + "-" + key,
            "source_format_id": "REVIEW-" + source_id + "-" + key,
            "label": label, "kind": kind, "types": ["ManualReviewedFormat"],
            "unit": unit, "options": safe_options, "numeric_ranges": [],
            "text_ranges": [], "required": bool(entry.get("required", False)),
            "active": True, "manual_clinically_reviewed": True,
        })
    return {
        "source_test_id": source_id, "name": source_form["name"],
        "source_department_id": source_form.get("source_department_id"),
        "fields": fields, "review_flags": [],
        "clinical_template_provenance": "reviewed_local_lab_method",
        "original_source_fields_preserved": True,
        "clinical_approval": False,
    }


def _source(conn, catalog_id, test_id):
    from hospital.royallab_native_catalog_store import (
        test_form, effective_source_form, is_non_lab_service)
    from hospital.royallab_native_result_drafts import validate_source_form
    original = test_form(conn, catalog_id, test_id)
    if is_non_lab_service(original):
        raise ValueError("Non-laboratory service is not a clinical result test")
    form = effective_source_form(original)
    try:
        validate_source_form(form)
    except ValueError:
        return original
    raise ValueError("Original source test already has a complete writable form")


def _freeze(conn, catalog_id, source_id):
    # Do not silently change existing patient draft field meanings or options.
    table = conn.execute("""SELECT 1 FROM sqlite_master
            WHERE type='table' AND name='royal_lab_native_result_drafts'""").fetchone()
    if table and conn.execute("""SELECT 1 FROM royal_lab_native_result_drafts
           WHERE catalog_id=? AND source_test_id=? LIMIT 1""", (catalog_id,source_id)).fetchone():
        raise ValueError("Historical result drafts exist: template replacement needs migration review")


def propose(conn, actor, catalog_id, source_test_id, specifications, *, method, evidence, rationale):
    preparer = _actor(actor)
    if type(catalog_id) is not int or catalog_id <= 0:
        raise ValueError("Invalid source catalog")
    source_test_id = str(source_test_id)
    original = _source(conn, catalog_id, source_test_id)
    _freeze(conn, catalog_id, source_test_id)
    form = _validated_form(original, specifications)
    from hospital.royallab_native_result_drafts import validate_source_form
    validate_source_form(form)
    method = _note(method, "Assay method", 4, 300)
    evidence = _note(evidence, "Manufacturer or laboratory protocol", 8, 600)
    rationale = _note(rationale, "Review rationale", 8, 600)
    canonical = json.dumps(form, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    conn.execute(SCHEMA)
    with conn:
        number = conn.execute("""SELECT COALESCE(MAX(revision),0)+1
              FROM royal_lab_template_reviews WHERE catalog_id=? AND source_test_id=?""",
              (catalog_id,source_test_id)).fetchone()[0]
        conn.execute("""INSERT INTO royal_lab_template_reviews
             (catalog_id,source_test_id,revision,state,form_json,form_hash,
              method,evidence,rationale,proposed_by)
             VALUES (?,?,?,'pending',?,?,?,?,?,?)""",
             (catalog_id,source_test_id,number,canonical,digest,method,evidence,rationale,preparer))
    return {"source_test_id":source_test_id,"revision":number,"state":"pending",
            "form_hash":digest,"patient_entry_enabled":False}


def approve(conn, actor, catalog_id, source_test_id, revision, expected_hash, *, attestation):
    reviewer = _actor(actor, approval=True)
    if type(revision) is not int or revision <= 0:
        raise ValueError("Invalid revision")
    source_test_id = str(source_test_id)
    _source(conn,catalog_id,source_test_id)
    _freeze(conn,catalog_id,source_test_id)
    _note(attestation,"Clinical method and unit attestation",12,800)
    conn.execute(SCHEMA)
    with conn:
        row = conn.execute("""SELECT proposed_by,state,form_hash,form_json FROM
             royal_lab_template_reviews WHERE catalog_id=? AND source_test_id=? AND revision=?""",
             (catalog_id,source_test_id,revision)).fetchone()
        if not row:
            raise KeyError("Unknown clinical review revision")
        if row[0] == reviewer:
            raise PermissionError("Clinical form requires an independent second reviewer")
        if row[1] != "pending" or row[2] != expected_hash:
            raise ValueError("Review changed or already activated")
        canonical = json.dumps(json.loads(row[3]),ensure_ascii=False,sort_keys=True,separators=(",", ":"))
        if hashlib.sha256(canonical.encode("utf-8")).hexdigest() != row[2]:
            raise ValueError("Review form hash has changed")
        from hospital.royallab_native_result_drafts import validate_source_form
        validate_source_form(json.loads(row[3]))
        conn.execute("""UPDATE royal_lab_template_reviews SET state='approved',
          approved_by=?,approved_at=CURRENT_TIMESTAMP,rationale=rationale || ?
          WHERE catalog_id=? AND source_test_id=? AND revision=? AND state='pending'""",
          (reviewer, "\nSigned review: " + attestation.strip(),
           catalog_id,source_test_id,revision))
    return {"source_test_id":source_test_id,"revision":revision,
            "state":"approved","patient_entry_enabled":True,"clinical_approval":False}


def active_reviewed_form(conn, catalog_id, source_test_id, effective_form):
    """Replace only with a separately signed-off exact-source-ID form."""
    if not conn.execute("""SELECT 1 FROM sqlite_master WHERE type='table'
            AND name='royal_lab_template_reviews'""").fetchone():
        return effective_form
    row = conn.execute("""SELECT revision,form_json,form_hash,method,evidence
          FROM royal_lab_template_reviews
          WHERE catalog_id=? AND source_test_id=? AND state='approved'
          ORDER BY revision DESC LIMIT 1""", (catalog_id,str(source_test_id))).fetchone()
    if not row:
        return effective_form
    form = json.loads(row[1])
    canonical = json.dumps(form,ensure_ascii=False,sort_keys=True,separators=(",", ":"))
    if hashlib.sha256(canonical.encode("utf-8")).hexdigest() != row[2]:
        raise ValueError("Signed clinical template was modified")
    return {**form,"clinical_template_revision":row[0],
            "clinical_review_method":row[3],
            "clinical_review_evidence":row[4]}


def review_history(conn,catalog_id,source_test_id):
    if not conn.execute("""SELECT 1 FROM sqlite_master WHERE type='table'
            AND name='royal_lab_template_reviews'""").fetchone():
        return []
    rows = conn.execute("""SELECT revision,state,form_hash,method,evidence,rationale,
          proposed_by,approved_by,proposed_at,approved_at FROM royal_lab_template_reviews
          WHERE catalog_id=? AND source_test_id=? ORDER BY revision""",
          (catalog_id,str(source_test_id))).fetchall()
    keys = ("revision","state","form_hash","method","evidence","rationale",
            "proposed_by","approved_by","proposed_at","approved_at")
    return [dict(zip(keys,row)) for row in rows]


def review_details(conn,catalog_id,source_test_id,revision):
    """Read the COMPLETE proposed clinical form before any second-person signoff."""
    if type(revision) is not int or revision <= 0:
        raise ValueError("Invalid review revision")
    if not conn.execute("""SELECT 1 FROM sqlite_master WHERE type='table'
            AND name='royal_lab_template_reviews'""").fetchone():
        raise KeyError("Clinical review proposal is not found")
    row=conn.execute("""SELECT state,form_json,form_hash,method,evidence,rationale,
          proposed_by,approved_by FROM royal_lab_template_reviews
          WHERE catalog_id=? AND source_test_id=? AND revision=?""",
          (catalog_id,str(source_test_id),revision)).fetchone()
    if not row:
        raise KeyError("Clinical review proposal is not found")
    canonical=json.dumps(json.loads(row[1]),ensure_ascii=False,sort_keys=True,separators=(",",":"))
    if hashlib.sha256(canonical.encode("utf-8")).hexdigest()!=row[2]:
        raise ValueError("Proposed clinical form was modified outside review")
    return {"source_test_id":str(source_test_id),"revision":revision,
            "state":row[0],"form":json.loads(row[1]),"form_hash":row[2],
            "method":row[3],"evidence":row[4],"rationale":row[5],
            "proposed_by":row[6],"approved_by":row[7],
            "can_publish_patient_results":False}


def review_suggestion(conn,catalog_id,source_test_id):
    """Prefill only source-proven fields or explicitly UNAPPROVED candidates.

    No patient data, kit-dependent invented answer choices or reference ranges.
    Staff must complete method, evidence and two-person signoff separately.
    """
    from hospital.royallab_native_catalog_store import effective_source_form
    from hospital.royallab_missing_test_review_templates import CANDIDATE_FIELDS
    original = _source(conn,catalog_id,str(source_test_id))
    source_id = str(source_test_id)
    form = effective_source_form(original)
    source_fields = form.get("fields") or []
    proposal = []
    warnings = []
    inactive=(False,0,"False","false","0")
    if source_fields:
        for field in source_fields:
            source_inactive = field.get("active") in inactive
            if source_inactive:
                # An inactive field MAY be proposed for independent review,
                # but its original inactive status must never be overwritten
                # or treated as permission to enter patient results.
                warnings.append("Original source field inactive; confirm current assay before approval: " +
                                str(field.get("label") or "Unnamed source field"))
            kind = field.get("kind")
            label = str(field.get("label") or "").strip()
            if not label:
                warnings.append("Unnamed original source field needs a verified label")
                continue
            if kind not in KINDS:
                warnings.append("Mixed or unsupported source field requires method-specific input review: " + label)
                continue
            choices = []
            if kind == "select":
                options = [o for o in field.get("options",[]) if isinstance(o,dict)
                           and o.get("active") not in inactive]
                labels = [str(o.get("label") or "").strip() for o in options]
                if not labels or any(not x for x in labels) or len(set(x.casefold() for x in labels))!=len(labels):
                    warnings.append("Missing or ambiguous dropdown: " + label)
                    continue
                choices = labels
            proposal.append({"key":"f"+str(len(proposal)+1),
                             "label":label, "kind":kind,
                             "unit":str(field.get("unit") or ""), "option_labels":choices,
                             "evidence_source_format_id":field.get("source_format_id"),
                             "source_was_inactive":source_inactive,
                             "source_proven":bool(field.get("types")) and
                                not field.get("manual_untyped_draft_only") and
                                not field.get("manual_missing_closed_options_draft_only")})
    else:
        for label,kind in CANDIDATE_FIELDS.get(source_id, []):
            proposal.append({"key":"f"+str(len(proposal)+1),
                             "label":label, "kind":kind, "unit":"",
                             "option_labels":[], "source_proven":False})
    if not proposal:
        warnings.append("No unambiguous template fields exist; obtain actual method and kit protocol")
    if len(proposal)>MAX_FIELDS:
        raise ValueError("More than 120 potential source fields requires laboratory review")
    return {"source_test_id":source_id,"source_test_name":original["name"],
            "fields":proposal,"warnings":warnings,
            "ready_for_patient_results":False,
            "needs_method_documentation":True,
            "requires_independent_approval":True,
            "source_archive_unchanged":True}
