#!/usr/bin/env python3
"""Windows-only lifecycle fix for synthetic SQLite TEST fixtures.

Python's sqlite3.Connection context manager commits/rolls back but does NOT
close the connection. On Windows that leaves a file handle and makes the
fixture's temporary directory cleanup fail (WinError 32). Replace test-only
context managers with commit-then-close. Never modifies pharmacy/application
source, production data, or actual hospital records.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
TARGETS = {
    "tests/test_unified_backup.py": 10,
    "tests/test_update_and_brand.py": 3,
}
for filename, expected in TARGETS.items():
    path = ROOT / filename
    source = path.read_text(encoding="utf-8")
    if "from contextlib import closing" in source:
        raise SystemExit(f"Test fixture already changed: {filename}")
    patched = source.replace(
        "import sqlite3\n", "import sqlite3\nfrom contextlib import closing\n", 1
    )
    # Both the DB transaction context manager AND closing() must run, in order:
    # c.__exit__ commits, then closing.__exit__ releases the Windows file handle.
    patched, count = re.subn(
        r"with sqlite3\.connect\(([^\n]+?)\) as c:",
        r"with closing(sqlite3.connect(\1)) as c, c:",
        patched,
    )
    if count != expected:
        raise SystemExit(
            f"Unexpected SQLite fixture count in {filename}: {count}, want {expected}"
        )
    if filename == "tests/test_unified_backup.py":
        exact = "with app.db_connect() as c:"
        if patched.count(exact) != 1:
            raise SystemExit("Unexpected app fixture count")
        patched = patched.replace(exact, "with closing(app.db_connect()) as c, c:")
    compile(patched, filename, "exec")
    path.write_text(patched, encoding="utf-8")
    print(f"WIN_TEST_SQLITE_CONNECTIONS_CLOSED: {filename} ({count} scopes)")
