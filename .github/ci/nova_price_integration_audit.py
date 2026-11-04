"""Read-only NOVA integration audit, run against extracted source in CI."""
from pathlib import Path
import re
p=Path("pharmacy/app.py")
s=p.read_text(encoding="utf-8")
patterns=[
 r"CREATE TABLE[^;]{0,1200};",
 r"def (?:init_db|connect_db|nova_bulk_unpriced|nova_purchase_save|audit|auth|handle)[^\n]*",
 r"'/api/v1/[^']*(?:price|package|purchase)[^']*'",
 r"purchase_lines[^\n]{0,180}",
 r"packages[^\n]{0,180}",
 r"def do_(?:GET|POST)[^\n]*",
]
print("NOVA AUDIT BEGIN")
for pat in patterns:
    matches=list(re.finditer(pat,s,re.I|re.S if pat.startswith("CREATE") else re.I))
    print("PATTERN",pat,"COUNT",len(matches))
    for m in matches[:12]:
        line=s.count("\n",0,m.start())+1
        print("LINE",line,repr(m.group(0)[:900]))
print("NOVA AUDIT END")
