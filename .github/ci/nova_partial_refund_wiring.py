"""Wire NOVA partial refunds with isolated API and invoice detail; no cashier UI changes."""
from pathlib import Path
p=Path('hospital/gateway.py');s=p.read_text(encoding='utf-8')
a="if path=='/api/hospital/invoice-refund':"
assert s.count(a)==1
if "if path=='/api/hospital/invoice-partial-refund':" not in s:
 s=s.replace(a,"if path=='/api/hospital/invoice-partial-refund':\n                        core.require_role(role,'admin');return self.reply(finance.partial_refund_invoice(c,user,data))\n                    "+a,1)
p.write_text(s,encoding='utf-8')
p=Path('hospital/finance.py');s=p.read_text(encoding='utf-8')
# initialize ledger at startup using existing finance schema creation, rather than on first refund
# table created by partial-refund function when first used; invoice queries guard table existence.
needle="    out['net_paid']=out['paid']-out['refunded']"
assert s.count(needle)==1
extra="""    if pharmacy.one(c,"SELECT name FROM sqlite_master WHERE type='table' AND name='nova_partial_refunds'"):
        partial=pharmacy.query(c,'''SELECT refund_no,cash_amount,bank_amount,bank_name,bank_reference,note,created_at
                                   FROM nova_partial_refunds WHERE invoice_id=? ORDER BY id''',(iid,))
        out['refunds']+=partial
        out['refunded']+=sum(x['cash_amount']+x['bank_amount'] for x in partial)
"""
if "out['refunds']+=partial" not in s:s=s.replace(needle,extra+needle,1)
# Preserve original paid, net paid; do not convert partial refunds into debt.
p.write_text(s,encoding='utf-8')
print('NOVA_PARTIAL_REFUND_API_AND_DETAIL_ADDED')
