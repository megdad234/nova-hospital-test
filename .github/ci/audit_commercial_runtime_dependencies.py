"""Inventory actual extracted pharmacy imports and local dependencies.

This is evidence for packaging, not proof of an installable runtime.
"""
from __future__ import annotations
import ast
import json
import sys
from pathlib import Path

def inspect(root: Path):
    root = Path(root)
    pharmacy = root / "pharmacy"
    if not pharmacy.is_dir():
        raise FileNotFoundError(pharmacy)
    modules = set()
    local = set()
    errors = []
    for file in sorted(pharmacy.rglob("*.py")):
        if "__pycache__" in file.parts:
            continue
        try:
            tree = ast.parse(file.read_text(encoding="utf-8"), filename=str(file))
        except (SyntaxError, UnicodeError) as exc:
            errors.append({"file": str(file.relative_to(root)), "error": str(exc)})
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    local.add(node.module or "<relative>")
                elif node.module:
                    modules.add(node.module.split(".")[0])
    stdlib = set(sys.stdlib_module_names)
    third_party = sorted(modules - stdlib - {"__future__"})
    possible_local = []
    external = []
    for name in third_party:
        if (root / (name + ".py")).exists() or (root / name).is_dir() or (pharmacy / (name + ".py")).exists() or (pharmacy / name).is_dir():
            possible_local.append(name)
        else:
            external.append(name)
    return {"source_files": len(list(pharmacy.rglob("*.py"))),
            "stdlib_imports": sorted(modules & stdlib),
            "external_import_candidates": external,
            "local_import_candidates": possible_local,
            "relative_imports": sorted(local),
            "syntax_errors": errors,
            "runtime_installed": False,
            "windows_installer_verified": False}

def main():
    root = Path.cwd()
    report = inspect(root)
    target = root / "commercial_pharmacy_stage" / "RUNTIME_DEPENDENCIES.json"
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"source_files": report["source_files"],
                      "external_import_candidates": report["external_import_candidates"],
                      "syntax_errors": report["syntax_errors"]}))
    return 2 if report["syntax_errors"] else 0

if __name__ == "__main__":
    raise SystemExit(main())
