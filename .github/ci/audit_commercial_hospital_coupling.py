"""Fail-closed audit for commercial pharmacy hospital API coupling.

Any unresolved hospital network call blocks the standalone installer. The
source snapshot remains available for diagnosis and is NOT an installable app.
"""
from pathlib import Path
import os
import json
import re

ROOT = Path(os.environ.get('NOVA_EXTRACTION_ROOT', str(Path(__file__).resolve().parents[2]))).resolve()
STAGE = ROOT / "commercial_pharmacy_stage"
pharmacy = STAGE / "pharmacy"
if not pharmacy.is_dir():
    raise SystemExit("MISSING_COMMERCIAL_PHARMACY_STAGE")
patterns = {
    "hospital_api": re.compile(r"(?i)/api/(?:v1/)?(?:nova-hospital|hospital)(?:/|[-\w]*)"),
    "hospital_db_table": re.compile(r"(?i)\bhospital_patients\b"),
    "hospital_import": re.compile(r"(?m)^\s*(?:from\s+hospital\b|import\s+hospital\b)"),
}
hits = []
for p in sorted(pharmacy.rglob("*")):
    if not p.is_file() or p.suffix.lower() not in {".py", ".js", ".html", ".css"}:
        continue
    for index, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        for name, pattern in patterns.items():
            if pattern.search(line):
                hits.append({"type": name, "file": str(p.relative_to(STAGE)),
                             "line": index, "excerpt": line.strip()[:180]})
report = {"standalone_network_and_schema_clear": not hits, "unresolved": hits,
          "installable": False}
(STAGE / "HOSPITAL_COUPLING_BLOCKERS.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print("COMMERCIAL_HOSPITAL_COUPLING_BLOCKERS", len(hits))
# Discovery itself does not fail: the release gate MUST refuse a build while
# any unresolved blockers exist. This allows inspecting the full source report.
