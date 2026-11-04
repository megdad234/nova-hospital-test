"""Produce a detailed, machine-readable isolation inventory from post-patch NOVA.

No source rewriting, DB migration, or installer publication happens here.
"""
from __future__ import annotations
import ast
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(os.environ.get("NOVA_EXTRACTION_ROOT", str(Path(__file__).resolve().parents[2]))).resolve()
STAGE = ROOT / "commercial_pharmacy_stage"
if not (STAGE / "EXTRACTION_MANIFEST.json").is_file():
    raise SystemExit("RUN_STAGE_FIRST")
pharmacy = STAGE / "pharmacy"
patterns = {
    "hospital_routes": re.compile(r"(?i)/(?:api|hospital)/[^ ]*(?:hospital|patient|laboratory|reception|cashier)"),
    "hospital_symbols": re.compile(r"(?i)\b(?:hospital_gateway|hospital_core|hospital_admin|hospital_patient|nova_server)\b"),
    "db_paths": re.compile(r"(?i)[\w./\\-]+\.(?:sqlite3?|db)\b"),
    "network_listeners": re.compile(r"(?i)\b(?:0\.0\.0\.0|127\.0\.0\.1|localhost|listen|bind|port)\b"),
    "service_identity": re.compile(r"(?i)\b(?:NOVA[_ -]?Hospital|service[_ -]?name|display[_ -]?name|AppId|DefaultDirName)\b"),
    "insurance": re.compile(r"(?i)\b(?:insurance|beneficiary|policy|coverage|patient)\b"),
    "printing": re.compile(r"(?i)\b(?:receipt|thermal|printer|print)\b"),
    "first_admin": re.compile(r"(?i)\b(?:first.admin|bootstrap.admin|create.admin|initial.admin|setup.admin)\b"),
}
inventory = {"stage_manifest": "EXTRACTION_MANIFEST.json", "status": "AUDIT_ONLY",
             "isolation_complete": False, "files": {}, "imports": [], "routes": [],
             "risk_counts": {}, "required_separation": [
                 "database and migration namespace", "Windows service identity",
                 "installation and application data directories",
                 "network port and LAN client discovery",
                 "admin bootstrap and roles", "insurance patient registry",
                 "hospital API dependency", "thermal receipt compatibility",
                 "backups, restore and upgrades", "pharmacy POS regression tests"]}
for path in sorted(pharmacy.rglob("*")):
    if not path.is_file() or path.suffix.lower() not in {".py", ".js", ".html", ".css", ".iss", ".ps1"}:
        continue
    rel = str(path.relative_to(STAGE))
    body = path.read_text(encoding="utf-8", errors="replace")
    lines = body.splitlines()
    hits = {}
    for category, regex in patterns.items():
        matches = [{"line": i, "excerpt": line.strip()[:180]}
                   for i, line in enumerate(lines, 1) if regex.search(line)]
        if matches:
            hits[category] = {"count": len(matches), "samples": matches[:35]}
            inventory["risk_counts"][category] = inventory["risk_counts"].get(category, 0) + len(matches)
    if path.suffix == ".py":
        tree = ast.parse(body, filename=rel)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    inventory["imports"].append({"file": rel, "line": node.lineno, "module": alias.name})
            elif isinstance(node, ast.ImportFrom):
                inventory["imports"].append({"file": rel, "line": node.lineno,
                                             "module": ("." * node.level) + (node.module or "")})
    if path.suffix in {".py", ".js"}:
        for i, line in enumerate(lines, 1):
            if re.search(r"(?i)(?:@app\\.route|@router\\.|add_url_rule|/api/)", line):
                inventory["routes"].append({"file": rel, "line": i, "excerpt": line.strip()[:200]})
    inventory["files"][rel] = {"lines": len(lines), "hits": hits}
(STAGE / "ISOLATION_AUDIT.json").write_text(
    json.dumps(inventory, ensure_ascii=False, indent=2), encoding="utf-8")
summary = [
    "# NOVA Commercial Pharmacy — Isolation audit",
    "", "This is a source inventory, NOT a standalone release.",
    "", f"Pharmacy source files scanned: {len(inventory['files'])}",
    f"Imports recorded: {len(inventory['imports'])}",
    f"Potential route references: {len(inventory['routes'])}", "",
    "## Candidate coupling signals",
]
summary += [f"- {key}: {value}" for key, value in sorted(inventory["risk_counts"].items())]
summary += ["", "## Release gate", "Standalone installer is BLOCKED until dependencies are removed",
            "or explicitly replaced and all acceptance checks pass.", ""]
(STAGE / "ISOLATION_AUDIT.md").write_text("\n".join(summary), encoding="utf-8")
print("ISOLATION_AUDIT_COMPLETE", len(inventory["files"]), len(inventory["imports"]))
