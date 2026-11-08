"""Isolated NOVA admin refunds UI patch. No database, cashier, or finance API edits."""
from pathlib import Path
app=Path('hospital/static/app.js')
admin=Path('hospital/static/admin-ui.js')
ui=Path('hospital/static/nova_admin_refunds.js')
a=app.read_text(encoding='utf-8')
b=admin.read_text(encoding='utf-8')
assert "['admin-finance','التحصيل والحسابات']" in a
assert "async function viewAdminPage(section){" in b
assert "function wireAdminPage(section){" in b
assert "function novaRefundAdminView" in ui.read_text(encoding='utf-8')
if "['admin-refunds','إدارة الاستردادات']" not in a:
 a=a.replace("['admin-finance','التحصيل والحسابات'],","['admin-finance','التحصيل والحسابات'],['admin-refunds','إدارة الاستردادات'],",1)
if "if(section==='admin-refunds')return novaRefundAdminView();" not in b:
 b=b.replace("async function viewAdminPage(section){","async function viewAdminPage(section){\n  if(section==='admin-refunds')return novaRefundAdminView();",1)
if "if(section==='admin-refunds'){novaWireRefundAdmin();return}" not in b:
 b=b.replace("function wireAdminPage(section){","function wireAdminPage(section){\n  if(section==='admin-refunds'){novaWireRefundAdmin();return}",1)
marker="/* NOVA_ADMIN_REFUNDS_V1:"
if marker not in b:
 b+="\n"+ui.read_text(encoding='utf-8')
app.write_text(a,encoding='utf-8')
admin.write_text(b,encoding='utf-8')
print('NOVA_ADMIN_REFUNDS_UI_INSTALLED')
