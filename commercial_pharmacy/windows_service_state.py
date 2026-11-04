"""Query only the dedicated commercial pharmacy Windows service."""
from __future__ import annotations
import re
import subprocess
import sys

SERVICE_NAME = "NOVACommercialPharmacyServer"

def require_stopped_service():
    if sys.platform != "win32":
        raise RuntimeError("Windows service state check requires Windows")
    result = subprocess.run(["sc.exe", "query", SERVICE_NAME],
                            capture_output=True, text=True, timeout=15, check=False)
    output = result.stdout + "\n" + result.stderr
    if result.returncode != 0:
        if re.search(r"\b1060\b", output):
            return {"service": SERVICE_NAME, "state": "not_installed"}
        raise RuntimeError("Cannot establish commercial pharmacy service state")
    match = re.search(r"STATE\s*:\s*(\d+)\s+([A-Z_]+)", output)
    if not match or match.group(1) != "1" or match.group(2) != "STOPPED":
        raise RuntimeError("Commercial pharmacy service must be STOPPED before restore")
    return {"service": SERVICE_NAME, "state": "stopped"}
