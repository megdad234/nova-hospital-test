"""Fail closed: never publish a NOVA installer advertised as Royal Lab-ready
unless the packaged build contains actual source data and a verified live activation.
This check deliberately rejects the current incomplete migration.
"""
import json,pathlib,sys

def verify(root):
    root=pathlib.Path(root)
    manifest=root/'hospital'/'royallab_live_release_manifest.json'
    if not manifest.is_file():
        raise RuntimeError('ROYALLAB_NOT_READY: no live release manifest; do not distribute as migrated')
    data=json.loads(manifest.read_text(encoding='utf-8'))
    required=('source_catalog_packaged','installer_imports_source_catalog',
              'nova_test_bindings_installed','dropdown_runtime_e2e_passed',
              'clinical_review_policy_verified')
    incomplete=[k for k in required if data.get(k) is not True]
    if incomplete:
        raise RuntimeError('ROYALLAB_NOT_READY: '+', '.join(incomplete))
    if data.get('source_test_count')!=367:
        raise RuntimeError('ROYALLAB_NOT_READY: incomplete Royal Lab source catalog')
    return True

if __name__=='__main__':
    try:verify(pathlib.Path(__file__).resolve().parents[2])
    except (RuntimeError,ValueError,KeyError) as e:
        print(str(e),file=sys.stderr)
        sys.exit(1)
