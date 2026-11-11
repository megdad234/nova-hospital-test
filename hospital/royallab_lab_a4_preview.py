"""Isolated A4 portrait laboratory report HTML preview.

Does not alter NOVA's pharmacy receipt printer or enable clinical publishing.
Only approved lab items supplied by NOVA may be rendered.
"""
from html import escape

def _e(value):
    return escape(str(value if value is not None else ""),quote=True)

def render_lab_a4_preview(report):
    if not isinstance(report,dict):raise ValueError("Report required")
    items=report.get("items")
    if not isinstance(items,list) or not items:raise ValueError("Approved laboratory items required")
    if any(not isinstance(item,dict) or item.get("result_status")!="approved" for item in items):
        raise PermissionError("Only approved laboratory results may be printed")
    patient=report.get("patient") or {}
    order=report.get("order") or {}
    if not isinstance(patient,dict) or not isinstance(order,dict):raise ValueError("Invalid report details")
    rows=[]
    for item in items:
        lines=item.get("lines") or []
        if not isinstance(lines,list):raise ValueError("Invalid laboratory lines")
        section=['<section class="test"><h2>'+_e(item.get("test_name") or item.get("name") or "Laboratory test")+'</h2>']
        section.append('<table><thead><tr><th>البند</th><th>النتيجة</th><th>الوحدة</th><th>المدى المرجعي</th></tr></thead><tbody>')
        for line in lines:
            if not isinstance(line,dict):raise ValueError("Invalid result line")
            section.append("<tr>"+''.join("<td>"+_e(line.get(k))+"</td>" for k in ("name","value","unit","reference_range"))+"</tr>")
        section.append("</tbody></table></section>")
        rows.append("".join(section))
    header='<header><h1>تقرير نتائج المختبر</h1><div class="details"><span>المريض: '+_e(patient.get("name") or report.get("patient_name"))+'</span><span>رقم الطلب: '+_e(order.get("id") or report.get("order_id"))+'</span><span>التاريخ: '+_e(order.get("created_at") or report.get("created_at"))+'</span></div></header>'
    css="""@page{size:A4 portrait;margin:13mm 12mm}*{box-sizing:border-box}
body{font-family:Arial,Tahoma,sans-serif;direction:rtl;color:#172b3a;margin:0;font-size:11pt}
header{border-bottom:2px solid #244c6b;padding-bottom:8mm;margin-bottom:7mm}
h1{text-align:center;font-size:18pt;margin:0 0 6mm}.details{display:flex;flex-wrap:wrap;gap:5mm 12mm}
h2{font-size:12pt;margin:0 0 3mm}.test{margin-bottom:6mm;break-inside:avoid-page;page-break-inside:avoid}
table{width:100%;border-collapse:collapse;table-layout:fixed}
thead{display:table-header-group}tr{break-inside:avoid;page-break-inside:avoid}
th,td{border-bottom:1px solid #d9e2e9;text-align:right;padding:2.5mm 2mm;overflow-wrap:anywhere}
th{background:#edf3f7;font-size:9pt}
@media screen{body{max-width:210mm;margin:auto;padding:12mm;box-shadow:0 0 8px #ddd}}"""
    return '<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><title>تقرير المختبر</title><style>'+css+'</style></head><body>'+header+''.join(rows)+'</body></html>'
