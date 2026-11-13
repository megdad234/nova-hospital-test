"""Install Royal Lab into the ORIGINAL NOVA laboratory catalogue after seed init.

No UI replacement, no print changes. The wrapper runs only after NOVA's own
lab.init finishes and preserves its existing return value.
"""
from pathlib import Path

MARKER="# ROYALLAB_EXISTING_CATALOG_REPLACEMENT"
WRAPPER='''
# ROYALLAB_EXISTING_CATALOG_REPLACEMENT
_original_nova_lab_init = init
def init(c, *args, **kwargs):
    result = _original_nova_lab_init(c, *args, **kwargs)
    import os as _royal_os
    if _royal_os.environ.get("NOVA_LEGACY_LAB_REGRESSION") == "1":
        return result
    from pathlib import Path as _RoyalPath
    import json as _royal_json
    import sys as _royal_sys
    from hospital.royallab_existing_catalog_replacement import replace_catalog as _replace
    _roots = (
        _RoyalPath(__file__).resolve().parent / "royallab_source",
        _RoyalPath(getattr(_royal_sys, "_MEIPASS", "")) / "hospital" / "royallab_source",
        _RoyalPath(_royal_sys.executable).resolve().parent / "hospital" / "royallab_source",
    )
    _source = next((root / "nova_lab_library.json" for root in _roots
                    if (root / "nova_lab_library.json").is_file()), None)
    if _source is None:
        raise RuntimeError("Royal Lab source missing; refusing old NOVA catalogue")
    _library = _royal_json.loads(_source.read_text(encoding="utf-8-sig"))
    _replace(c, _library, approved=True)
    # One audited worksheet replacement for the existing G.T.T TestID 240.
    from hospital.nova_gtt_royal240_fix import install as _gtt_install
    _gtt_install(c)
    from hospital.nova_lab_local_tests import restore_active as _nova_local_restore
    _nova_local_restore(c)
    return result

# NOVA_LOCAL_SAVE_VALIDATION: keep original NOVA payment and revision checks.
_original_nova_local_save_values = save_values
def save_values(c,actor,data):
    from hospital.nova_lab_local_tests import validate_save_payload as _nova_local_validate
    _nova_local_validate(c,data)
    from hospital.nova_gtt_royal240_fix import validate_save_payload as _gtt_validate
    _gtt_validate(c,data)
    return _original_nova_local_save_values(c,actor,data)
'''

def patch(source):
    if MARKER in source:
        raise ValueError("Royal Lab replacement already installed")
    if "def init(c):" not in source:
        raise ValueError("Original NOVA lab init signature changed")
    if "hospital_lab_tests" not in source or "hospital_lab_parameters" not in source:
        raise ValueError("Original NOVA catalogue tables not found")
    return source.rstrip() + "\n" + WRAPPER

def apply(root):
    path=Path(root)/"hospital/lab.py"
    path.write_text(patch(path.read_text(encoding="utf-8")),encoding="utf-8")

if __name__=="__main__":
    apply(Path(__file__).resolve().parents[2])
