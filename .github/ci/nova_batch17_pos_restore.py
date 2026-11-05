from pathlib import Path
root=Path(__file__).resolve().parents[2]
css=root/'pharmacy/static/style.css'
s=css.read_text(encoding='utf-8')
# Restore compact sale layout, overriding only the POS geometry added by later batches.
s+="""

/* NOVA17: restore usable pharmacy checkout geometry; no sales/refund logic changes. */
@media screen and (min-width:951px){
.salearea{display:grid!important;grid-template-columns:minmax(300px,1fr) minmax(0,1.65fr)!important;align-items:start!important;gap:12px!important}
.salearea>.nova-holdbar{grid-column:1/-1!important;grid-row:1!important;min-height:0!important}
.salearea>.panel.nova-pos-search{grid-column:1!important;grid-row:2!important;height:auto!important;min-height:0!important;overflow:visible!important}
.salearea>.panel.nova-pos-checkout{grid-column:2!important;grid-row:2!important;height:auto!important;min-height:0!important;overflow:visible!important}
.salearea>.nova-pos-checkout .sale-cart-list{height:auto!important;min-height:80px!important;max-height:240px!important;overflow-y:auto!important}
.salearea>.nova-pos-checkout .pay-buttons{display:flex!important;flex-wrap:wrap!important;gap:8px!important}
}
@media screen and (max-width:950px){
.salearea{display:flex!important;flex-direction:column!important}
.salearea>.panel{width:100%!important}
.salearea>.nova-pos-checkout .sale-cart-list{height:auto!important;min-height:80px!important;max-height:260px!important}
}
"""
css.write_text(s,encoding='utf-8')
# Prevent the Batch14 extra discount field from splitting the approved cart header.
p=root/'pharmacy/static/app.js'
j=p.read_text(encoding='utf-8')
needle='</div><div class="field"><label for="nova-sale-discount">'
if needle in j:
 j=j.replace(needle,'</div><div class="field nova-pos-discount-compact"><label for="nova-sale-discount">',1)
 p.write_text(j,encoding='utf-8')
print('NOVA17_POS_LAYOUT_RESTORED_WITHOUT_TOUCHING_REFUNDS')
