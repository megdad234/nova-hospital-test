"""Minimal LAN client launcher for the independent pharmacy server."""
from __future__ import annotations
import argparse
import ipaddress
import os
import webbrowser
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
    return 0 if webbrowser.open(url) else 2

if __name__ == "__main__":
    raise SystemExit(main())
