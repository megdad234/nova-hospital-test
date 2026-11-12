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
                    if path=='/api/hospital/royallab-native/review/propose':
                        core.require_role(role,'admin','lab')
                        return self.reply(royallab_clinical_template_review.propose(
                            c,user,royallab_native_catalog_api.current_catalog_id(c),
                            data.get('source_test_id'),data.get('fields'),
                            method=data.get('method'),evidence=data.get('evidence'),
                            rationale=data.get('rationale')))
                    if path=='/api/hospital/royallab-native/review/approve':
                        core.require_role(role,'admin')
                        return self.reply(royallab_clinical_template_review.approve(
                            c,user,royallab_native_catalog_api.current_catalog_id(c),
                            data.get('source_test_id'),
                            core.integer(data.get('revision'),'نسخة نموذج المعمل',1),
                            data.get('form_hash'),attestation=data.get('attestation')))
"""
REVIEW_DETAILS_ROUTE="""                    if path.startswith('/api/hospital/royallab-native/review/details/'):
                        core.require_role(role,'admin','lab')
                        parts=path.rsplit('/',2)
                        return self.reply(royallab_clinical_template_review.review_details(
                            c,royallab_native_catalog_api.current_catalog_id(c),
                            parts[-2],core.integer(parts[-1],'نسخة نموذج المعمل',1)))
"""
REVIEW_HISTORY_ROUTE="""                    if path.startswith('/api/hospital/royallab-native/review/history/'):
                        core.require_role(role,'admin','lab')
                        return self.reply(royallab_clinical_template_review.review_history(
                            c,royallab_native_catalog_api.current_catalog_id(c),
                            path.rsplit('/',1)[-1]))
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
 source=source.replace(IMPORT,IMPORT+", royallab_native_catalog_api, royallab_native_order_bridge, royallab_clinical_template_review",1)
 # Routes inherit existing authentication and database connection context.
 marker="                    if path=='/api/hospital/patients':"
 if source.count(marker)!=2:raise ValueError("Expected GET and POST patient routes")
 parts=source.split(marker)
 if len(parts)!=3:raise ValueError("NOVA GET/POST patient anchors changed")
 return parts[0]+ROUTES+GET_DRAFT_ROUTE+REVIEW_HISTORY_ROUTE+REVIEW_DETAILS_ROUTE+marker+parts[1]+POST_ROUTES+marker+parts[2]
def apply(root):
 p=Path(root)/'hospital/gateway.py'
 p.write_text(patch(p.read_text(encoding='utf-8')),encoding='utf-8')
if __name__=='__main__':apply(Path(__file__).resolve().parents[2])
