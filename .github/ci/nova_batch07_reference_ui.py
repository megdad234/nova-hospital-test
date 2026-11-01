#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NOVA: bank-reference mandatory indicator + Arabic warning only.

This patch deliberately leaves the server validation and financial logic unchanged.
Runs after NOVA batch06; any upstream drift must fail the build.
"""
from pathlib import Path

def replace_once(path, old, new):
    p = Path(path)
    text = p.read_text(encoding='utf-8')
    hits = text.count(old)
    if hits != 1:
        raise RuntimeError(f'{path}: expected one anchor, found {hits}: {old[:85]!r}')
    p.write_text(text.replace(old, new, 1), encoding='utf-8')

finance = 'hospital/static/finance-ui.js'
replace_once(finance,
"""    document.querySelectorAll('input[name="payment_method"]').forEach(i=>i.onchange=update);
    $('pay-cash').oninput=update;$('pay-bank').oninput=update;""",
"""    // Reflect the selected bank's EXISTING server-side require_reference policy.
    const novaReferenceIndicator=()=>{
      const selectedBank=financeState.banks.find(b=>b.id===Number($('pay-bank-id').value||0));
      const required=mode()!=='cash'&&Number($('pay-bank').value||0)>0&&Boolean(selectedBank?.require_reference);
      const wrap=$('pay-ref-wrap'),field=wrap?.querySelector('input[name="bank_reference"]');
      if(!wrap||!field)return;
      let star=wrap.querySelector('.nova-required-ref');
      if(!star){star=document.createElement('span');star.className='nova-required-ref';
        star.textContent=' *';star.style.color='#b42318';star.style.fontWeight='700';
        wrap.insertBefore(star,field);}
      star.hidden=!required;
      field.setAttribute('aria-required',required?'true':'false');
    };
    const novaReferenceUpdate=()=>{update();novaReferenceIndicator();};
    document.querySelectorAll('input[name="payment_method"]').forEach(i=>i.onchange=novaReferenceUpdate);
    $('pay-cash').oninput=novaReferenceUpdate;$('pay-bank').oninput=novaReferenceUpdate;
    $('pay-bank-id').onchange=novaReferenceUpdate;
    novaReferenceUpdate();""")
replace_once(finance,
"""    form('new-payment-form',async f=>{
      const key='nova-'+""",
"""    form('new-payment-form',async f=>{
      const selectedBank=financeState.banks.find(b=>b.id===Number(f.get('bank_id')||0));
      if(Number(f.get('bank_amount')||0)>0&&selectedBank?.require_reference&&!String(f.get('bank_reference')||'').trim()){
        notice('رقم العملية البنكية إلزامي لهذا البنك. أدخل الرقم قبل حفظ التحصيل.',true);
        $('pay-ref-wrap')?.querySelector('input[name="bank_reference"]')?.focus();
        return;
      }
      const key='nova-'+""")

admin = 'hospital/static/admin-ui.js'
replace_once(admin,
"""function admPaymentFields(){const formEl=$('adm-settle-form');if(!formEl)return;const mode=$('adm-pay-method').value;const cash=$('adm-cash-wrap'),bank=$('adm-bank-wrap'),ref=$('adm-ref-wrap');cash.hidden=mode!=='mixed';bank.hidden=mode==='cash';ref.hidden=mode==='cash';}""",
"""function admPaymentFields(){
 const formEl=$('adm-settle-form');if(!formEl)return;
 const mode=$('adm-pay-method').value,cash=$('adm-cash-wrap'),bank=$('adm-bank-wrap'),ref=$('adm-ref-wrap');
 cash.hidden=mode!=='mixed';bank.hidden=mode==='cash';ref.hidden=mode==='cash';
 const selectedBank=adminState.banks.find(b=>b.id===Number(formEl.querySelector('[name="bank_id"]')?.value||0));
 const amount=Number(formEl.querySelector('[name="amount"]')?.value||0);
 const cashAmount=Number(formEl.querySelector('[name="cash_amount"]')?.value||0);
 const required=Boolean(selectedBank?.require_reference)&&(mode==='bank'||(mode==='mixed'&&amount>cashAmount));
 const field=ref.querySelector('input[name="bank_reference"]');
 if(!field)return;
 let star=ref.querySelector('.nova-required-ref');
 if(!star){star=document.createElement('span');star.className='nova-required-ref';
   star.textContent=' *';star.style.color='#b42318';star.style.fontWeight='700';
   ref.insertBefore(star,field);}
 star.hidden=!required;
 field.setAttribute('aria-required',required?'true':'false');
}""")
replace_once(admin,
"""   $('adm-pay-method').addEventListener('change',admPaymentFields);admPaymentFields();""",
"""   insurance.addEventListener('change',admPaymentFields);
   insurance.addEventListener('input',admPaymentFields);
   admPaymentFields();""")
replace_once(admin,
"""     if(!Number.isSafeInteger(cash)||cash<0||cash>raw)throw Error('المبلغ النقدي غير صحيح');
     const company=""",
"""     if(!Number.isSafeInteger(cash)||cash<0||cash>raw)throw Error('المبلغ النقدي غير صحيح');
     const selectedBank=adminState.banks.find(b=>b.id===Number(values.get('bank_id')||0));
     if(raw-cash>0&&selectedBank?.require_reference&&!String(values.get('bank_reference')||'').trim()){
       notice('رقم العملية البنكية إلزامي لهذا البنك. أدخل الرقم قبل تسجيل التسوية.',true);
       insurance.querySelector('input[name="bank_reference"]')?.focus();
       return;
     }
     const company=""")

# Intentional guardrails: UI wording only; no changes to account policies,
# bank reference formats, server checks, finance schema, or previously recorded data.
print('NOVA bank-reference asterisk and Arabic warning patch applied.')
