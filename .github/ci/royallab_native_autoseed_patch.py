"""Initialize original Royal Lab catalogue during NOVA lab schema setup.

This is an additive, idempotent migration; never removes existing orders or
pharmacy data. A missing source file fails explicitly rather than seeding fake tests.
"""
from pathlib import Path
ANCHOR="    c.executescript(SCHEMA)\n    for table in ('hospital_lab_parameters','hospital_lab_lines'):"
INJECT="""    c.executescript(SCHEMA)
    # ROYALLAB_NATIVE_AUTOSEED: preserve original source tests and all ranges.
    from hospital.royallab_native_catalog_store import install_file as _royallab_install
    import sys as _royallab_sys
    from pathlib import Path
    _royallab_roots = (
        Path(__file__).resolve().parent / 'royallab_source',
        Path(getattr(_royallab_sys, '_MEIPASS', '')) / 'hospital' / 'royallab_source',
        Path(_royallab_sys.executable).resolve().parent / 'hospital' / 'royallab_source',
    )
    _royallab_path = next((p / 'nova_lab_library.json' for p in _royallab_roots
                           if (p / 'nova_lab_library.json').is_file()), None)
    if _royallab_path is not None:
        _royallab_install(c, _royallab_path)
    for table in ('hospital_lab_parameters','hospital_lab_lines'):"""
def patch(source):
 if source.count(ANCHOR)!=1:raise ValueError("Expected NOVA04 lab schema initialization anchor")
 if "ROYALLAB_NATIVE_AUTOSEED" in source:raise ValueError("Already patched")
 return source.replace(ANCHOR,INJECT,1)
def apply(root):
 p=Path(root)/'hospital/lab.py'
 p.write_text(patch(p.read_text(encoding='utf-8')),encoding='utf-8')
if __name__=='__main__':apply(Path(__file__).resolve().parents[2])
