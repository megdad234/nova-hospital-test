"""Patch NOVA pharmacy's actual DATA and DB globals for standalone runtime.

Fail-closed AST matching: only extracted pharmacy/app.py is modified.
The original NOVA Hospital source ZIP, server and database are untouched.
"""
from __future__ import annotations
import ast
import os
from pathlib import Path

ROOT = Path(os.environ.get("NOVA_EXTRACTION_ROOT", str(Path(__file__).resolve().parents[2]))).resolve()
target = ROOT / "pharmacy/app.py"
if not target.is_file():
    raise SystemExit("COMMERCIAL_DATABASE_SOURCE_MISSING")
source = target.read_text(encoding="utf-8")
tree = ast.parse(source)
assignments = {}
for node in tree.body:
    if isinstance(node, (ast.Assign, ast.AnnAssign)):
        names = ([t.id for t in node.targets if isinstance(t, ast.Name)]
                 if isinstance(node, ast.Assign) else
                 [node.target.id] if isinstance(node.target, ast.Name) else [])
        for name in names:
            if name in {"DATA", "DB"}:
                assignments.setdefault(name, []).append(node)
if any(len(assignments.get(name, [])) != 1 for name in ("DATA", "DB")):
    raise SystemExit("COMMERCIAL_DATABASE_GLOBAL_ANCHOR_DRIFT")
lines = source.splitlines(keepends=True)
patches = []
data = assignments["DATA"][0]
db = assignments["DB"][0]
if data.lineno >= db.lineno:
    raise SystemExit("COMMERCIAL_DATABASE_EXPECTED_DATA_BEFORE_DB")
replacement = """# Independent NOVA Commercial Pharmacy storage. Never reuse hospital DATA.
import os as _nova_commercial_os
from pathlib import Path as _nova_commercial_Path
DATA = _nova_commercial_Path(_nova_commercial_os.environ.get(
    'NOVA_COMMERCIAL_DATA_DIR',
    str(_nova_commercial_Path(_nova_commercial_os.environ.get('PROGRAMDATA') or
         str(_nova_commercial_Path.home() / 'AppData' / 'Local')) /
         'NOVACommercialPharmacy'))).expanduser().resolve()
"""
patches.append((data.lineno - 1, data.end_lineno, replacement))
patches.append((db.lineno - 1, db.end_lineno,
                "DB = DATA / 'commercial_pharmacy.sqlite3'\n"))
for start, end, value in sorted(patches, reverse=True):
    lines[start:end] = [value]
updated = "".join(lines)
ast.parse(updated)
if "commercial_pharmacy.sqlite3" not in updated:
    raise SystemExit("COMMERCIAL_DATABASE_PATCH_NOT_APPLIED")
target.write_text(updated, encoding="utf-8")
print("COMMERCIAL_PHARMACY_DATABASE_GLOBALS_ISOLATED")
