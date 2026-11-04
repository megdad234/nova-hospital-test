"""Audit extracted pharmacy server configuration before packaging."""
from pathlib import Path
import json
import ast
import os

ROOT = Path(os.environ.get("NOVA_EXTRACTION_ROOT", Path(__file__).resolve().parents[2])).resolve()

def inspect(root=ROOT):
    findings = {}
    for name in ("server_host.py", "app.py"):
        file = root / "pharmacy" / name
        if not file.is_file():
            findings[name] = {"present": False}
            continue
        source = file.read_text(encoding="utf-8")
        try:
            ast.parse(source, filename=str(file))
            syntax_valid = True
        except SyntaxError:
            syntax_valid = False
        findings[name] = {
            "present": True,
            "syntax_valid": syntax_valid,
            "commercial_port_override": "NOVA_COMMERCIAL_PORT" in source,
            "commercial_database_override": "NOVA_COMMERCIAL_DATA_DIR" in source,
        }
    return {"runtime_verified": False, "source": findings,
            "port_override_present": findings.get("server_host.py", {}).get("commercial_port_override", False),
            "database_override_present": findings.get("app.py", {}).get("commercial_database_override", False)}

if __name__ == "__main__":
    result = inspect()
    output = ROOT / "commercial_pharmacy_stage" / "SERVER_ENTRYPOINT_AUDIT.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result))
