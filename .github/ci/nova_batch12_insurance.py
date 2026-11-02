# -*- coding: utf-8 -*-
"""NOVA Batch12: pharmacy beneficiary card to unified hospital patient.
Applies AFTER Batch11, on EXTRACTED source only. Never alters a live database.
"""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]

def edit(path,transform):
    p=ROOT/path
    src=p.read_text(encoding='utf-8')
    dst=transform(src)
    if src==dst:raise RuntimeError('NOVA12_NO_CHANGE '+path)
    p.write_text(dst,encoding='utf-8')
def one(src,old,new,label):
    count=src.count(old)
    if count!=1:raise RuntimeError('NOVA12_ANCHOR '+label+': '+str(count))
    return src.replace(old,new,1)

addon=(ROOT/'.github/ci/nova_batch12_insurance_backend.pyfrag').read_text(encoding='utf-8')
def patch_backend(s):
    # Server always verifies the beneficiary contract, identity, patient file,
    # and coverage before the original sale writes stock or journal entries.
    source="""    checked=[]
    rx_needed=False
    for x in rows:"""
    validation="""    nova_insured_schema(c)
    insured_member=None
    if contract_id or p.get('insurance_sale') is True:
        if not contract:raise ValueError('بيع التأمين يتطلب اختيار عقد فعّال')
        if not partner_id:raise ValueError('حدد المستفيد التأميني أولاً')
        selected=p.get('insurance_member_id')
        if not selected:raise ValueError('اختر بطاقة المستفيد التأميني')
        insured_member=one(c,'SELECT * FROM insurance_members WHERE id=? AND contract_id=? AND partner_id=? AND active=1',
            (posint(selected,'المستفيد'),contract['id'],partner_id))
        if not insured_member:raise ValueError('المستفيد غير مسجل في العقد أو غير فعّال')
        if p.get('insurance_verified') is not True:
            raise ValueError('يلزم التحقق من البطاقة وأهلية العلاج قبل البيع')
        card=one(c,'SELECT patient_id FROM nova_pharmacy_insured_cards WHERE member_id=? AND contract_id=?',
                 (insured_member['id'],contract['id']))
        if not card:raise ValueError('المستفيد ليس له بطاقة مرتبطة بملف المريض')
        expected=insured_member['coverage_override'] if insured_member['coverage_override'] is not None else contract['coverage_default']
        if coverage!=expected:raise ValueError('نسبة التأمين تختلف عن العقد، أعد اختيار البطاقة')
    checked=[]
    rx_needed=False
    for x in rows:"""
    s=one(s,source,validation,'server sale validation')
    s=one(s,
      "        if prescription:\n            c.execute('INSERT INTO sale_prescriptions",
      "        if insured_member:\n            nova_insured_sale_snapshot(c,insured_member,contract,uid,coverage,saleid)\n        if prescription:\n            c.execute('INSERT INTO sale_prescriptions",
      'atomic sale card snapshot')
    # Sales list supplies stable card snapshot, even if insurance membership
    # subsequently changes. Never rewrite historical sales.
    s=one(s,
      "def sales(c):\n    r=query(c,",
      "def sales(c):\n    nova_insured_schema(c)\n    r=query(c,",
      'sales schema')
    s=one(s,
      "    for s in r:\n        s['lines']=query(c,",
      "    for s in r:\n        s['insurance_details']=one(c,'SELECT patient_name,patient_no,card_no,insurer_name,coverage FROM nova_pharmacy_insured_sales WHERE sale_id=?',(s['id'],))\n        s['lines']=query(c,",
      'sale snapshot read')
    # All three GET endpoints are role-gated. No patient list is returned in
    # normal POS load, searches require an intentional staff query.
    s=one(s,
      "'/api/v1/insurance':'claims',",
      "'/api/v1/nova-insured-search':'sale','/api/v1/nova-hospital-patient-search':'sale','/api/v1/nova-insurance-monthly-detail':'claims','/api/v1/insurance':'claims',",
      'GET permission')
    s=one(s,
      "'/api/v1/insurance':lambda:insurance_list(c),",
      """'/api/v1/nova-insured-search':lambda:nova_insured_search(c,(parse_qs(urlparse(self.path).query).get('contract_id') or [''])[0],(parse_qs(urlparse(self.path).query).get('q') or [''])[0]),
                     '/api/v1/nova-hospital-patient-search':lambda:nova_patient_search(c,(parse_qs(urlparse(self.path).query).get('q') or [''])[0]),
                     '/api/v1/nova-insurance-monthly-detail':lambda:nova_insurance_monthly_detail(c,(parse_qs(urlparse(self.path).query).get('authority_id') or [''])[0],(parse_qs(urlparse(self.path).query).get('period') or [''])[0]),
                     '/api/v1/insurance':lambda:insurance_list(c),""",
      'GET result')
    s=one(s,
      "'/api/v1/insurance-member':('claims',lambda:insurance_member_create(c,data,u['id'])),",
      """'/api/v1/nova-insured-enroll':('sale',lambda:nova_insured_enroll(c,data,u['id'])),
                     '/api/v1/insurance-member':('claims',lambda:insurance_member_create(c,data,u['id'])),""",
      'POST enrollment')
    if 'NOVA_BATCH12_INSURED_PATIENT' in s:raise RuntimeError('Batch12 already present')
    return s+'\n# NOVA_BATCH12_INSURED_PATIENT\n'+addon+'\n'

edit('pharmacy/app.py',patch_backend)

def patch_pos(s):
    s=one(s,"insurance_contract_id:state.insuranceContractId||null,payments",
      "insurance_contract_id:state.insuranceContractId||null,insurance_sale:!!state.authorityId,insurance_member_id:state.novaInsuredMember?.member_id||null,insurance_verified:state.novaInsuranceVerified===true,payments",
      'attach selected member to sale request')
    return s
edit('pharmacy/static/app.js',patch_pos)

def patch_ui(s):
    return s+'\n/* NOVA_BATCH12_INSURANCE_UI */\n'+(ROOT/'pharmacy/static/nova_batch12_insurance.js').read_text(encoding='utf-8')+'\n'
edit('pharmacy/static/nova_pharmacy_batch08.js',patch_ui)
def patch_css(s):
    return s+'\n'+(ROOT/'pharmacy/static/nova_batch12_insurance.css').read_text(encoding='utf-8')+'\n'
edit('pharmacy/static/style.css',patch_css)
print('NOVA_BATCH12_APPLIED: insured member/card, hospital patient link, sale snapshot, monthly claims')
