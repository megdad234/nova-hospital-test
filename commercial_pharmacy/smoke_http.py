"""Opt-in live HTTP smoke test for a separately launched commercial pharmacy server."""
from __future__ import annotations
import argparse
import json
from urllib.request import urlopen
from urllib.error import URLError
from .desktop_client import pharmacy_url

def inspect(host: str, port: int, timeout: float = 3.0):
    url = pharmacy_url(host, port)
    try:
        with urlopen(url, timeout=timeout) as response:
            return {"reachable": True, "http_status": response.status,
                    "url": url, "http_responded": True, "runtime_verified": False}
    except (URLError, TimeoutError, OSError) as exc:
        return {"reachable": False, "url": url, "runtime_verified": False,
                "error": type(exc).__name__}

def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=18763)
    parser.add_argument("--timeout", type=float, default=3.0)
    args = parser.parse_args(argv)
    result = inspect(args.host, args.port, args.timeout)
    print(json.dumps(result))
    return 0 if result.get("http_responded") else 2

if __name__ == "__main__":
    raise SystemExit(main())
