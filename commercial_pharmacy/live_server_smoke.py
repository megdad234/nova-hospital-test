"""Launch an extracted commercial server and verify a live HTTP response.

This is an integration smoke test, NOT POS/database acceptance. The child
process is always terminated and never installed as a Windows service.
"""
from __future__ import annotations
import argparse
import json
import os
import sqlite3
from pathlib import Path
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen

from .launch import prepare
from .runtime_isolation import check_port_free


def run(source_root, data_dir, port=18763, timeout=25.0):
    if not 1 <= port <= 65535:
        raise ValueError("Invalid commercial port")
    if timeout <= 0:
        raise ValueError("Timeout must be positive")
    if not check_port_free(port):
        return {"server_started": False, "http_responded": False,
                "database_verified": False, "pos_verified": False,
                "installer_verified": False, "port": port,
                "error": "port_already_in_use"}
    command, env, cwd = prepare(source_root, data_dir=data_dir, port=port)
    # Never inherit a production hospital database override.
    env.pop("NOVA_HOSPITAL_DATA_DIR", None)
    env["PYTHONNOUSERSITE"] = "1"
    result = {"server_started": False, "http_responded": False,
              "database_verified": False, "pos_verified": False,
              "installer_verified": False, "port": port}
    process = subprocess.Popen(command, cwd=str(cwd), env=env,
                               stdin=subprocess.DEVNULL,
                               stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
    try:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if process.poll() is not None:
                result["error"] = "server_exited_before_http"
                result["exit_code"] = process.returncode
                break
            try:
                with urlopen(f"http://127.0.0.1:{port}/", timeout=1.0) as response:
                    result["http_status"] = response.status
                    if 200 <= response.status < 300:
                        result["server_started"] = True
                        result["http_responded"] = True
                    else:
                        result["error"] = "unexpected_http_status"
                    break
            except (URLError, TimeoutError, OSError):
                time.sleep(0.3)
        else:
            result["error"] = "server_http_timeout"
        if result["http_responded"]:
            # Confirm that the running server initialized its own SQLite database,
            # not merely that a web page answered HTTP 200.
            database = Path(data_dir).resolve() / "commercial_pharmacy.sqlite3"
            if database.is_file():
                try:
                    with sqlite3.connect(f"file:{database.as_posix()}?mode=ro", uri=True, timeout=3) as conn:
                        integrity = conn.execute("PRAGMA quick_check").fetchone()
                        tables = conn.execute(
                            "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
                        ).fetchone()[0]
                    result["database_verified"] = bool(
                        integrity and integrity[0] == "ok" and tables > 0
                    )
                    result["database_table_count"] = tables
                    if not result["database_verified"]:
                        result["database_error"] = "database_not_initialized_or_integrity_failed"
                except sqlite3.Error as exc:
                    result["database_error"] = str(exc)
            else:
                result["database_error"] = "commercial_database_not_created"
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--port", type=int, default=18763)
    parser.add_argument("--timeout", type=float, default=25)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        result = run(args.source_root, args.data_dir, args.port, args.timeout)
    except (OSError, RuntimeError, ValueError, SyntaxError) as exc:
        result = {"server_started": False, "http_responded": False,
                  "database_verified": False, "pos_verified": False,
                  "installer_verified": False, "port": args.port,
                  "error": type(exc).__name__, "detail": str(exc)}
    payload = json.dumps(result, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(payload)
    return 0 if result["http_responded"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
