"""Stage a read-only, post-patch pharmacy source snapshot for standalone extraction.

This is NOT an installable application. Hospital dependencies are inventoried,
not silently deleted. No production database or original source is modified.
"""
from pathlib import Path
import ast
import json
import shutil
import hashlib
import os

ROOT = Path(os.environ.get("NOVA_EXTRACTION_ROOT", str(Path(__file__).resolve().parents[2]))).resolve()
OUT = ROOT / "commercial_pharmacy_stage"
if OUT.is_symlink():
    raise SystemExit("REFUSE_SYMLINK_OUTPUT")
if OUT.exists():
    shutil.rmtree(OUT)
OUT.mkdir()
required = ["pharmacy/app.py", "pharmacy/desktop.py", "pharmacy/server_host.py",
            "pharmacy/static/index.html", "pharmacy/static/app.js",
            "pharmacy/windows-installer.iss"]
missing = [p for p in required if not (ROOT / p).is_file()]
if missing:
    raise SystemExit("MISSING_REQUIRED: " + ", ".join(missing))
shutil.copytree(ROOT / "pharmacy", OUT / "pharmacy",
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.db", "*.sqlite", "*.sqlite3"))
# Preserve shared components as references until their use is audited.
shutil.copytree(ROOT / "hospital", OUT / "hospital_reference",
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.db", "*.sqlite", "*.sqlite3"))
shutil.copytree(ROOT / "windows", OUT / "windows_reference",
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
for p in ("nova_server.py", "README_START_HERE_AR.md"):
    if (ROOT / p).exists():
        shutil.copy2(ROOT / p, OUT / p)
references = []
for f in (OUT / "pharmacy").rglob("*"):
    if not f.is_file() or f.suffix not in {".py", ".js", ".html", ".css", ".ps1", ".iss"}:
        continue
    text = f.read_text(encoding="utf-8", errors="replace")
    if f.suffix == ".py":
        try:
            ast.parse(text, filename=str(f))
        except SyntaxError as e:
            raise SystemExit(f"SYNTAX_ERROR {f}: {e}")
    lines = [(i, line.strip()[:220]) for i, line in enumerate(text.splitlines(), 1)
             if "hospital/" in line or "hospital." in line or "/api/hospital/" in line
             or "NOVA_Hospital" in line or "nova_server" in line]
    if lines:
        references.append({"file": str(f.relative_to(OUT)), "references": lines[:100]})
files = sorted(p for p in (OUT / "pharmacy").rglob("*") if p.is_file())
if any(p.suffix.lower() in {".db", ".sqlite", ".sqlite3"} for p in files):
    raise SystemExit("DATABASE_COPIED_INTO_SNAPSHOT")
manifest = {"status": "SOURCE_SNAPSHOT_ONLY_NOT_INSTALLABLE",
            "pharmacy_files": len(files), "hospital_dependencies": references,
            "sha256": {str(p.relative_to(OUT)): hashlib.sha256(p.read_bytes()).hexdigest()
                       for p in files},
            "required_acceptance": ["first-admin", "users-and-shifts", "pos",
                                    "inventory", "purchases", "insurance",
                                    "printing", "backup-restore", "windows-installer",
                                    "lan", "coexistence-with-nova"]}
(OUT / "EXTRACTION_MANIFEST.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"STAGED_PHARMACY_FILES={len(files)}; DEPENDENCY_FILES={len(references)}")
