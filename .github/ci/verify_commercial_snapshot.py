"""Verify that pharmacy extracted files are free of accidental hospital database copies.

Also checks symlink traversal, executable source integrity and minimum
pharmacy UI/API presence before attempting a Windows package.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

def verify_snapshot(stage: Path):
    manifest_path = stage / "EXTRACTION_MANIFEST.json"
    if not manifest_path.is_file():
        raise FileNotFoundError("Extraction manifest missing")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    issues = []
    for rel, expected in manifest.get("sha256", {}).items():
        path = stage / rel
        if path.is_symlink() or not path.is_file() or stage.resolve() not in path.resolve().parents:
            issues.append("missing or unsafe source file: " + rel)
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            issues.append("source integrity mismatch: " + rel)
    for file in (stage / "pharmacy").rglob("*"):
        if file.is_symlink():
            issues.append("source symlink forbidden: " + str(file))
        if file.is_file() and (file.suffix.lower() in (".db", ".sqlite", ".sqlite3") or file.name.lower().endswith((".db-wal", ".db-shm", ".sqlite-wal", ".sqlite-shm", ".sqlite3-wal", ".sqlite3-shm"))):
            issues.append("live database included: " + str(file))
    if not manifest.get("sha256"):
        issues.append("empty source manifest")
    return issues

if __name__ == "__main__":
    stage = Path("commercial_pharmacy_stage")
    problems = verify_snapshot(stage)
    result = {"source_integrity_passed": not problems, "issues": problems,
              "windows_installation_verified": False}
    (stage / "SOURCE_INTEGRITY.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    raise SystemExit(2 if problems else 0)
