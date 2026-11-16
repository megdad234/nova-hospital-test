"""Surgical lab-only NOVA work-queue upgrade after normal Windows UI patches.

Original backend retains core.orders and exact order_detail/result/payment routes.
A new admin/lab read-only endpoint permits date/status/test/patient searches
across all paid orders. The viewLab and single JS listener are replaced;
all report/print/receipt/pharmacy code is intentionally untouched.
"""
from pathlib import Path
import re

GATEWAY_IMPORT = "from hospital import core, lab, finance, admin"
GATEWAY_ANCHOR = """                    if path=='/api/hospital/orders':
                        core.require_role(role,'admin','reception','cashier','lab');return self.reply(core.orders(c,role))"""
GATEWAY_ROUTE = """                    if path=='/api/hospital/lab/queue':
                        core.require_role(role,'admin','lab')
                        query=parse_qs(urlparse(self.path).query)
                        def arg(key,default=''):
                            return (query.get(key) or [default])[0]
                        return self.reply(nova_lab_queue_search.search_queue(
                            c,role=role,q=arg('q'),period=arg('period','today'),
                            date_from=arg('from'),date_to=arg('to'),
                            status=arg('status','all'),page=arg('page','1'),
                            page_size=arg('page_size','25'),sort=arg('sort','newest')))
"""
LAB_WIRE_PATTERN = re.compile(
    r"if\(section==='lab'\)\{const render=\(\)=>\{\$\('lab-queue'\)\.innerHTML="
    r"orderRows\(state\.orders\.filter\(x=>\['paid','completed'\]\.includes\(x\.status\)\)"
    r"\.filter\(x=>.*?\)\);"
    r"document\.querySelectorAll\('\[data-order\]'\)\.forEach\(b=>b\.addEventListener"
    r"\('click',\(\)=>openDetails\(Number\(b\.dataset\.order\)\)\)\)\};"
    r"\$\('lab-search'\)\?\.addEventListener\('input',render\);"
    r"\$\('lab-refresh'\)\?\.addEventListener\('click',\(\)=>navigate\('lab'\)\)\}"
)
LAB_VIEW_PATTERN = re.compile(r"^function viewLab\(\)\{[^\n]*\}$", re.M)
STYLE = """
/* NOVA_LAB_QUEUE_FILTERS: exclusive to lab queue, no print/pharmacy styles. */
.nova-lab-toolbar{display:grid;grid-template-columns:minmax(220px,2fr) repeat(3,minmax(120px,1fr)) auto;gap:12px;align-items:end;margin:0 0 14px}
.nova-lab-toolbar label,.nova-lab-dates label{display:flex;flex-direction:column;gap:5px;font-weight:700;font-size:.85rem}
.nova-lab-toolbar input,.nova-lab-toolbar select,.nova-lab-dates input{width:100%;min-width:0;padding:10px;border:1px solid #bad8c9;border-radius:9px;background:var(--surface,#fff)}
.nova-lab-dates{display:flex;flex-wrap:wrap;gap:12px;margin:0 0 13px}
.nova-lab-dates[hidden],.nova-lab-alert[hidden]{display:none!important}
.nova-lab-alert{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:9px;border:1px solid #f0d7a4;border-radius:12px;background:#fff9eb;padding:10px 14px;margin:10px 0;color:#72511d}
.nova-lab-counters{color:#286152;font-weight:700;margin:10px 0}
.nova-lab-paging{display:flex;align-items:center;justify-content:flex-end;gap:10px;flex-wrap:wrap;margin:14px 0}
.nova-lab-preview{max-width:330px;overflow-wrap:anywhere}
.nova-lab-file{display:block;color:#60716b;font-size:.8rem;margin-top:4px}
#lab-queue[aria-busy="true"]{opacity:.65}
@media(max-width:920px){.nova-lab-toolbar{grid-template-columns:repeat(2,minmax(0,1fr))}.nova-lab-search-label{grid-column:1/-1}}
@media(max-width:550px){.nova-lab-toolbar{grid-template-columns:1fr}.nova-lab-search-label{grid-column:auto}}
"""


def patch_gateway(source):
    if source.count("if path=='/api/hospital/lab/queue':"):
        raise ValueError("NOVA laboratory queue route already installed")
    if source.count(GATEWAY_IMPORT) != 1:
        raise ValueError("NOVA hospital imports changed; stop")
    if source.count(GATEWAY_ANCHOR) != 1:
        raise ValueError("NOVA original orders route changed; stop")
    source=source.replace(GATEWAY_IMPORT,
                          GATEWAY_IMPORT+", nova_lab_queue_search",1)
    source=source.replace(GATEWAY_ANCHOR,GATEWAY_ROUTE+GATEWAY_ANCHOR,1)
    return source


def patch_app(source, extra):
    if "function novaLabQueueView()" in source:
        raise ValueError("NOVA laboratory queue already installed")
    if "function novaLabQueueView()" not in extra or "function novaLabQueueWire()" not in extra:
        raise ValueError("Missing validated laboratory queue JS functions")
    if source.count("function printReport(")!=1 or source.count("function openDetails(")!=1:
        raise ValueError("Original laboratory results/printing hooks changed; stop")
    result,count=LAB_VIEW_PATTERN.subn("function viewLab(){return novaLabQueueView();}",source)
    if count!=1:
        raise ValueError("Original NOVA laboratory view not found exactly once")
    result,count=LAB_WIRE_PATTERN.subn("if(section==='lab'){novaLabQueueWire();}",result)
    if count!=1:
        raise ValueError("Original NOVA laboratory search binding differs; stop")
    return result+"\n\n/* NOVA_LAB_QUEUE_FILTERS */\n"+extra+"\n"


def patch_style(source):
    if "NOVA_LAB_QUEUE_FILTERS" in source:
        raise ValueError("NOVA lab-only CSS already present")
    return source+"\n"+STYLE


def apply(root):
    root=Path(root)
    app_path=root/"hospital/static/app.js"
    css_path=root/"hospital/static/style.css"
    gateway_path=root/"hospital/gateway.py"
    helper_path=root/"hospital/static/nova_lab_queue_ui.js"
    if not (root/"hospital/nova_lab_queue_search.py").is_file():
        raise FileNotFoundError("Read-only NOVA lab queue backend missing")
    updated={
        app_path:patch_app(app_path.read_text(encoding="utf-8"),
                           helper_path.read_text(encoding="utf-8")),
        css_path:patch_style(css_path.read_text(encoding="utf-8")),
        gateway_path:patch_gateway(gateway_path.read_text(encoding="utf-8")),
    }
    for path,data in updated.items():
        path.write_text(data,encoding="utf-8")
    return tuple(str(k) for k in updated)


if __name__=="__main__":
    apply(Path(__file__).resolve().parents[2])
