"""Build an inspectable manifest of pharmacy runtime dependencies and assets.

This is deliberately conservative: it never deletes files, rewrites imports,
or assumes that a referenced hospital module is safe to remove.
"""
from __future__ import annotations
import ast
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
STAGE = ROOT / "commercial_pharmacy_stage"
SOURCE = STAGE / "pharmacy"
if not SOURCE.is_dir():
    raise SystemExit("MISSING_POST_PATCH_PHARMACY_SOURCE")

report = {"status": "requires_integration", "asset_references": [],
          "python_imports": [], "unresolved_local_assets": [],
          "hospital_module_imports": [], "source_hashes": {}}
asset_pattern = re.compile(r"""(?i)(?:src|href)\s*=\s*["']([^"'?#]+)|(?:fetch\s*\(\s*["'])([^"'?#]+)""")
for file in sorted(SOURCE.rglob("*")):
    if not file.is_file():
        continue
    rel = str(file.relative_to(STAGE))
    report["source_hashes"][rel] = hashlib.sha256(file.read_bytes()).hexdigest()
    if file.suffix.lower() not in {".py", ".js", ".html", ".css"}:
        continue
    body = file.read_text(encoding="utf-8", errors="replace")
    if file.suffix == ".py":
        tree = ast.parse(body, filename=rel)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                modules = [("." * node.level) + (node.module or "")]
            else:
                continue
            for module in modules:
                entry = {"file": rel, "line": node.lineno, "module": module}
                report["python_imports"].append(entry)
                if module.startswith("hospital.") or module == "hospital":
                    report["hospital_module_imports"].append(entry)
    if file.suffix.lower() not in {".html", ".js"}:
        continue
    for i, line in enumerate(body.splitlines(), 1):
        for match in asset_pattern.finditer(line):
            asset = next((v for v in match.groups() if v), None)
            if not asset or asset.startswith(("http:", "https:", "data:", "#", "mailto:")):
                continue
            report["asset_references"].append({"file": rel, "line": i, "asset": asset[:250]})
            if asset.startswith("/static/"):
                target = SOURCE / "static" / asset[len("/static/"):]
                if not target.is_file():
                    report["unresolved_local_assets"].append({"file": rel, "line": i, "asset": asset})
(STAGE / "PHARMACY_ASSET_DEPENDENCIES.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print("PHARMACY_ASSET_INVENTORY", len(report["asset_references"]),
      "MISSING_STATIC", len(report["unresolved_local_assets"]),
      "HOSPITAL_IMPORTS", len(report["hospital_module_imports"]))
