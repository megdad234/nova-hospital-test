from pathlib import Path
s=Path('pharmacy/app.py').read_text(encoding='utf-8')
j=Path('pharmacy/static/index.html').read_text(encoding='utf-8')
for key in ('def sale_list(', 'def sale_history(', 'def sale_return(', 'CREATE TABLE IF NOT EXISTS sale_returns','CREATE TABLE sale_returns'):
 i=s.find(key)
 if i>=0:print('NOVA_RETURN_INSPECT',key,repr(s[i:i+2400]))
for key in ('فواتير البيع والمرتجعات','سجل الفواتير والمرتجعات','function renderSales','function saleHistory','function saleReturn'):
 i=j.find(key)
 if i>=0:print('NOVA_RETURN_UI',key,repr(j[max(0,i-600):i+1800]))

for key in ("FROM sales", "function sales", "sale-history", "sale-list", "sale-returns", "فواتير البيع"):
 for filename in ('pharmacy/app.py','pharmacy/static/index.html','pharmacy/static/app.js','pharmacy/static/nova_pharmacy_batch08.js'):
  p=Path(filename)
  if not p.exists():continue
  content=p.read_text(encoding='utf-8')
  hits=[i for i in range(len(content)) if content.startswith(key,i)]
  for i in hits[:4]:print('NOVA_RETURN_CONTEXT',filename,key,repr(content[max(0,i-550):i+950]))

for key in ('تحصيل الفترة','cash_gross','bank_gross'):
 for filename in ('hospital/static/admin-ui.js','hospital/static/nova_batch09_collections.js'):
  p=Path(filename)
  if p.exists():
   content=p.read_text(encoding='utf-8')
   for i in [i for i in range(len(content)) if content.startswith(key,i)][:4]:
    print('NOVA_FINANCE_CONTEXT',filename,key,repr(content[max(0,i-700):i+1100]))

for filename in ('pharmacy/app.py','pharmacy/static/index.html'):
 source=Path(filename).read_text(encoding='utf-8')
 lines=source.splitlines()
 for i,line in enumerate(lines):
  if any(t in line for t in ('sale_returns sr','FROM sales s','FROM sales ORDER','فواتير البيع والمرتجعات','سجل الفواتير والمرتجعات','function renderSale','function saleList','function salesList','function renderHistory')):
   print('NOVA16_TARGET',filename,i+1,repr('\\n'.join(lines[max(0,i-5):i+12])[:2000]))
