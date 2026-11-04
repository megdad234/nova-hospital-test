"""Launch an extracted commercial server and verify a live HTTP response.

This is an integration smoke test, NOT POS/database acceptance. The child
process is always terminated and never installed as a Windows service.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen

from .launch import prepare


def run(source_root, data_dir, port=18763, timeout=25.0):
    if not 1 <= port <= 65535:
        raise ValueError("Invalid commercial port")
    if timeout <= 0:
        raise ValueError("Timeout must be positive")
    command, env, cwd = prepare(source_root, data_dir=data_dir, port=port)
    # Never inherit a production hospital database override.
    env.pop("NOVA_HOSPITAL_DATA_DIR", None)
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
                    result["server_started"] = True
                    result["http_responded"] = True
                    result["http_status"] = response.status
                    break
            except (URLError, TimeoutError, OSError):
                time.sleep(0.3)
        else:
            result["error"] = "server_http_timeout"
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
    result = run(args.source_root, args.data_dir, args.port, args.timeout)
    payload = json.dumps(result, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(payload)
    return 0 if result["http_responded"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
