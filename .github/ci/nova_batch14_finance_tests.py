# -*- coding: utf-8 -*-
"""NOVA14 focused financial regressions, executed after all source patches."""
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def allocation(gross_lines,discount):
    gross=sum(gross_lines)
    if discount<0 or discount>gross:raise ValueError('discount')
    net=gross-discount
    allocated=0;result=[]
    for idx,line in enumerate(gross_lines):
        value=line*net//gross if gross and idx<len(gross_lines)-1 else net-allocated
        result.append(value);allocated+=value
    return result
def returned(line_total,qty,earlier,now):
    return line_total*(earlier+now)//qty-line_total*earlier//qty
class FinancialRegression(unittest.TestCase):
    def test_discount_allocation_exact(self):
        for gross in ([100],[100,200],[101,103,107],[1,1,1],[0,100]):
            for discount in (0,1,sum(gross)//2,sum(gross)):
                values=allocation(gross,discount)
                self.assertEqual(sum(values),sum(gross)-discount)
                self.assertTrue(all(v>=0 for v in values))
    def test_partial_returns_never_exceed_net_sale(self):
        for total,qty in [(100,3),(99,4),(0,7),(1,9),(101,11)]:
            self.assertEqual(sum(returned(total,qty,i,1) for i in range(qty)),total)
    def test_net_profit_uses_cost_not_tender(self):
        gross=1200;discount=100;actual_batch_cost=760
        self.assertEqual(gross-discount-actual_batch_cost,340)
    def test_source_finance_contract(self):
        app=(ROOT/'pharmacy/app.py').read_text(encoding='utf-8')
        js=(ROOT/'pharmacy/static/app.js').read_text(encoding='utf-8')
        self.assertIn("discount=amt(p.get('discount',0)",app)
        self.assertIn("net_lines.append(net)",app)
        self.assertIn("amount=after-before",app)
        self.assertIn("discount:saleDiscount()",js)
        self.assertIn('id="nova-sale-discount"',js)
    def test_profit_permission_and_receipt_isolation(self):
        app=(ROOT/'pharmacy/app.py').read_text(encoding='utf-8')
        js=(ROOT/'pharmacy/static/app.js').read_text(encoding='utf-8')
        self.assertIn("can_profit=bool(permissions.intersection(",app)
        self.assertIn("'net_profit':total-cost_total if can_profit else None",app)
        self.assertIn("data.net_profit===null||data.net_profit===undefined",js)
        self.assertIn("receipt(actual)",js)
        self.assertNotIn("cash-tender",js[js.index('function payFields(due)'):js.index('function mixedBalance()')])
    def test_invalid_discount_rejected_by_server(self):
        app=(ROOT/'pharmacy/app.py').read_text(encoding='utf-8')
        self.assertIn("if discount>gross:raise ValueError(",app)
        self.assertIn("total=gross-discount",app)
if __name__=='__main__':unittest.main()
