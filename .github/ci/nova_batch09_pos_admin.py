# -*- coding: utf-8 -*-
"""NOVA Batch09: surgical POS grid fix, true held-cart dialog and admin bank ledger.
All changes target the EXTRACTED build tree after Batch08. Never touch live SQLite.
"""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
def change(file,fn):
    p=ROOT/file
    before=p.read_text(encoding="utf-8")
    after=fn(before)
    if after==before:raise RuntimeError("NOVA09_EMPTY_CHANGE "+file)
    p.write_text(after,encoding="utf-8")
def one(s,old,new,label):
    n=s.count(old)
    if n!=1:raise RuntimeError("NOVA09_ANCHOR "+label+" count "+str(n))
    return s.replace(old,new,1)

# The Batch05 hold bar changed the first/second-child CSS semantics. Use
# explicit panel roles in supplemental JS + CSS instead of shifting the POS.
change("pharmacy/static/nova_pharmacy_batch08.js",
       lambda s:s+"\n"+(ROOT/"pharmacy/static/nova_batch09_pos.js").read_text(encoding="utf-8"))
change("pharmacy/static/style.css",
       lambda s:s+"\n"+(ROOT/"pharmacy/static/nova_batch09_pos.css").read_text(encoding="utf-8"))

# Keep default one-owner-only hold visibility (avoid another cashier seeing an
# unfinished patient bill); preserve payment selection alongside existing items.
def held(s):
    return one(s,"'coverage':amt(p.get('coverage',0),'التغطية')}",
       "'coverage':amt(p.get('coverage',0),'التغطية'),\n"
       "             'pay_mode':p.get('pay_mode') if p.get('pay_mode') in ('cash','bank','mixed','credit') else 'cash',\n"
       "             'insurance_contract_id':p.get('insurance_contract_id') or None}",
       "held metadata")
change("pharmacy/app.py",held)

# Admin reports: read-only, admin-gated, event-driven. No backfill or schema changes.
EXTRA=Path(ROOT/"hospital/static/nova_batch09_collections.pyfrag").read_text(encoding="utf-8")
change("hospital/admin.py",lambda s:s+"\n"+EXTRA+"\n")
change("hospital/static/admin-ui.js",
       lambda s:s+"\n"+(ROOT/"hospital/static/nova_batch09_collections.js").read_text(encoding="utf-8"))
change("hospital/static/style.css",
       lambda s:s+"\n"+(ROOT/"hospital/static/nova_batch09_collections.css").read_text(encoding="utf-8"))

def gateway(s):
    needle="                if method=='GET' and path=='/api/hospital/admin/reports':"
    additional="""                if method=='GET' and path=='/api/hospital/admin/collection-detail':
                    core.require_role(role,'admin')
                    return self.reply(admin.nova_collection_details(c,parse_qs(urlparse(self.path).query)))
                if method=='GET' and path=='/api/hospital/admin/collection-export':
                    core.require_role(role,'admin')
                    return self.reply(admin.nova_collection_export(c,parse_qs(urlparse(self.path).query)))
"""
    return one(s,needle,additional+needle,"admin only collection endpoints")
change("hospital/gateway.py",gateway)
print("NOVA_BATCH09_APPLIED POS compacted; held invoice dialog; admin detailed ledgers + XLSX/PDF")
