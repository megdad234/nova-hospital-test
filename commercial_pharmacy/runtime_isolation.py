"""Runtime isolation primitives for NOVA Commercial Pharmacy.

No import-time side effects. Does not open or modify a hospital database.
The pharmacy server must explicitly adopt these paths and settings before
the application can be considered standalone.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import json
import os
import re
import socket
import sys

PRODUCT = "NOVACommercialPharmacy"
SERVICE_NAME = "NOVACommercialPharmacyServer"
DATABASE_NAME = "commercial_pharmacy.sqlite3"
PORT = 18763
WINDOWS_APP_ID = "NOVACommercialPharmacy.Standalone"
_SAFE_NAME = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,127}$")

@dataclass(frozen=True)
class CommercialPaths:
    data: Path
    database: Path
    backups: Path
    logs: Path
    config: Path

def _base_data_dir(environ=None):
    env = os.environ if environ is None else environ
    if env.get("NOVA_COMMERCIAL_DATA_DIR"):
        return Path(env["NOVA_COMMERCIAL_DATA_DIR"]).expanduser().resolve()
    if os.name == "nt":
        return (Path(env.get("PROGRAMDATA") or r"C:\ProgramData") / PRODUCT).resolve()
    return (Path(env.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")) / PRODUCT).resolve()

def paths(environ=None):
    base = _base_data_dir(environ)
    return CommercialPaths(base, base / DATABASE_NAME, base / "backups",
                           base / "logs", base / "commercial_config.json")

def validate_paths(value: CommercialPaths, forbidden_paths=()):
    db = value.database.resolve()
    if db.parent != value.data.resolve() or db.name != DATABASE_NAME:
        raise ValueError("Commercial database must remain in its own data directory")
    for forbidden in forbidden_paths:
        f = Path(forbidden).resolve()
        if value.data.resolve() == f or f in value.data.resolve().parents or value.data.resolve() in f.parents:
            raise ValueError("Commercial data directory overlaps a protected NOVA Hospital path")
    return value

def initialize_directories(value: CommercialPaths):
    validate_paths(value)
    for folder in (value.data, value.backups, value.logs):
        folder.mkdir(parents=True, exist_ok=True)
    return value

def choose_port(environ=None):
    env = os.environ if environ is None else environ
    port = int(env.get("NOVA_COMMERCIAL_PORT", PORT))
    if not 1024 <= port <= 65535 or port == 10080:
        raise ValueError("Invalid or hospital-reserved commercial port")
    return port

def check_port_free(port, host="127.0.0.1"):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        return sock.connect_ex((host, port)) != 0

def safe_backup_filename(name):
    if name in {".", ".."} or not _SAFE_NAME.fullmatch(name):
        raise ValueError("Unsafe backup filename")
    return name

def backup_destination(value: CommercialPaths, filename):
    return value.backups / safe_backup_filename(filename)

def export_runtime_config(value: CommercialPaths, environ=None):
    return {
        "product": PRODUCT, "service_name": SERVICE_NAME,
        "database_path": str(value.database),
        "backup_directory": str(value.backups),
        "log_directory": str(value.logs),
        "port": choose_port(environ),
        "hospital_database_enabled": False,
        "hospital_service_enabled": False,
    }

def write_runtime_config(value: CommercialPaths, environ=None):
    initialize_directories(value)
    config = export_runtime_config(value, environ)
    temporary = value.config.with_suffix(".tmp")
    temporary.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(value.config)
    return config

if __name__ == "__main__":
    p = paths()
    print(json.dumps(export_runtime_config(validate_paths(p)), indent=2))
