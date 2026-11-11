"""Fail closed until Royal Lab source, import, bindings and real dropdown tests exist.

A manifest is an assertion, not evidence. The gate also verifies the packaged
source files and reproducible test evidence. It never grants clinical approval.
"""
import hashlib,json,pathlib,sys

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
    source=data.get('source_bundle')
    if not isinstance(source,dict):
        raise RuntimeError('ROYALLAB_NOT_READY: source bundle evidence missing')
    for key in ('library','unlinked'):
        entry=source.get(key)
        if not isinstance(entry,dict) or not isinstance(entry.get('path'),str):
            raise RuntimeError('ROYALLAB_NOT_READY: missing '+key+' bundle path')
        rel=pathlib.PurePosixPath(entry['path'])
        if rel.is_absolute() or '..' in rel.parts or not rel.parts or rel.parts[0]!='hospital':
            raise RuntimeError('ROYALLAB_NOT_READY: unsafe '+key+' bundle path')
        path=root.joinpath(*rel.parts)
        if not path.is_file() or not isinstance(entry.get('sha256'),str):
            raise RuntimeError('ROYALLAB_NOT_READY: missing '+key+' bundle bytes or digest')
        if hashlib.sha256(path.read_bytes()).hexdigest()!=entry['sha256']:
            raise RuntimeError('ROYALLAB_NOT_READY: '+key+' bundle digest mismatch')
    from royallab_source_bundle_preflight import verify as source_verify
    counts=source_verify(root.joinpath(*pathlib.PurePosixPath(source['library']['path']).parts),
                         root.joinpath(*pathlib.PurePosixPath(source['unlinked']['path']).parts))
    if counts['tests']!=367 or counts['analytes']!=1245:
        raise RuntimeError('ROYALLAB_NOT_READY: source bundle incomplete')
    evidence=data.get('runtime_evidence')
    if not isinstance(evidence,dict) or evidence.get('passed') is not True:
        raise RuntimeError('ROYALLAB_NOT_READY: runtime test evidence missing')
    if evidence.get('real_installed_windows') is not True or evidence.get('dropdowns_verified') is not True:
        raise RuntimeError('ROYALLAB_NOT_READY: installed Windows dropdowns unverified')
    return True

if __name__=='__main__':
    try:verify(pathlib.Path(__file__).resolve().parents[2])
    except (RuntimeError,ValueError,KeyError,FileNotFoundError,ImportError) as e:
        print(str(e),file=sys.stderr)
        sys.exit(1)
