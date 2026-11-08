from pathlib import Path
p=Path('pharmacy/static/app.js')
s=p.read_text(encoding='utf-8')
start=s.index('function sales(){return ')
end=s.index('\nfunction showReceipt(',start)
old=s[start:end]
# Strictly isolated: no POS, returnModal, data logic, or other UI functions touched.
assert "state.sales.map(s=>" in old and "returnModal(" in old
assert old.count("state.sales.map(s=>")==1
assert old.count("returnModal(")==1
assert old.count("<tr>")==1
status="""function novaReturnDisplayStatus(s){
 const lines=Array.isArray(s.lines)?s.lines:[];
 const qty=lines.reduce((n,l)=>n+Math.max(0,Number(l.qty)||0),0);
 const returned=lines.reduce((n,l)=>n+Math.min(Math.max(0,Number(l.qty)||0),Math.max(0,Number(l.returned)||0)),0);
 return qty>0&&returned>=qty?'full':returned>0?'partial':'none';
}
"""
# The verified history row has a nested permission-controlled refund button.
# Change only that row's presentation, preserving the existing permission check and handler.
assert old.count("state.sales.map(s=>")==1
assert old.count("can('refund')?")==1
assert old.count('onclick="returnModal(${s.id})"')==1
assert old.count('onclick="showReceipt(${s.id})"')==1
new=old.replace('state.sales.map(s=>\x60<tr>', 'state.sales.map(s=>{const novaReturnState=novaReturnDisplayStatus(s);return \x60<tr style="background:${novaReturnState===\'full\'?\'#fee2e2\':novaReturnState===\'partial\'?\'#fef9c3\':\'\'}">',1)
assert new!=old, 'Sales history row template changed'
old_button="can('refund')?\x60<button class=\"btn danger small\" onclick=\"returnModal(${s.id})\">مرتجع</button>\x60:''"
new_button="novaReturnState==='full'?\x60<span style=\"color:#b91c1c;font-weight:700\">تم الاسترجاع</span>\x60:(novaReturnState==='partial'?\x60<span style=\"color:#a16207;font-weight:700\">مرتجع جزئي</span>\x60:'')+(can('refund')?\x60<button class=\"btn danger small\" onclick=\"returnModal(${s.id})\">مرتجع</button>\x60:'')"
new=new.replace(old_button,new_button,1)
# Do not offer a second refund when every sold unit has already been returned.
# Only change the rendered action; original refund permissions and handler remain.
new=new.replace("+(can('refund')?", "+(novaReturnState==='full'?'':(can('refund')?", 1)
new=new.replace("مرتجع</button>`:'')", "مرتجع</button>`:''))", 1)
new=new.replace('\x60))}', '\x60;}))}',1)
assert new!=old and 'novaReturnDisplayStatus(s)' in new
assert "novaReturnState==='full'?'':(can('refund')?" in new, 'Fully returned invoice must not show refund action'
assert new.count('onclick="returnModal(${s.id})"')==1, 'Refund handler must remain unchanged'
assert new.count('onclick="showReceipt(${s.id})"')==1, 'Receipt action must remain unchanged'
s=s[:start]+status+new+s[end:]
p.write_text(s,encoding='utf-8')
print('NOVA_RETURN_HISTORY_DISPLAY_ONLY')
