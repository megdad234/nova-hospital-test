"""Strict isolated typed Royal Lab result widget patch for NOVA hospital UI.

Only changes input rendering in resultTable; never alters save/publish handlers.
No source metadata => original text input remains unchanged.
"""
from pathlib import Path
ANCHOR='''<input data-line="${x.id}" value="${esc(x.value)}" maxlength="4000" aria-label="نتيجة ${esc(x.name)}" autocomplete="off" dir="auto">'''
REPLACEMENT='''${royalLabInput(x)}'''
HELPER='''function royalLabInput(x){const m=x.royal_lab_field;if(!m||!['number','text','select','select_or_text','select_or_number'].includes(m.kind))return `<input data-line="${x.id}" value="${esc(x.value)}" maxlength="4000" aria-label="نتيجة ${esc(x.name)}" autocomplete="off" dir="auto">`;const value=String(x.value??'');const opts=Array.isArray(m.options)?m.options.filter(v=>typeof v==='string'&&v.trim()):[];const label=esc(x.name);if(m.kind==='select'&&opts.length){const values=['',...opts];if(value&&!values.includes(value))values.push(value);return `<select data-line="${x.id}" aria-label="نتيجة ${label}">${values.map(v=>`<option value="${esc(v)}" ${v===value?'selected':''}>${esc(v||'— اختر —')}</option>`).join('')}</select>`}if((m.kind==='select_or_text'||m.kind==='select_or_number')&&opts.length){const listId='royal-options-'+Number(x.id);return `<input data-line="${x.id}" list="${listId}" value="${esc(value)}" maxlength="4000" aria-label="نتيجة ${label}" autocomplete="off" dir="auto"><datalist id="${listId}">${opts.map(v=>`<option value="${esc(v)}"></option>`).join('')}</datalist>`}return `<input data-line="${x.id}" ${m.kind==='number'?'inputmode="decimal"':''} value="${esc(value)}" maxlength="4000" aria-label="نتيجة ${label}" autocomplete="off" dir="auto">`}
'''
def patch(source):
    if source.count(ANCHOR)!=1:raise ValueError("Expected original NOVA result input anchor exactly once")
    if 'function royalLabInput(' in source:raise ValueError("Typed widget already installed")
    return HELPER+source.replace(ANCHOR,REPLACEMENT,1)
def apply(root):
    p=Path(root)/'hospital/static/app.js'
    p.write_text(patch(p.read_text(encoding='utf-8')),encoding='utf-8')
if __name__=='__main__':apply(Path(__file__).resolve().parents[2])
