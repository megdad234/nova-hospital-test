"""Guarded source launcher for extracted commercial pharmacy; not a Windows service."""
from __future__ import annotations
import argparse
import ast
import os
from pathlib import Path
import subprocess
import sys
from .runtime_isolation import paths, validate_paths, initialize_directories, choose_port

def prepare(source_root, data_dir=None, port=None, protected_hospital_paths=()):
    root = Path(source_root).resolve()
    app = root / "pharmacy" / "app.py"
    entry = root / "pharmacy" / "server_host.py"
    if not app.is_file() or not entry.is_file():
        raise FileNotFoundError("Commercial pharmacy source entrypoint missing")
    source = app.read_text(encoding="utf-8")
    ast.parse(source, filename=str(app))
    if "commercial_pharmacy.sqlite3" not in source or "NOVA_COMMERCIAL_DATA_DIR" not in source:
        raise RuntimeError("Commercial database patch not applied")
    if "NOVA_COMMERCIAL_PORT" not in entry.read_text(encoding="utf-8"):
        raise RuntimeError("Server does not honor commercial port override")
    ast.parse(entry.read_text(encoding="utf-8"), filename=str(entry))
    env = dict(os.environ)
    if data_dir is not None:
        env["NOVA_COMMERCIAL_DATA_DIR"] = str(Path(data_dir).resolve())
    if port is not None:
        env["NOVA_COMMERCIAL_PORT"] = str(port)
    config = validate_paths(paths(env), protected_hospital_paths)
    initialize_directories(config)
    env["NOVA_COMMERCIAL_DATA_DIR"] = str(config.data)
    env["NOVA_COMMERCIAL_PORT"] = str(choose_port(env))
    return [sys.executable, str(entry)], env, root

def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--data-dir")
    parser.add_argument("--port", type=int)
    parser.add_argument("--protect-hospital-dir", action="append", default=[])
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args(argv)
    command, env, root = prepare(args.source_root, args.data_dir, args.port, args.protect_hospital_dir)
    if args.preflight_only:
        print("COMMERCIAL_SOURCE_PREFLIGHT_PASSED_SERVER_NOT_STARTED")
        return 0
    return subprocess.call(command, cwd=str(root), env=env)

if __name__ == "__main__":
    raise SystemExit(main())
