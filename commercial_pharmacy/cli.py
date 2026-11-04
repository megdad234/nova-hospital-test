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
            from .database import verify_pharmacy_database
            with closing(open_pharmacy_database(config, protected_hospital_paths=args.protect_hospital_dir)) as conn:
                verify_pharmacy_database(conn, config)
                result["database_integrity"] = conn.execute("PRAGMA integrity_check").fetchone()[0]
    elif args.command == "initialize":
        result = write_runtime_config(config)
    elif args.command == "check-database":
        if not config.database.is_file():
            raise FileNotFoundError("Commercial database does not exist")
        from .database import verify_pharmacy_database
        with closing(open_pharmacy_database(config, protected_hospital_paths=args.protect_hospital_dir)) as conn:
            verify_pharmacy_database(conn, config)
            result = {"integrity": conn.execute("PRAGMA integrity_check").fetchone()[0]}
    elif args.command == "backup":
        if not config.database.is_file():
            raise FileNotFoundError("Commercial database does not exist")
        with closing(open_pharmacy_database(config, protected_hospital_paths=args.protect_hospital_dir)) as conn:
            result = {"backup": str(create_backup(conn, config, args.filename))}
    elif args.command == "verify-backup":
        result = inspect_backup(args.file)
    elif args.command == "restore-offline":
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
