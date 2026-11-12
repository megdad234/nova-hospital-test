"""Attach original Royal Lab catalogue GET endpoints to existing NOVA gateway.

Preserves authentication and role authorization; no patient-result write endpoint.
Original test identifiers are used; no legacy test-name matching.
"""
from pathlib import Path
ANCHOR="return self.reply(royallab_nova_live_order_overlay.overlay_order_detail(c,core.order_detail(c,oid,role),role))"
IMPORT="from hospital import core, lab, finance, admin, royallab_nova_live_order_overlay"
POST_ROUTES="""                    if path=='/api/hospital/royallab-native/order/attach':
                        core.require_role(role,'admin','lab')
                        return self.reply(royallab_native_order_bridge.attach_native_test(
                            c,user,core.integer(data.get('nova_item_id'),'رقم فحص الطلب',1),
                            data.get('source_test_id')))
                    if path=='/api/hospital/royallab-native/order/draft':
                        core.require_role(role,'admin','lab')
                        return self.reply(royallab_native_order_bridge.save_order_item_draft(
                            c,user,core.integer(data.get('nova_item_id'),'رقم فحص الطلب',1),
                            data.get('values')))
"""
GET_DRAFT_ROUTE="""                    if path.startswith('/api/hospital/royallab-native/order/draft/'):
                        core.require_role(role,'admin','lab')
                        return self.reply(royallab_native_order_bridge.load_order_item_draft(
                            c,user,core.integer(path.rsplit('/',1)[-1],'رقم فحص الطلب',1)))
"""
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
 source=source.replace(IMPORT,IMPORT+", royallab_native_catalog_api, royallab_native_order_bridge",1)
 # Routes inherit existing authentication and database connection context.
 marker="                    if path=='/api/hospital/patients':"
 if source.count(marker)!=2:raise ValueError("Expected GET and POST patient routes")
 source=source.replace(marker,ROUTES+GET_DRAFT_ROUTE+marker,1)
 return source.replace(marker,POST_ROUTES+marker,1)
def apply(root):
 p=Path(root)/'hospital/gateway.py'
 p.write_text(patch(p.read_text(encoding='utf-8')),encoding='utf-8')
if __name__=='__main__':apply(Path(__file__).resolve().parents[2])
