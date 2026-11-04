"""Offline-only commercial pharmacy restore with rollback.

The caller must stop the pharmacy Windows service before invoking this module.
This routine refuses to touch any database outside the commercial data root.
"""
from __future__ import annotations
from contextlib import closing
from pathlib import Path
import os
import sqlite3
import time
from .backup import inspect_backup, stage_restore
from .runtime_isolation import CommercialPaths, validate_paths

def restore_offline(backup: Path, config: CommercialPaths, *, service_stopped: bool,
                    protected_hospital_paths=()):
    validate_paths(config, forbidden_paths=protected_hospital_paths)
    if not service_stopped:
        raise RuntimeError("Stop commercial pharmacy service before restoring")
    if not backup.is_file():
        raise FileNotFoundError(str(backup))
    if backup.is_symlink() or backup.resolve().parent != config.backups.resolve():
        raise ValueError("Restore input must be a pharmacy-owned backup file")
    db = config.database.resolve()
    if db.parent != config.data.resolve():
        raise ValueError("Refusing to restore outside commercial pharmacy directory")
    # Check source integrity before any live-database modification.
    inspect_backup(backup)
    if db.exists():
        with closing(sqlite3.connect(db.as_uri() + "?mode=ro", uri=True, timeout=0.1)) as conn:
            result = conn.execute("PRAGMA quick_check").fetchone()[0]
            if result != "ok":
                raise ValueError("Existing commercial database failed quick_check: " + str(result))
    # A stopped application can leave WAL sidecars. Checkpoint them only
    # after the caller confirms the service is stopped, then verify removal.
    if db.exists():
        with closing(sqlite3.connect(db, timeout=2.0)) as checkpoint:
            checkpoint.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    if any(Path(str(db) + suffix).exists() for suffix in ("-wal", "-shm")):
        raise RuntimeError("Database WAL sidecars remain; restore requires exclusive access")
    # A successful SQLite connect/checkpoint does not prove the Windows service
    # is stopped. The caller must separately verify that service state.
    staged = stage_restore(backup, config)
    rollback = config.backups / ("pre-restore-" + str(time.time_ns()) + ".sqlite3")
    if rollback.exists():
        staged.unlink(missing_ok=True)
        raise FileExistsError(str(rollback))
    try:
        if db.exists():
            # Preserve the previous database as a rollback snapshot.
            os.replace(db, rollback)
        try:
            os.replace(staged, db)
        except Exception:
            if rollback.exists() and not db.exists():
                os.replace(rollback, db)
            raise
        return {"database": str(db), "rollback": str(rollback) if rollback.exists() else None}
    finally:
        staged.unlink(missing_ok=True)
