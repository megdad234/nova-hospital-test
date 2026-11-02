/* NOVA UNIFIED THERMAL ENGINE — used identically by Pharmacy and Hospital.
   Self-contained print document prevents all main-app @page / A4 / dashboard rules
   from leaking into 80mm receipts. Real printer remains user-selected by browser. */
function novaUnifiedThermalPrint(markup, requestedPaper) {
  const paper=requestedPaper==='thermal58'?'thermal58':'thermal80';
  const mm=paper==='thermal58'?58:80;
  const contentMM=paper==='thermal58'?48:72;
  const padMM=paper==='thermal58'?5:4;
  let frame=document.getElementById('nova-unified-thermal-frame');
  if(frame)frame.remove();
  frame=document.createElement('iframe');
  frame.id='nova-unified-thermal-frame';
  frame.title='NOVA thermal '+mm+'mm';
  frame.setAttribute('aria-hidden','true');
  // Offscreen but with a real viewport: 1px iframes have caused truncated
  // measurements and non-deterministic CSS pagination in print previews.
  frame.style.cssText='position:fixed;left:-15000px;top:0;width:100mm;height:550px;border:0;opacity:0;pointer-events:none';
  const css=[
    '*{box-sizing:border-box}',
    'html{padding:0!important;margin:0!important;background:white!important;overflow:visible!important}',
    'body{width:'+mm+'mm!important;max-width:'+mm+'mm!important;min-width:'+mm+'mm!important;margin:0!important;padding:'+padMM+'mm!important;color:#101010!important;background:white!important;direction:rtl;font:10pt/1.5 Tahoma,Arial,sans-serif!important;overflow:visible!important}',
    '#printable,.thermal-receipt,.nova-thermal,.nova-thermal-v2{width:'+contentMM+'mm!important;max-width:'+contentMM+'mm!important;min-width:0!important;margin:0!important;padding:0!important;border:0!important;box-shadow:none!important;font:inherit!important;line-height:1.5!important;color:#101010!important;direction:rtl!important;overflow:visible!important}',
    'h1,h2,h3,p{margin-top:0}',
    '.receipt-center,.nova-receipt-head{text-align:center}',
    '.receipt-center h2,.nova-receipt-head h2{font-size:17pt!important;font-weight:800!important;line-height:1.3!important;margin:0 0 1mm!important}',
    '.receipt-center p,.nova-receipt-head p{font-size:10pt;margin:1mm 0}',
    '.receipt-divider{border:0;border-bottom:1px dashed #444;margin:2.5mm 0}',
    '.receipt-line{padding:1.4mm 0;border-bottom:1px dotted #bbb;break-inside:avoid}',
    '.receipt-line-name{font-weight:700;overflow-wrap:anywhere}',
    '.receipt-line-nums,.receipt-sum{display:flex;justify-content:space-between;align-items:baseline;gap:3mm;break-inside:avoid}',
    '.receipt-grand{font-size:12pt;font-weight:800;border-top:1px solid #777;margin-top:1mm;padding-top:1.5mm;break-inside:avoid}',
    '.nova-receipt-divider{border-top:1px dashed #444;margin:2.5mm 0}',
    '.nova-receipt-row{display:flex;justify-content:space-between;align-items:baseline;gap:3mm;padding:1.2mm 0;break-inside:avoid}',
    '.nova-receipt-row span{flex:0 1 auto}',
    '.nova-receipt-row strong{flex:0 1 auto;text-align:left;overflow-wrap:anywhere}',
    '.nova-receipt-ltr,bdi[dir=ltr],[dir=ltr]{direction:ltr!important;unicode-bidi:isolate;font-variant-numeric:tabular-nums}',
    '.nova-receipt-service-title{font-weight:800;margin-bottom:1mm}',
    '.nova-receipt-service{display:flex;justify-content:space-between;align-items:baseline;gap:2mm;padding:1mm 0;border-bottom:1px dotted #aaa;break-inside:avoid}',
    '.nova-receipt-service span:first-child{flex:1;min-width:0}',
    '.nova-receipt-service span:last-child{flex:0 0 auto;font-weight:700}',
    '.nova-receipt-total{font-size:12pt;font-weight:800;border-top:1px solid #777;border-bottom:1px solid #777;padding:1mm 0;margin:1mm 0;break-inside:avoid}',
    '.nova-receipt-foot{display:flex;flex-direction:column;align-items:center;gap:1mm;text-align:center;font-size:9pt;margin-top:2mm}',
    'table{width:100%;border-collapse:collapse}th,td{font-size:9pt;padding:1mm;overflow-wrap:anywhere;border:1px solid #aaa}',
    '@media print{html,body{margin:0!important;padding-right:'+padMM+'mm!important;padding-left:'+padMM+'mm!important}#printable,.thermal-receipt,.nova-thermal-v2{break-inside:auto}}'
  ].join('\n');
  const source='<!doctype html><html lang="ar" dir="rtl"><head>'+
    '<meta charset="utf-8"><title>NOVA Thermal '+mm+'mm</title><style>'+css+'</style>'+
    '</head><body><main id="nova-ticket">'+markup+'</main></body></html>';
  let ready=false,done=false;
  const cleanup=()=>{if(done)return;done=true;frame.remove()};
  frame.onload=async function(){
    if(ready)return;ready=true;
    try{
      const doc=frame.contentDocument;
      if(!doc)throw Error('المستند الحراري غير متاح');
      if(doc.fonts?.ready)await doc.fonts.ready;
      const ticket=doc.getElementById('nova-ticket');
      if(!ticket||!ticket.textContent.trim())throw Error('الإيصال فارغ');
      // Fit the WHOLE ticket into ONE continuous roll segment. Measure only
      // the actual content; body.scrollHeight includes iframe viewport height.
      const cssHeight=Math.max(ticket.getBoundingClientRect().height,ticket.scrollHeight);
      const measuredMM=cssHeight*25.4/96;
      const length=Math.max(65,Math.ceil(measuredMM+2*padMM+12));
      if(!Number.isFinite(length)||length>1500)throw Error('الإيصال أطول من مقاس الطباعة المدعوم');
      const rule=doc.createElement('style');
      rule.textContent='@page{size:'+mm+'mm '+length+'mm;margin:0}';
      doc.head.appendChild(rule);
      // Driver paper selection still takes precedence if the user chooses A4.
      const win=frame.contentWindow;
      win.addEventListener('afterprint',cleanup,{once:true});
      win.focus();win.print();
      setTimeout(cleanup,120000);
    }catch(err){
      cleanup();
      if(typeof toast==='function')toast('خطأ طباعة الإيصال: '+err.message,true);
      else if(typeof notice==='function')notice('خطأ طباعة الإيصال: '+err.message,true);
    }
  };
  frame.srcdoc=source;
  document.body.appendChild(frame);
}
