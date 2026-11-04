"""Source launcher preflight for commercial pharmacy."""
from pathlib import Path

def source_files(root):
    root = Path(root).resolve()
    files = (root / 'pharmacy' / 'app.py', root / 'pharmacy' / 'server_host.py')
    for file in files:
        if not file.is_file():
            raise FileNotFoundError(str(file))
    return files
