# -*- coding: utf-8 -*-
"""NOVA Batch11: one thermal print engine for PHARMACY + HOSPITAL.

Runs after Batch10. No database or finance mutation. Keeps A4 purchase invoices,
full hospital invoices, laboratory results and admin reports on legacy printers.
"""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
engine=(ROOT/'.github/ci/nova_unified_thermal_engine.js').read_text(encoding='utf-8')
if 'function novaUnifiedThermalPrint(' not in engine:
    raise RuntimeError('NOVA11 shared thermal source missing')

def add(name,addition,marker):
    p=ROOT/name
    original=p.read_text(encoding='utf-8')
    if marker not in original or 'NOVA_BATCH11_UNIFIED' in original:
        raise RuntimeError('NOVA11 source drift '+name)
    p.write_text(original+'\n/* NOVA_BATCH11_UNIFIED */\n'+addition,encoding='utf-8')

# We do not modify the historical pharmacy receipt builder at all.
# Only its print transport switches from global window.print/A4 page inheritance
# to an isolated document. Purchase slips & reports keep their original flow.
pharmacy=r"""
printReceipt=async function(){
  const printable=document.getElementById('printable');
  if(!printable){toast('لا توجد فاتورة قابلة للطباعة',true);return}
  let paper=window.MADAR_PRINT_PAPER||'thermal80';
  const bridge=typeof nativeBridge==='function'?nativeBridge():null;
  if(bridge){
    try{
      const devices=await bridge.get_devices();
      paper=devices?.settings?.paper||paper;
    }catch(e){/* preserve user printer selection, default 80mm */}
  }
  if(printable.classList.contains('thermal-receipt')&&paper!=='a4'){
    novaUnifiedThermalPrint(printable.outerHTML,paper);
    return;
  }
  // A4 supplier purchase invoice or deliberately chosen A4 sales copy:
  // retain existing print behavior, no global changes to purchase/finance.
  document.body.classList.remove('paper-thermal80','paper-thermal58','paper-a4');
  document.body.classList.add('paper-'+(paper==='a4'?'a4':'thermal80'),'printing-receipt');
  let cleaned=false;
  const clean=()=>{
    if(cleaned)return;cleaned=true;
    document.body.classList.remove('printing-receipt','paper-thermal80','paper-thermal58','paper-a4');
  };
  window.addEventListener('afterprint',clean,{once:true});
  window.print();setTimeout(clean,120000);
};
"""
# Batch08/09 reuses this script at the end; no script tag or MIME changes.
add('pharmacy/static/nova_pharmacy_batch08.js',engine+'\n'+pharmacy,'novaPurchaseSuggestedPrice')

# Keep hospital payment selection (including older partial payments).
# Batch10 already creates an independent receipt markup; exchange only the
# iframe/printing engine, without changing its business content.
hospital=r"""
novaPrintThermalDocument=function(markup){
  novaUnifiedThermalPrint(markup,'thermal80');
};
"""
add('hospital/static/finance-ui.js',engine+'\n'+hospital,'function novaPrintReceipt(inv,index)')

print('NOVA_BATCH11_UNIFIED_PRINT_APPLIED pharmacy thermal, hospital thermal, A4 preserved')
