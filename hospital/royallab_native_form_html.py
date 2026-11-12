"""Render original Royal Lab test forms, without matching old NOVA tests.

HTML fragment is safe for authenticated lab UI; no network or patient data.
"""
from html import escape
import re

def _e(value):
    return escape("" if value is None else str(value), quote=True)

def _visible(value):
    # Preserve source identifiers in data attributes, not in visible clinical labels.
    return _e(re.sub(r'\bROYAL[\s_-]*\d+\b', '', '' if value is None else str(value), flags=re.I).strip())

def render_form(test):
    if not isinstance(test, dict) or not isinstance(test.get("fields"), list):
        raise ValueError("Royal Lab native test form required")
    rows = []
    for field in test["fields"]:
        key = field.get("source_format_id")
        kind = field.get("kind")
        if key is None:
            rows.append('<div class="royal-field royal-review">حقل غير مكتمل: '+_visible(field.get("label"))+'</div>')
            continue
        label = _visible(field.get("label"))
        numeric_step = "1" if "IntegerResultFormat" in (field.get("types") or []) else "any"
        unit = _e(field.get("unit"))
        name = _e(key)
        common = ' name="royal_'+name+'" data-source-format-id="'+name+'"'
        if kind in ("select", "select_or_number", "select_or_text"):
            options = ['<option value="">— اختر النتيجة —</option>']
            for opt in field.get("options", []):
                if opt.get("active") in (False, 0, "False", "false", "0"):
                    continue
                options.append('<option value="'+_e(opt.get("id"))+'">'+_visible(opt.get("label"))+'</option>')
            select = '<select'+common+'>'+''.join(options)+'</select>'
            if kind == "select_or_number":
                select += '<input type="number" step="'+numeric_step+'" data-alternative-for="'+name+'" placeholder="أو قيمة رقمية">'
            if kind == "select_or_text":
                select += '<input type="text" data-alternative-for="'+name+'" placeholder="أو نص">'
            control = select
        elif kind == "number":
            control = '<input type="number" step="'+numeric_step+'"'+common+'>'
        elif kind == "text":
            control = '<input type="text"'+common+'>'
        else:
            control = '<span class="royal-review">يتطلب مراجعة نوع الحقل</span>'
        rows.append('<label class="royal-field"><span>'+label+'</span>'+control+
                    ('<small>'+unit+'</small>' if unit else '')+'</label>')
    return '<section class="royal-native-form" dir="rtl" data-source-test-id="'+_e(test.get("source_test_id"))+'">'+\
           '<h2>'+_visible(test.get("name"))+'</h2>'+''.join(rows)+'</section>'
