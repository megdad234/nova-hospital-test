from pathlib import Path
s=Path('pharmacy/app.py').read_text(encoding='utf-8')
j=Path('pharmacy/static/index.html').read_text(encoding='utf-8')
for key in ('def sale_list(', 'def sale_history(', 'def sale_return(', 'CREATE TABLE IF NOT EXISTS sale_returns','CREATE TABLE sale_returns'):
 i=s.find(key)
 if i>=0:print('NOVA_RETURN_INSPECT',key,repr(s[i:i+2400]))
for key in ('فواتير البيع والمرتجعات','سجل الفواتير والمرتجعات','function renderSales','function saleHistory','function saleReturn'):
 i=j.find(key)
 if i>=0:print('NOVA_RETURN_UI',key,repr(j[max(0,i-600):i+1800]))
