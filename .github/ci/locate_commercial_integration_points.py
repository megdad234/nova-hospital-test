"""Identify concrete pharmacy startup and database integration points.

The generated report is line-precise, designed to drive a later audited
integration patch. It does not mutate the original NOVA source.
"""
from __future__ import annotations
import ast
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
STAGE = ROOT / "commercial_pharmacy_stage"
SOURCE = STAGE / "pharmacy"
if not SOURCE.exists():
    raise SystemExit("MISSING_POST_PATCH_PHARMACY_SOURCE")

keywords = {
    "sqlite_connect": r"sqlite3\s*\.\s*connect\s*\(",
    "database_path": r"(?i)(?:database|db_path|db_file|sqlite|\.db\b)",
    "server_bind": r"(?i)(?:\.run\(|HTTPServer\(|ThreadingHTTPServer\(|\.serve_forever\(|uvicorn|host\s*=|port\s*=)",
    "service_registration": r"(?i)(?:winsw|nssm|sc\.exe|service_name|ServiceFramework|pywin32)",
    "first_admin": r"(?i)(?:first.admin|admin.setup|bootstrap.admin|create.admin|initial.admin)",
    "patient_lookup": r"(?i)(?:nova-hospital-patient-search|hospital.patient|patient.search|patient_id)",
    "receipt": r"(?i)(?:thermal|receipt|printer|print)",
    "backup": r"(?i)(?:backup|restore|checkpoint)",
}
report = {"status": "integration_points_unverified", "source_root": "pharmacy",
          "entrypoints": [], "functions": [], "signals": {}, "critical_blockers": []}
for filename in ("app.py", "desktop.py", "server_host.py", "recovery.py"):
    p = SOURCE / filename
    if not p.exists():
        report["critical_blockers"].append("missing " + filename)
        continue
    body = p.read_text(encoding="utf-8", errors="replace")
    lines = body.splitlines()
    try:
        tree = ast.parse(body, filename=filename)
    except SyntaxError as exc:
        report["critical_blockers"].append(f"invalid Python {filename}: {exc}")
        continue
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if re.search(r"(?i)(?:main|start|serve|init|setup|db|backup|admin|login|insurance|print|receipt)", node.name):
                report["functions"].append({"file": filename, "name": node.name, "line": node.lineno,
                                            "kind": type(node).__name__})
        if isinstance(node, ast.If):
            if isinstance(node.test, ast.Compare) and any(
                isinstance(comp, ast.Constant) and comp.value == "__main__"
                for comp in node.test.comparators):
                report["entrypoints"].append({"file": filename, "line": node.lineno})
    for category, pattern in keywords.items():
        for index, line in enumerate(lines, 1):
            if re.search(pattern, line):
                report["signals"].setdefault(category, []).append(
                    {"file": filename, "line": index, "excerpt": line.strip()[:220]})
report["critical_blockers"].append("NOVA pharmacy entrypoint not yet switched to commercial paths and service")
report["critical_blockers"].append("Hospital patient API not yet replaced with commercial customer registry")
report["critical_blockers"].append("Windows installer not yet generated and acceptance-tested")
(STAGE / "INTEGRATION_POINTS.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print("INTEGRATION_POINTS_IDENTIFIED", len(report["functions"]),
      sum(len(v) for v in report["signals"].values()))
