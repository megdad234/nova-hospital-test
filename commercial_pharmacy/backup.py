"""Standalone SQLite backup and restore primitives.

Uses SQLite's online backup API, never copies live database files. Restore
requires an explicit offline/maintenance-mode decision by the caller and a
separate destination; it does not overwrite a running pharmacy database.
"""
from __future__ import annotations
from pathlib import Path
from contextlib import closing
import os
import sqlite3
import tempfile
from .runtime_isolation import CommercialPaths, backup_destination, validate_paths
from .database import verify_pharmacy_database

def create_backup(connection: sqlite3.Connection, config: CommercialPaths, filename: str):
    validate_paths(config)
    verify_pharmacy_database(connection, config)
    if not config.backups.is_dir():
        raise FileNotFoundError("Commercial backup directory missing")
    target = backup_destination(config, filename)
    if target.suffix.lower() not in (".sqlite3", ".sqlite", ".db"):
        raise ValueError("Backup must be a SQLite database")
    if target.is_symlink() or target.exists():
        raise FileExistsError("Refusing to overwrite an existing backup")
    fd, temporary = tempfile.mkstemp(prefix=".backup-", suffix=".sqlite3", dir=config.backups)
    os.close(fd)
    try:
        with closing(sqlite3.connect(temporary)) as output:
            connection.backup(output)
            check = output.execute("PRAGMA integrity_check").fetchone()[0]
            if check != "ok":
                raise RuntimeError("Backup integrity check failed: " + str(check))
        os.replace(temporary, target)
        return target
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)

def inspect_backup(path: Path):
    if not path.is_file():
        raise FileNotFoundError(str(path))
    uri = path.resolve().as_uri() + "?mode=ro"
    with closing(sqlite3.connect(uri, uri=True)) as conn:
        result = conn.execute("PRAGMA integrity_check").fetchone()[0]
        if result != "ok":
            raise ValueError("Invalid SQLite backup: " + str(result))
        tables = [row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    return {"valid": True, "tables": tables, "bytes": path.stat().st_size}

def stage_restore(backup: Path, config: CommercialPaths):
    """Validate and copy backup into a staging directory, not the live DB."""
    validate_paths(config)
    inspect_backup(backup)
    config.backups.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix="restore-staged-", suffix=".sqlite3", dir=config.backups)
    os.close(fd)
    candidate = Path(name)
    try:
        with closing(sqlite3.connect(backup.resolve().as_uri() + "?mode=ro", uri=True)) as src:
            with closing(sqlite3.connect(candidate)) as dst:
                src.backup(dst)
        inspect_backup(candidate)
        return candidate
    except Exception:
        candidate.unlink(missing_ok=True)
        raise
