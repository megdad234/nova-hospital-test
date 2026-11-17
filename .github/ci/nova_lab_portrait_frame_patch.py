"""NOVA LAB A4 PORTRAIT: replace ONLY the hospital lab-result print call.

Root cause: lab report currently prints inside shared hospital DOM, with global
@page size:A4 (orientation unspecified). A named @page on a nested element does
not reliably override the system/Edge printer landscape setting.
This patch creates a clean SAME-ORIGIN print document (hidden iframe) with
a single UNNAMED @page A4 portrait; pharmacy and receipts are untouched.
"""
import json
import re
from pathlib import Path

REPORT_SIGNATURE = "async function printReport(id)"
OLD_PRINT = """    const area=$('print-area');area.innerHTML=html;
    document.body.classList.add('printing-lab');
    const cleanup=()=>{document.body.classList.remove('printing-lab');area.innerHTML=''};
    window.addEventListener('afterprint',cleanup,{once:true});
    await Promise.all([...area.querySelectorAll('img')].map(x=>x.decode?.().catch(()=>{})||Promise.resolve()));
    window.print();"""
MARKER="/* NOVA_LAB_ISOLATED_A4_PORTRAIT_V2 */"

def patch(source, css):
    if MARKER in source:
        raise RuntimeError("Lab print hardfix already applied")
    if source.count(REPORT_SIGNATURE)!=1 or source.count(OLD_PRINT)!=1:
        raise RuntimeError("The real NOVA printReport contract changed; refusing speculative patch")
    if len(re.findall(r'(?m)^\s*@page\s*\{',css))!=1 or "size: A4 portrait;" not in css:
        raise RuntimeError("Standalone LAB stylesheet is not exclusively A4 portrait")
    if "@media print" not in css or "table-layout:fixed" not in css:
        raise RuntimeError("Standalone LAB table print CSS missing")
    js_css=json.dumps(css,ensure_ascii=False)
    helper=r'''
/* NOVA_LAB_ISOLATED_A4_PORTRAIT_V2 */
function novaLabPrintA4Portrait(reportMarkup){
  // The only page stylesheet in this document has @page A4 portrait;
  // no hospital/admin/receipt print rules can leak into this context.
  const old=document.getElementById('nova-lab-a4-portrait-frame');
  if(old)old.remove();
  const frame=document.createElement('iframe');
  frame.id='nova-lab-a4-portrait-frame';
  frame.setAttribute('title','طباعة نتائج المعمل A4 بالطول');
  frame.setAttribute('aria-hidden','true');
  // Never display the iframe, but keep a real layout box. display:none
  // can make Chromium/Edge print a blank PDF or ignore @page size.
  frame.style.cssText='position:fixed;left:0;top:0;width:210mm;height:297mm;'+
    'opacity:0;pointer-events:none;border:0;z-index:-1';
  const sheet=__NOVA_LAB_CSS__;
  // Report fields are already escaped by the existing NOVA report builder.
  // Only sanitized clinical report markup is inserted; no app JS or forms.
  const markup='<!doctype html><html lang="ar" dir="rtl"><head>'+
    '<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">'+
    '<title>نتائج المعمل - A4 Portrait</title><style>'+sheet+'</style></head><body>'+
    reportMarkup+'</body></html>';
  frame.addEventListener('load',async ()=>{
    if(!frame.isConnected)return;
    const w=frame.contentWindow;
    if(!w)return;
    // Wait for report logo/font layout so the first print preview is final.
    try{
      if(w.document.fonts && w.document.fonts.ready)await w.document.fonts.ready;
      const images=Array.from(w.document.images||[]);
      await Promise.all(images.map(img=>img.complete?Promise.resolve():
        new Promise(resolve=>{
          img.addEventListener('load',resolve,{once:true});
          img.addEventListener('error',resolve,{once:true});
        })));
      if(!frame.isConnected)return;
      // Keep the frame until the actual browser print preview/dialog closes.
      // Deleting it on calling print() can yield clipped/blank output.
      w.addEventListener('afterprint',()=>{
        window.setTimeout(()=>{if(frame.isConnected)frame.remove()},1200);
      },{once:true});
      w.focus();
      w.print();
    }catch(err){
      if(frame.isConnected)frame.remove();
      notice('تعذر فتح طباعة المعمل: '+String(err.message||err),true);
    }
  },{once:true});
  frame.srcdoc=markup;
  document.body.appendChild(frame);
}
'''.replace("__NOVA_LAB_CSS__",js_css)
    source=source.replace(REPORT_SIGNATURE,helper+"\n"+REPORT_SIGNATURE,1)
    source=source.replace(OLD_PRINT,"    novaLabPrintA4Portrait(html);",1)
    return source

def apply(root):
    root=Path(root)
    file=root/"hospital/static/app.js"
    stylesheet=root/".github/ci/nova_lab_portrait_print.css"
    before=file.read_text(encoding="utf-8")
    out=patch(before,stylesheet.read_text(encoding="utf-8"))
    file.write_text(out,encoding="utf-8")
    return file

if __name__=="__main__":
    apply(Path(__file__).resolve().parents[2])
    print("NOVA_LAB_ISOLATED_A4_PORTRAIT_V2_APPLIED")
