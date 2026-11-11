"""Standalone, read-only HTML form preview for a staged Royal Lab test.
Never posts data, never embeds patient identifiers, never enables clinical use.
"""
import html,json
from royallab_catalog_preview import test_form

def render_preview(conn,batch_id,source_test_id):
    form=test_form(conn,batch_id,source_test_id)
    esc=lambda x:html.escape(str(x if x is not None else ""),quote=True)
    pieces=['<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8">',
      '<meta name="viewport" content="width=device-width,initial-scale=1">',
      '<title>Royal Lab — معاينة فقط</title>',
      '<style>body{font-family:Tahoma,Arial,sans-serif;background:#f5f8fc;color:#172c43;margin:0;padding:24px}main{max-width:920px;margin:auto;background:white;border-radius:16px;padding:24px;box-shadow:0 4px 22px #16345515}h1{font-size:22px}label{display:block;margin:16px 0 6px;font-weight:bold}input,select,textarea{width:100%;box-sizing:border-box;padding:10px;border:1px solid #a9b7c7;border-radius:8px;font:inherit}small{color:#53687d}.warning{background:#fff2d9;padding:12px;border-radius:8px}.field{border-bottom:1px solid #e6ebf0;padding:12px 0}.unit{display:inline-block;margin:5px;color:#43566b}</style>',
      '</head><body><main><h1>معاينة: '+esc(form["name"])+'</h1>',
      '<p class="warning">معاينة فنية فقط — غير معتمد للاستخدام السريري ولا يحفظ نتائج المرضى.</p>']
    for i,f in enumerate(form["fields"]):
        kind=f.get("kind","unknown")
        label=esc(f.get("label") or "حقل نتيجة")
        fid="field_"+str(i)
        pieces.append('<div class="field"><label for="'+fid+'">'+label+'</label>')
        opts=f.get("options") or []
        if kind=="select":
            pieces.append('<select id="'+fid+'" disabled><option value="">اختر النتيجة</option>')
            for o in opts:pieces.append('<option>'+esc(o.get("label"))+'</option>')
            pieces.append('</select>')
        elif kind in ("select_or_text","select_or_number"):
            lid="choices_"+str(i)
            pieces.append('<input id="'+fid+'" list="'+lid+'" disabled placeholder="اختر أو اكتب"><datalist id="'+lid+'">')
            for o in opts:pieces.append('<option value="'+esc(o.get("label"))+'"></option>')
            pieces.append('</datalist>')
        elif kind=="number":
            pieces.append('<input id="'+fid+'" type="number" step="any" disabled>')
        elif kind=="text":
            pieces.append('<input id="'+fid+'" type="text" disabled>')
        else:
            pieces.append('<p class="warning">نوع النتيجة يحتاج مراجعة المصدر قبل تفعيل الإدخال.</p>')
        if f.get("unit"):pieces.append('<small class="unit">الوحدة: '+esc(f["unit"])+'</small>')
        pieces.append('</div>')
    pieces.append('<p><small>لا توجد أزرار حفظ أو إرسال في هذه المعاينة.</small></p></main></body></html>')
    return "".join(pieces)
