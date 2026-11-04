"""Commercial pharmacy administrator CLI.

Supports only safe infrastructure operations until the NOVA pharmacy server
entrypoint has been integrated and acceptance-tested. It never bootstraps a
second administrator or changes the existing NOVA pharmacy login flow.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
import sqlite3
from datetime import datetime, timezone
from .backup import create_backup, inspect_backup
from .database import open_pharmacy_database
from .restore import restore_offline
from .runtime_isolation import (
    check_port_free, choose_port, initialize_directories, paths, validate_paths,
    write_runtime_config,
)
from contextlib import closing

def parser():
    p = argparse.ArgumentParser(prog="nova-commercial-pharmacy")
    p.add_argument("--data-dir", type=Path, default=None)
    p.add_argument("--protect-hospital-dir", type=Path, action="append", default=[])
    commands = p.add_subparsers(dest="command", required=True)
    commands.add_parser("inspect")
    commands.add_parser("diagnose")
    commands.add_parser("initialize")
    commands.add_parser("check-database")
    commands.add_parser("list-backups")
    automatic = commands.add_parser("backup-auto")
    automatic.add_argument("--retain", type=int, default=30)
    backup = commands.add_parser("backup")
    backup.add_argument("filename")
    check = commands.add_parser("verify-backup")
    check.add_argument("file", type=Path)
    restore = commands.add_parser("restore-offline")
    restore.add_argument("file", type=Path)
    restore.add_argument("--confirm-service-stopped", action="store_true")
    return p

def run(argv=None):
    args = parser().parse_args(argv)
    env = None if args.data_dir is None else {"NOVA_COMMERCIAL_DATA_DIR": str(args.data_dir)}
    config = validate_paths(paths(env), args.protect_hospital_dir)
    if args.command == "inspect":
        result = {"data_dir": str(config.data), "database": str(config.database),
                  "port": choose_port(), "initialized": config.data.is_dir(),
                  "database_exists": config.database.is_file(),
                  "hospital_database_enabled": False}
    elif args.command == "diagnose":
        result = {"product": "NOVACommercialPharmacy",
                  "database": str(config.database),
                  "database_exists": config.database.is_file(),
                  "port": choose_port(),
                  "port_available": check_port_free(choose_port()),
                  "backups_directory_exists": config.backups.is_dir(),
                  "logs_directory_exists": config.logs.is_dir(),
                  "hospital_database_enabled": False,
                  "hospital_service_enabled": False}
        if config.database.is_file():
            with closing(sqlite3.connect(config.database.resolve().as_uri() + "?mode=ro", uri=True)) as conn:
                result["database_integrity"] = conn.execute("PRAGMA integrity_check").fetchone()[0]
    elif args.command == "initialize":
        result = write_runtime_config(config)
    elif args.command == "check-database":
        if not config.database.is_file():
            raise FileNotFoundError("Commercial database does not exist")
        with closing(sqlite3.connect(config.database.resolve().as_uri() + "?mode=ro", uri=True)) as conn:
            result = {"integrity": conn.execute("PRAGMA integrity_check").fetchone()[0],
                      "database": str(config.database), "read_only": True}
    elif args.command == "list-backups":
        result = {"backups": [
            {"name": item.name, "bytes": item.stat().st_size}
            for item in sorted(config.backups.iterdir())
            if item.is_file() and not item.is_symlink()
            and item.suffix.lower() in (".sqlite3", ".sqlite", ".db")
        ] if config.backups.is_dir() else []}
    elif args.command == "backup-auto":
        if not 1 <= args.retain <= 365:
            raise ValueError("Automatic backup retention must be 1 to 365")
        if not config.database.is_file():
            raise FileNotFoundError("Commercial database does not exist")
        with closing(open_pharmacy_database(config, protected_hospital_paths=args.protect_hospital_dir)) as conn:
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
            backup_path = create_backup(conn, config, "auto-" + stamp + ".sqlite3")
        backups = sorted((p for p in config.backups.glob("auto-*.sqlite3")
                          if p.is_file() and not p.is_symlink()),
                         key=lambda p: p.name, reverse=True)
        removed = []
        for old in backups[args.retain:]:
            old.unlink()
            removed.append(old.name)
        result = {"backup": str(backup_path), "retained": min(len(backups), args.retain),
                  "removed_automatic_backups": removed}
    elif args.command == "backup":
        if not config.database.is_file():
            raise FileNotFoundError("Commercial database does not exist")
        with closing(open_pharmacy_database(config, protected_hospital_paths=args.protect_hospital_dir)) as conn:
            result = {"backup": str(create_backup(conn, config, args.filename))}
    elif args.command == "verify-backup":
        result = inspect_backup(args.file)
    elif args.command == "restore-offline":
        if sys.platform == "win32" and args.confirm_service_stopped:
            from .windows_service_state import require_stopped_service
            require_stopped_service()
        result = restore_offline(args.file, config,
                                 service_stopped=args.confirm_service_stopped,
                                 protected_hospital_paths=args.protect_hospital_dir)
    else:
        raise AssertionError(args.command)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    try:
        sys.exit(run())
    except (ValueError, FileNotFoundError, FileExistsError, RuntimeError) as exc:
        print("COMMERCIAL_PHARMACY_OPERATION_BLOCKED:", str(exc), file=sys.stderr)
        sys.exit(2)
