"""Assemble a strictly isolated commercial Windows runtime payload.

Requires an audited extraction snapshot and an independently provisioned Python
runtime. Does not create a runtime, start a server or authorize release.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import shutil

FORBIDDEN = {".db", ".sqlite", ".sqlite3", ".pyc"}
REQUIRED = ("pharmacy/app.py", "pharmacy/server_host.py",
            "pharmacy/static/app.js", "commercial_pharmacy/launch.py",
            "commercial_pharmacy/runtime_isolation.py")

def assemble(stage: Path, runtime: Path, destination: Path):
    stage, runtime, destination = (p.resolve() for p in (stage, runtime, destination))
    if destination == stage or destination == runtime or destination in stage.parents or destination in runtime.parents:
        raise ValueError("Unsafe payload destination")
    if stage in destination.parents or runtime in destination.parents:
        raise ValueError("Payload destination must be separate from source and runtime")
    if destination.exists():
        raise FileExistsError("Refusing to overwrite existing payload")
    manifest = stage / "EXTRACTION_MANIFEST.json"
    if not manifest.is_file() or json.loads(manifest.read_text(encoding="utf-8")).get("status") != "SOURCE_SNAPSHOT_ONLY_NOT_INSTALLABLE":
        raise ValueError("Audited source snapshot manifest required")
    for relative in REQUIRED:
        if not (stage / relative).is_file():
            raise FileNotFoundError(relative)
    if not (runtime / "python.exe").is_file():
        raise FileNotFoundError("Dedicated Windows Python runtime missing")
    for root in (stage / "pharmacy", stage / "commercial_pharmacy", runtime):
        for file in root.rglob("*"):
            if file.is_symlink():
                raise ValueError("Symlinks are not allowed in runtime payload")
            if file.is_file() and (file.suffix.lower() in FORBIDDEN or file.name.lower().endswith(("-wal", "-shm"))):
                raise ValueError("Database or bytecode must not enter runtime payload: " + file.name)
    destination.mkdir(parents=True)
    try:
        shutil.copytree(stage / "pharmacy", destination / "pharmacy")
        shutil.copytree(stage / "commercial_pharmacy", destination / "commercial_pharmacy")
        shutil.copytree(runtime, destination / "runtime")
        (destination / "PAYLOAD_NOT_RELEASE_AUTHORIZED.txt").write_text(
            "Source and Python runtime staged only. Full Windows acceptance still required.\n", encoding="utf-8")
    except Exception:
        shutil.rmtree(destination)
        raise
    return destination

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", type=Path, required=True)
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    print(assemble(args.stage, args.runtime, args.destination))
if __name__ == "__main__":
    main()
