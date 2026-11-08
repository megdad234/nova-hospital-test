'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');

const script=fs.readFileSync('pharmacy/static/nova_batch13_purchase.js','utf8');
const stocked={id:1,active:1,name:'Test Medicine Stock',generic_name:'Generic',strength:'10 mg',sku:'STOCK',
  available:30,base_uom:'شريط',packages:[{id:11,unit_name:'علبة',factor:3,barcode:'STK123',sale_price:5000}]};
const master={id:2,active:1,name:'Test Medicine Master',generic_name:'Generic',strength:'10 mg',sku:'MASTER',
  available:0,base_uom:'شريط',packages:[{id:22,unit_name:'علبة',factor:3,barcode:'',sale_price:0}]};
const search={value:'test'};
const results={innerHTML:''},count={textContent:''};
const choice={value:'',options:[],replaceChildren(){this.options=[];},add(o){this.options.push(o)}};
const els={'buy-search':search,'buy-suggestions':results,'buy-count':count,'buy-pkg':choice};
const state={products:[master,stocked],suppliers:[{id:10,name:'Test Supplier'}],purchaseRows:[],
  purchaseDate:'2026-11-03',purchaseRef:'',purchaseNote:'',purchasePay:'credit',
  purchasePaid:'',purchaseBankRef:'',purchaseSupplier:10,madarPartialPurchase:false};
const env={
  window:{},state,document:{querySelector(){return null}},$(id){return els[id]||null},
  purchase(){return 'old'},nav(){},filterBuyChoices(){},
  skuPack(id){const p=state.products.find(x=>x.packages.some(pk=>pk.id===id));
    return p?{...p.packages.find(pk=>pk.id===id),product:p}:null},
  esc(x){return String(x??'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/"/g,'&quot;')},
  fmt(x){return Number(x).toLocaleString('en-US')},
  sel(label,id){return '<select id="'+id+'"></select>'},
  f(label,id){return '<input id="'+id+'">'},
  today(){return '2026-11-03'},
  v(id){return els[id]?.value||''},
  Option:class{constructor(text,value){this.text=text;this.value=value}},
  novaPurchaseSuggestedPrice(row){return Math.round((row.unit_cost||0)*1.25)},
  toast(){},
};
vm.createContext(env);
vm.runInContext(script,env);
const html=env.purchase();
assert.match(html,/nova13-columns/);
assert.match(html,/nova13-invoice/);
assert.match(html,/nova13-finder/);
assert.match(html,/nova13-table-scroll/);
state.nova13Selected=11;
state.nova13Entry={};
assert.match(env.purchase(),/nova13-barcode/);
assert.match(html,/nova13SaveDraft/);
env.filterBuyChoices();
assert.equal(count.textContent.startsWith('2 نتيجة'),true);
assert.ok(results.innerHTML.indexOf('data-nova13-choice="11"')<
          results.innerHTML.indexOf('data-nova13-choice="22"'),
          'stock item must precede nonstock dictionary item');
const unitRule=env.window.nova13UnitRules([{
  package_id:11,nova13_unit_count:3,nova_manual_sale_price:true,nova_sale_price:5000
}]);
assert.equal(unitRule[0].unit_price,1667);
assert.equal(env.window.nova13Barcodes([{
  package_id:11,nova13_barcode_dirty:true,nova13_barcode:'STOCK-NEW'
}])[0].barcode,'STOCK-NEW');
state.purchaseRows=[{package_id:11,qty:1,unit_cost:20000,nova13_unit_count:3,nova_sale_price:15000,nova_manual_sale_price:true}];
const fake={value:'21000',closest(){return null}};
env.window.nova13LivePackPrice(0,fake);
assert.equal(state.purchaseRows[0].nova13_unit_sale_price,7000);
assert.equal(state.purchaseRows[0].nova13_unit_manual,false);
env.window.nova13LiveUnitPrice(0,{value:'5000',closest(){return null}});
assert.equal(state.purchaseRows[0].nova_sale_price,15000);
assert.equal(state.purchaseRows[0].nova13_unit_sale_price,5000);
console.log('NOVA13_UI_SMOKE_OK: RTL split view, stock-first single search, barcode, editable strip prices');
