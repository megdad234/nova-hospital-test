"""Scoped A4 portrait pagination adjustments for existing NOVA laboratory reports."""
from pathlib import Path
def patch(source):
 anchor="/* NOVA Stage 5.2 — printable, clinic-style laboratory result sheet */"
 if source.count(anchor)!=1:raise RuntimeError("Original lab print CSS anchor not unique")
 marker="/* RoyalLab NOVA A4 portrait pagination — laboratory only */"
 if marker in source:raise RuntimeError("Lab pagination already patched")
 css="""/* RoyalLab NOVA A4 portrait pagination — laboratory only */
@media print{
 body.printing-lab #print-area .lab-print{width:100%;max-width:100%;font-size:10pt}
 body.printing-lab #print-area .print-head{break-after:avoid-page;page-break-after:avoid}
 body.printing-lab #print-area .print-patient{break-inside:avoid-page;page-break-inside:avoid;break-after:avoid-page}
 body.printing-lab #print-area .lab-print-test{break-inside:auto;page-break-inside:auto}
 body.printing-lab #print-area .print-test{break-after:avoid-page;page-break-after:avoid}
 body.printing-lab #print-area table{break-inside:auto;page-break-inside:auto}
 body.printing-lab #print-area thead{display:table-header-group}
 body.printing-lab #print-area tr{break-inside:avoid-page;page-break-inside:avoid}
 body.printing-lab #print-area .lab-print-group th,body.printing-lab #print-area .nova-lab-section th{background:#e4f0e9;font-weight:700;break-after:avoid-page}
 body.printing-lab #print-area .print-foot{break-inside:avoid-page}
}

/* A named A4 page applies ONLY to printed laboratory result documents.
   Unlike a global @page override it cannot rotate pharmacy, cashier, or
   hospital invoice printing. Chromium/Edge honors this named size. */
@page nova_lab_portrait{
 size:A4 portrait;
 margin:11mm 12mm 12mm;
}
@media print{
 body.printing-lab #print-area{
  page:nova_lab_portrait!important;
  width:100%!important;
  max-width:100%!important;
  min-width:0!important;
  overflow:visible!important;
 }
 body.printing-lab #print-area .lab-print{
  page:nova_lab_portrait!important;
  box-sizing:border-box!important;
  width:100%!important;
  max-width:100%!important;
  min-width:0!important;
  margin:0!important;
  padding:0!important;
  overflow:visible!important;
  font-size:9.5pt!important;
  line-height:1.35!important;
 }
 body.printing-lab #print-area .lab-print .print-head{
  min-height:0!important;
  padding:5px 0 8px!important;
  break-inside:avoid-page!important;
  break-after:avoid-page!important;
 }
 body.printing-lab #print-area .lab-print .print-logo{
  max-width:78px!important;
  max-height:65px!important;
 }
 body.printing-lab #print-area .lab-print .print-patient{
  padding:8px 0!important;
  column-gap:14px!important;
  row-gap:4px!important;
  break-inside:avoid-page!important;
  break-after:avoid-page!important;
 }
 body.printing-lab #print-area .lab-print .lab-print-test{
  min-width:0!important;
  margin-top:9px!important;
  break-inside:avoid-page;
  page-break-inside:avoid;
 }
 body.printing-lab #print-area .lab-print .print-test{
  margin:0 0 4px!important;
  padding:4px 8px!important;
  break-after:avoid-page!important;
 }
 body.printing-lab #print-area .lab-print .lab-results{
  display:table!important;
  box-sizing:border-box!important;
  width:100%!important;
  max-width:100%!important;
  min-width:0!important;
  table-layout:fixed!important;
  border-collapse:collapse!important;
  overflow:visible!important;
 }
 body.printing-lab #print-area .lab-print .lab-results th,
 body.printing-lab #print-area .lab-print .lab-results td{
  box-sizing:border-box!important;
  min-width:0!important;
  max-width:100%!important;
  padding:4px 5px!important;
  font-size:8.7pt!important;
  line-height:1.25!important;
  overflow-wrap:anywhere!important;
  word-break:normal!important;
  white-space:normal!important;
 }
 body.printing-lab #print-area .lab-print .lab-results :is(th,td):nth-child(1){width:34%!important}
 body.printing-lab #print-area .lab-print .lab-results :is(th,td):nth-child(2){width:16%!important}
 body.printing-lab #print-area .lab-print .lab-results :is(th,td):nth-child(3){width:18%!important}
 body.printing-lab #print-area .lab-print .lab-results :is(th,td):nth-child(4){width:32%!important}
 body.printing-lab #print-area .lab-print .lab-results thead{
  display:table-header-group!important;
 }
 body.printing-lab #print-area .lab-print .lab-results tr{
  break-inside:avoid-page!important;
  page-break-inside:avoid!important;
 }
 body.printing-lab #print-area .lab-print .lab-results .nova-lab-section,
 body.printing-lab #print-area .lab-print .lab-results .lab-print-group{
  break-after:avoid-page!important;
 }
 body.printing-lab #print-area .lab-print .print-foot{
  margin-top:9px!important;
  break-inside:avoid-page!important;
  page-break-inside:avoid!important;
 }
}
"""
 return source+"\n"+css
def apply(root):
 file=Path(root)/"hospital/static/style.css"
 file.write_text(patch(file.read_text(encoding="utf-8")),encoding="utf-8")
 return file
if __name__=="__main__":apply(Path(__file__).resolve().parents[2])
