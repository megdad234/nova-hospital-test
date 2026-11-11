"""Surgical lab-print-only patch for extracted NOVA app.js.

Never changes receipt printing, billing, report API or database.
Must run after source extraction and other app.js modifications.
"""
from pathlib import Path

def patch_lab_print_js(source):
    anchor="${d.partial?'<p class=\"small\">تقرير جزئي — توجد فحوصات أخرى لم تُجهز للطباعة.</p>':''}"
    if source.count(anchor)!=1:
        raise RuntimeError("Expected exactly one lab-only partial-report message")
    return source.replace(anchor,"",1)

def apply(root):
    file=Path(root)/"hospital/static/app.js"
    before=file.read_text(encoding="utf-8")
    after=patch_lab_print_js(before)
    file.write_text(after,encoding="utf-8")
    return file

if __name__=="__main__":
    apply(Path(__file__).resolve().parents[2])
