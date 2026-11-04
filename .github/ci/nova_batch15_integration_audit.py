"""Bounded audit of extracted, fully patched pharmacy source.

Prints only schema, route and price anchors needed for integrating
supplier price lists without guessing existing database contracts.
"""
from pathlib import Path
import re
p=Path("pharmacy/app.py")
s=p.read_text(encoding="utf-8")
lines=s.splitlines()
patterns=[
 r"CREATE TABLE.*(?:packages|purchase_lines|audit)",
 r"ALTER TABLE.*(?:packages|purchase_lines)",
 r"def (?:init_db|db|connect|nova_bulk_unpriced|audit|do_GET|do_POST)",
 r"/api/v1/(?:nova-reprice-unpriced|products|packages|purchases)",
 r"INSERT INTO (?:purchase_lines|audit)",
 r"FROM purchase_lines",
 r"UPDATE packages SET sale_price",
]
for pattern in patterns:
 print("\n=== ",pattern," ===")
 hits=[i for i,line in enumerate(lines) if re.search(pattern,line,re.I)]
 print("matches",len(hits))
 for i in hits[:8]:
  lo=max(0,i-3);hi=min(len(lines),i+7)
  for j in range(lo,hi):
   print(f"{j+1}: {lines[j][:220]}")
print("\n=== UI anchors ===")
for path in ("pharmacy/static/index.html","pharmacy/static/ux_v14.js"):
 q=Path(path)
 if q.exists():
  ls=q.read_text(encoding="utf-8").splitlines()
  for i,line in enumerate(ls):
   if re.search(r"importDialog|nova_pharmacy_batch08|ux_v14.js|price",line,re.I):
    print(path,i+1,line[:180])
    if i>2000: break
