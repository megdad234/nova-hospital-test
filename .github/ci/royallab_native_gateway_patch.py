"""Attach original Royal Lab catalogue GET endpoints to existing NOVA gateway.

Preserves authentication and role authorization; no patient-result write endpoint.
Original test identifiers are used; no legacy test-name matching.
"""
from pathlib import Path
ANCHOR="return self.reply(royallab_nova_live_order_overlay.overlay_order_detail(c,core.order_detail(c,oid,role),role))"
IMPORT="from hospital import core, lab, finance, admin, royallab_nova_live_order_overlay"
ROUTES="""                    if path=='/api/hospital/royallab-native/tests':
                        core.require_role(role,'admin','reception','lab')
                        return self.reply(royallab_native_catalog_api.catalog_response(c))
                    if path.startswith('/api/hospital/royallab-native/form/'):
                        core.require_role(role,'admin','lab')
                        return self.reply(royallab_native_catalog_api.form_response(c,path.rsplit('/',1)[-1]))
"""
def patch(source):
 if source.count(ANCHOR)!=1:raise ValueError("Royal Lab gateway anchor changed")
 if source.count(IMPORT)!=1:raise ValueError("Royal Lab gateway import anchor changed")
 if 'royallab-native/tests' in source:raise ValueError("Native routes already installed")
 source=source.replace(IMPORT,IMPORT+", royallab_native_catalog_api",1)
 # Routes inherit existing authentication and database connection context.
 return source.replace(ANCHOR,ROUTES+"                    "+ANCHOR,1)
def apply(root):
 p=Path(root)/'hospital/gateway.py'
 p.write_text(patch(p.read_text(encoding='utf-8')),encoding='utf-8')
if __name__=='__main__':apply(Path(__file__).resolve().parents[2])
