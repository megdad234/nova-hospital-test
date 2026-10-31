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

# The synthetic concurrency probe also used transaction-only SQLite context
# managers. Close their handles before its TemporaryDirectory is deleted.
probe = ROOT / "concurrency_probe.py"
probe_source = probe.read_text(encoding="utf-8")
probe_expected = "with app.db_connect() as c:"
if probe_source.count(probe_expected) != 2:
    raise SystemExit("Unexpected synthetic concurrency DB context count")
probe_fixed = probe_source.replace(
    "from pathlib import Path\n",
    "from pathlib import Path\nfrom contextlib import closing\n", 1,
).replace(probe_expected, "with closing(app.db_connect()) as c, c:")
if "from contextlib import closing" not in probe_fixed:
    raise SystemExit("Concurrency probe import patch failed")
compile(probe_fixed, str(probe), "exec")
probe.write_text(probe_fixed, encoding="utf-8")
print("WIN_CONCURRENCY_SQLITE_CONNECTIONS_CLOSED: 2 scopes")


# PyInstaller resolves --add-data paths relative to the SPEC directory.
# The original script put its spec in windows/, but passed source paths
# relative to the repository root. Keep the spec at root on the CI runner.
# This changes only the disposable Windows build script, not application code.
build = ROOT / "windows" / "build-windows.ps1"
source = build.read_text(encoding="utf-8")
old = "--specpath windows"
if source.count(old) != 1:
    raise SystemExit("Unexpected PyInstaller spec directory in build script")
fixed = source.replace(old, "--specpath .")
if not (ROOT / "pharmacy" / "static").is_dir():
    raise SystemExit("Pharmacy asset source directory missing")
if not (ROOT / "hospital" / "static").is_dir():
    raise SystemExit("Hospital asset source directory missing")
build.write_text(fixed, encoding="utf-8")
print("WIN_PYINSTALLER_ASSET_ROOT_CORRECTED")
