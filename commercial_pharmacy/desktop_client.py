"""Minimal LAN client launcher for the independent pharmacy server."""
from __future__ import annotations
import argparse
import ipaddress
import os
import webbrowser
import socket
import subprocess
import sys
import time
from pathlib import Path
from .runtime_isolation import choose_port

def pharmacy_url(host="127.0.0.1", port=18763):
    if not host or any(char in host for char in "/\\:@?# "):
        raise ValueError("Invalid pharmacy server address")
    if host.replace(".", "").isdigit() and host.count(".") != 3:
        raise ValueError("Malformed numeric server address")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        if host.replace(".", "").isdigit():
            raise ValueError("Invalid IPv4 address")
        if not all(label and label.replace("-", "").isalnum()
                   for label in host.split(".")):
            raise ValueError("Invalid pharmacy server hostname")
    else:
        if address.version != 4:
            raise ValueError("Use an IPv4 LAN address")
    selected = choose_port({"NOVA_COMMERCIAL_PORT": str(port)})
    return f"http://{host}:{selected}/"

def _ready(host, port):
    try:
        with socket.create_connection((host, port), timeout=0.5):
            return True
    except OSError:
        return False

def _start_local_server(port):
    # Fallback only for the local server; LAN clients must never spawn one.
    root = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent
    python = root / "runtime" / "python.exe"
    entry = root / "pharmacy" / "server_host.py"
    if not python.is_file() or not entry.is_file():
        return False
    env = dict(os.environ)
    env["NOVA_COMMERCIAL_PORT"] = str(port)
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "DETACHED_PROCESS", 0)
    subprocess.Popen([str(python), str(entry)], cwd=str(root), env=env,
                     creationflags=flags, stdin=subprocess.DEVNULL,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     close_fds=True)
    return True

def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=os.environ.get("NOVA_COMMERCIAL_SERVER_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("NOVA_COMMERCIAL_PORT", "18763")))
    parser.add_argument("--print-url", action="store_true")
    args = parser.parse_args(argv)
    url = pharmacy_url(args.host, args.port)
    if args.print_url:
        print(url)
        return 0
    if not args.print_url and args.host == "127.0.0.1" and not _ready(args.host, args.port):
        _start_local_server(args.port)
        for _ in range(60):
            if _ready(args.host, args.port):
                break
            time.sleep(0.5)
    if not _ready(args.host, args.port):
        print("NOVA Commercial Pharmacy server is not ready", file=sys.stderr)
        return 3
    return 0 if webbrowser.open(url) else 2

if __name__ == "__main__":
    raise SystemExit(main())
