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
# Build on exact existing sale row, without replacing the whole history screen.
new=old.replace('state.sales.map(s=>','state.sales.map(s=>{const novaReturnState=novaReturnDisplayStatus(s);return ',1)
assert new.count('}))')==1, 'Unknown history callback structure'
new=new.replace('}))',';}))',1)
new=new.replace('<tr>','<tr style="background:${novaReturnState===\'full\'?\'#fee2e2\':novaReturnState===\'partial\'?\'#fef9c3\':\'\'}">',1)
# Locate only the pre-existing refund button, retain its original onclick and behavior for partial/normal.
import re
pattern=r'<button[^>]*onclick="returnModal\(\$\{s\.id\}\)"[^>]*>[^<]*</button>'
matches=list(re.finditer(pattern,new))
assert len(matches)==1, 'Refund button shape changed; refuse unsafe patch'
button=matches[0].group()
replacement="${novaReturnState==='full'?'<span style=\\"color:#b91c1c;font-weight:700\\">تم الاسترجاع</span>':novaReturnState==='partial'?'<span style=\\"color:#a16207;font-weight:700\\">مرتجع جزئي</span>':''}"+button
# In a full refund, suppress original button visually, but never alter the refund function.
replacement="${novaReturnState==='full'?'<span style=\\"color:#b91c1c;font-weight:700\\">تم الاسترجاع</span>':novaReturnState==='partial'?'<span style=\\"color:#a16207;font-weight:700\\">مرتجع جزئي</span>':''}"+ "${novaReturnState==='full'?'':\`"+button+"\`}"
new=new[:matches[0].start()]+replacement+new[matches[0].end():]
s=s[:start]+status+new+s[end:]
p.write_text(s,encoding='utf-8')
print('NOVA_RETURN_HISTORY_DISPLAY_ONLY')
