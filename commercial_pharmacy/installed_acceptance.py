"""Consolidated acceptance evidence for a separately installed retail pharmacy.

This is deliberately read-only: never submits a sale or alters hospital data.
"""
import argparse
import json
import sqlite3
from pathlib import Path
from urllib.request import urlopen
from urllib.error import HTTPError, URLError

def audit(root, data, port):
    root, data = Path(root).resolve(), Path(data).resolve()
    required = [
        "NOVACommercialPharmacy.exe",
        "NOVACommercialPharmacyServer.exe",
        "runtime/python.exe",
        "pharmacy/app.py",
        "pharmacy/server_host.py",
        "pharmacy/static/app.js",
        "commercial_pharmacy/launch.py",
    ]
    files = {name: (root / name).is_file() for name in required}
    database = data / "commercial_pharmacy.sqlite3"
    evidence = {"installed_files": files, "database_exists": database.is_file(),
                "hospital_reference_absent": not (root / "hospital_reference").exists(),
                "http": {}, "database": {}, "business_workflows_verified": False,
                "thermal_printer_verified": False, "windows_service_verified": False}
    if database.is_file():
        with sqlite3.connect(database) as connection:
            evidence["database"]["integrity"] = connection.execute("PRAGMA quick_check").fetchone()[0]
            evidence["database"]["tables"] = connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
            evidence["database"]["tables"] = [item[0] for item in evidence["database"]["tables"]]
    for route in ("/", "/static/app.js"):
        try:
            with urlopen("http://127.0.0.1:%d%s" % (port, route), timeout=5) as response:
                evidence["http"][route] = {"status": response.status, "bytes": len(response.read())}
        except (HTTPError, URLError, TimeoutError) as error:
            evidence["http"][route] = {"error": str(error)}
    evidence["passed"] = (all(files.values()) and evidence["hospital_reference_absent"]
                          and evidence["database"].get("integrity") == "ok"
                          and len(evidence["database"].get("tables", [])) > 0
                          and evidence["http"].get("/", {}).get("status") == 200
                          and evidence["http"].get("/static/app.js", {}).get("status") == 200)
    return evidence

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--data", required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    evidence = audit(args.root, args.data, args.port)
    Path(args.output).write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in evidence.items() if key != "database"}, indent=2))
    return 0 if evidence["passed"] else 2

if __name__ == "__main__":
    raise SystemExit(main())
