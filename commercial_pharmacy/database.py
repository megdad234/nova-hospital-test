"""Strict pharmacy-only SQL database access guard.

Integrate this factory into pharmacy startup before enabling a standalone
release. No hospital DB migration or copying is performed.
"""
from __future__ import annotations
from pathlib import Path
import sqlite3
from .runtime_isolation import CommercialPaths, DATABASE_NAME, validate_paths

def open_pharmacy_database(config: CommercialPaths, *, protected_hospital_paths=(),
                           timeout=30.0):
    validate_paths(config, forbidden_paths=protected_hospital_paths)
    db = config.database.resolve()
    if db.name != DATABASE_NAME or db.parent != config.data.resolve():
        raise ValueError("Refusing to connect to a noncommercial database")
    if not config.data.is_dir():
        raise FileNotFoundError("Commercial data directory not initialized")
    # A SQLite URI in mode=rwc creates only the dedicated pharmacy database.
    connection = sqlite3.connect(db.as_uri() + "?mode=rwc", uri=True, timeout=timeout)
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 30000")
    connection.execute("PRAGMA journal_mode = WAL")
    verify_pharmacy_database(connection, config)
    return connection

def verify_pharmacy_database(connection, config: CommercialPaths):
    actual = connection.execute("PRAGMA database_list").fetchall()
    main = next((row[2] for row in actual if row[1] == "main"), None)
    if not main or Path(main).resolve() != config.database.resolve():
        raise RuntimeError("Connected SQLite database is not the commercial pharmacy database")
    return True
