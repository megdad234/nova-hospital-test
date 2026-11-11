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
 body.printing-lab #print-area .lab-print-group th{background:#e4f0e9;font-weight:700;break-after:avoid-page}
 body.printing-lab #print-area .print-foot{break-inside:avoid-page}
}
"""
 return source+"\n"+css
def apply(root):
 file=Path(root)/"hospital/static/style.css"
 file.write_text(patch(file.read_text(encoding="utf-8")),encoding="utf-8")
 return file
if __name__=="__main__":apply(Path(__file__).resolve().parents[2])
