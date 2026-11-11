"""Surgical NOVA order-detail read-only Royal Lab overlay patch.

Preserves existing role checks, payment gating, original order endpoint,
and the lab/values save endpoint. Missing review binding means legacy output.
"""
from pathlib import Path
IMPORT="from hospital import core, lab, finance, admin"
ROUTE="return self.reply(core.order_detail(c,oid,role))"
NEW_ROUTE="return self.reply(royallab_nova_live_order_overlay.overlay_order_detail(c,core.order_detail(c,oid,role),role))"
def patch(source):
    if source.count(IMPORT)!=1 or source.count(ROUTE)!=1:
        raise ValueError("Original NOVA gateway import or order route anchor changed")
    if "royallab_nova_live_order_overlay" in source:
        raise ValueError("Royal Lab order route already patched")
    source=source.replace(IMPORT,IMPORT+", royallab_nova_live_order_overlay",1)
    return source.replace(ROUTE,NEW_ROUTE,1)
def apply(root):
    p=Path(root)/"hospital/gateway.py"
    p.write_text(patch(p.read_text(encoding="utf-8")),encoding="utf-8")
if __name__=="__main__":apply(Path(__file__).resolve().parents[2])
