# -*- coding:utf-8 -*-
"""Update prior acceptance checks only where user explicitly changed cashier policy.
Keeps the original authorization assertions and adds checks for new price approval.
"""
from pathlib import Path
p=Path(__file__).resolve().parents[2]/'tests/test_finance_workflow.py'
s=p.read_text(encoding='utf-8')
def swap(a,b,count=1):
 global s
 n=s.count(a)
 if n!=count:raise RuntimeError('NOVA05_TEST_EXPECTATION_ANCHOR '+repr(a[:90])+' '+str(n))
 s=s.replace(a,b)
swap("        self.expect_status(cashier,'get','/api/hospital/patients')",
     "        self.assertIsInstance(cashier.get('/api/hospital/patients'),list)")
swap("""        self.expect_status(rec,'get','/api/hospital/patients')
        self.expect_status(rec,'post','/api/hospital/patients',{'full_name':'No'})""",
     """        self.assertIsInstance(rec.get('/api/hospital/patients'),list)
        self.assertTrue(rec.post('/api/hospital/patients',{'full_name':'Synthetic Cashier Direct'})['patient_no'])""")
swap("""        self.assertEqual(cashier.post('/api/hospital/invoice-insurance-release',{'invoice_id':zero['id']})['status'],'settled')""",
     """        self.expect_status(cashier,'post','/api/hospital/invoice-insurance-release',{'invoice_id':zero['id']},400)
        self.admin.post('/api/hospital/nova-free-approval',{'service_key':free['key'],'approved':True})
        self.assertEqual(cashier.post('/api/hospital/invoice-insurance-release',{'invoice_id':zero['id']})['status'],'settled')""")
p.write_text(s,encoding='utf-8')
print('NOVA05_FINANCE_EXPECTATIONS_UPDATED')
