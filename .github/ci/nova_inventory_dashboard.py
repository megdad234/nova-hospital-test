"""NOVA inventory-only dashboard overlay. No database/schema/routes/other pages changed."""
from pathlib import Path
p=Path('pharmacy/static/ux_v14.js')
s=p.read_text(encoding='utf-8')
marker='/* NOVA_INVENTORY_DASHBOARD_V1 */'
if marker in s:
    print('Inventory dashboard already installed')
else:
    addon=Path('pharmacy/static/nova_inventory_dashboard.js').read_text(encoding='utf-8')
    assert 'function stock()' in Path('pharmacy/static/app.js').read_text(encoding='utf-8')
    assert 'stockAdjustModal' in Path('pharmacy/static/app.js').read_text(encoding='utf-8')
    p.write_text(s+'\n'+marker+'\n'+addon+'\n',encoding='utf-8')
    print('NOVA_INVENTORY_DASHBOARD_APPLIED')
