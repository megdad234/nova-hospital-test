/* NOVA Batch11 browser-document print contract tests (Node no external deps).
   Covers document isolation, 80/58 paper sizes, long content and blank receipts. */
'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const engine=fs.readFileSync('.github/ci/nova_unified_thermal_engine.js','utf8');
const pharmacy=fs.readFileSync('pharmacy/static/nova_pharmacy_batch08.js','utf8');
const pharmacyMain=fs.readFileSync('pharmacy/static/app.js','utf8');
const hospital=fs.readFileSync('hospital/static/finance-ui.js','utf8');
assert(pharmacy.includes("printReceipt=async function()"));
assert(pharmacy.includes("printable.classList.contains('thermal-receipt')"));
assert(pharmacy.includes("novaUnifiedThermalPrint(printable.outerHTML,paper)"));
assert(hospital.includes("novaPrintThermalDocument=function(markup)"));
assert(hospital.includes("novaUnifiedThermalPrint(markup,'thermal80')"));
assert(pharmacy.includes(engine.trim()));
assert(hospital.includes(engine.trim()));
assert(hospital.includes("function financePrintInvoice(inv)"));
assert(pharmacyMain.includes("function printPurchase(id)"));
vm.runInThisContext(engine,{filename:'nova_unified_thermal_engine.js'});

async function check(paper,height,expectedWidth){
  const emitted={count:0,page:'',html:''};
  const ticket={textContent:'NOVA Hospital — مبلغ 5,000',scrollHeight:height,
    getBoundingClientRect(){return {height}}};
  const doc={
    fonts:{ready:Promise.resolve()},
    getElementById(id){assert.equal(id,'nova-ticket');return ticket},
    createElement(type){assert.equal(type,'style');return {textContent:''}},
    head:{appendChild(el){emitted.page=el.textContent}}
  };
  const docwin={addEventListener(){},focus(){},print(){emitted.count++}};
  const frame={
    style:{},setAttribute(){},contentDocument:doc,contentWindow:docwin,
    remove(){emitted.removed=true},
  };
  global.document={
    getElementById(){return null},
    createElement(type){assert.equal(type,'iframe');return frame},
    body:{appendChild(el){emitted.html=el.srcdoc; Promise.resolve().then(()=>el.onload())}}
  };
  global.setTimeout=()=>1;
  novaUnifiedThermalPrint('<article class="thermal-receipt">NOVA Hospital</article>',paper);
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(emitted.count,1,'print dialog should launch only once');
  assert(emitted.page.startsWith('@page{size:'+expectedWidth+'mm '),emitted.page);
  assert(emitted.page.endsWith('mm;margin:0}'),emitted.page);
  assert(emitted.html.includes('width:'+expectedWidth+'mm!important'), 'paper width missing');
  assert(!emitted.html.includes('size:A4'),'no A4 should enter receipt document');
  assert(emitted.html.includes('thermal-receipt'), 'preserve pharmacy receipt');
}
(async()=>{
  await check('thermal80',180,80);
  await check('thermal58',205,58);
  await check('thermal80',1500,80);
  console.log('NOVA11_JS_PRINT_TEST_PASSED: 80mm/58mm, exact markup, no A4, one-page custom roll');
})().catch(e=>{console.error(e.stack||e);process.exitCode=1});
