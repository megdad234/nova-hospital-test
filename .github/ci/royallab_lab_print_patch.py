"""Surgical lab-print-only patch for extracted NOVA app.js.

Never changes receipt printing, billing, report API or database.
Must run after source extraction and other app.js modifications.
"""
from pathlib import Path

def patch_lab_print_js(source):
    anchor="${d.partial?'<p class=\"small\">تقرير جزئي — توجد فحوصات أخرى لم تُجهز للطباعة.</p>':''}"
    if source.count(anchor)>1:
        raise RuntimeError("Duplicate lab-only partial-report message")
    # Earlier NOVA build stages may already remove the partial-report notice.
    # Accept that state only if no alternate partial notice remains in printReport.
    if anchor not in source:
        segment=source[source.find("async function printReport("):source.find("async function printReport(")+6000]
        if not segment or "تقرير جزئي" in segment or "d.partial?" in segment:
            raise RuntimeError("Unexpected alternate lab partial-report notice")
    # Preserve the existing report endpoint, approval filter, and print window.
    # Only add visual section headings for NOVA Batch04 section_name snapshots.
    old="(i.lines||[]).filter(x=>String(x.value??'').trim()!=='').map(x=>"
    new="(i.lines||[]).filter(x=>String(x.value??'').trim()!=='').flatMap((x,idx,visible)=>{const group=String(x.section_name||'').trim();const previous=idx?String(visible[idx-1].section_name||'').trim():'';return [...(group&&group!==previous?[`<tr class=\"lab-print-group\"><th colspan=\"4\">${esc(group)}</th></tr>`]:[]),"
    if source.count(old)!=1:raise RuntimeError("Expected exactly one lab-only result row mapping")
    # Match only the end of the exact result row template, not any other table.
    start=source.index(old)
    end_marker='</tr>`))}</section>'
    end=source.find(end_marker,start)
    if end<0:raise RuntimeError("Lab report row end anchor missing")
    source=source[:start]+source[start:].replace(old,new,1)
    start=source.index(new)
    end=source.find(end_marker,start)
    if end<0:raise RuntimeError("Lab report mapping closure missing")
    source=source[:end]+source[end:].replace(end_marker,'</tr>`]}))}</section>',1)
    return source.replace(anchor,"",1)

def apply(root):
    file=Path(root)/"hospital/static/app.js"
    before=file.read_text(encoding="utf-8")
    after=patch_lab_print_js(before)
    file.write_text(after,encoding="utf-8")
    return file

if __name__=="__main__":
    apply(Path(__file__).resolve().parents[2])
