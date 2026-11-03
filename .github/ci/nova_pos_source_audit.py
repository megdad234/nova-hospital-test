# -*- coding: utf-8 -*-
"""Read-only NOVA POS source audit. Runs only on extracted source in CI."""
from pathlib import Path
import re
root=Path(__file__).resolve().parents[2]
for filename in ('pharmacy/static/app.js','pharmacy/static/ux_v14.js','pharmacy/app.py'):
    p=root/filename
    lines=p.read_text(encoding='utf-8').splitlines()
    print('NOVA_POS_AUDIT_FILE',filename,'LINES',len(lines))
    keys=('function pos(', 'function confirmSale(', 'function saleCart(', 'function saleTotal(', 'def sell(', 'def sale', 'function checkout(', 'sale-cart-list', 'salearea', 'sale-discount', 'discount:', 'discount=', 'saleRows', 'received', 'profit', 'cost_basis')
    matches=[i for i,line in enumerate(lines) if any(k in line for k in keys)]
    seen=set()
    for i in matches[:55]:
        a=max(0,i-3);b=min(len(lines),i+10)
        if any(j in seen for j in range(a,b)):continue
        seen.update(range(a,b))
        print('NOVA_POS_AUDIT_SNIPPET',filename,a+1,b)
        for j in range(a,b):print(f'{j+1}: {lines[j][:240]}')
