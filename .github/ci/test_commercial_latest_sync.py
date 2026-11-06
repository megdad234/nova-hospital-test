# Regression gate: preserve approved NOVA POS and refund transaction logic.
# Runs on generated, isolated commercial source after all NOVA batch patches.
from pathlib import Path

root = Path(__file__).resolve().parents[2]
app = (root / "pharmacy/app.py").read_text(encoding="utf-8")
js = (root / "pharmacy/static/app.js").read_text(encoding="utf-8")
price_ui = (root / "pharmacy/static/nova_bulk_prices_ui.js").read_text(encoding="utf-8")
html = (root / "pharmacy/static/index.html").read_text(encoding="utf-8")

assert "NOVA_COMMERCIAL_DATA_DIR" in app and "commercial_pharmacy.sqlite3" in app, "Hospital database isolation missing"
assert "def nova_price_list_approve(" in app and "def nova_price_list_rollback(" in app, "Price change rollback missing"
assert "function novaReturnDisplayStatus(s)" in js, "Missing approved display-only NOVA return status"
assert "تم الاسترجاع" in js and "مرتجع جزئي" in js, "Missing full and partial return labels"
assert js.count("function sales(){return ") == 1, "Unexpected sales history replacement"
assert js.count("function novaReturnDisplayStatus(s)") == 1, "Return status injected more than once"
assert "function pos()" in js and js.index("function pos()") < js.index("function novaReturnDisplayStatus(s)"), "POS handler/layout moved"
assert "panel.hidden=true" in price_ui and "panel.hidden=false" in price_ui, "Supplier price overlay must be hidden by default and toggle explicitly"
assert "close.onclick" in price_ui and "launch.onclick" in price_ui, "Price overlay close/open wiring missing"
assert "display:block" not in price_ui.split("panel.style.cssText=",1)[1].split(";",1)[0], "Price overlay must not override hidden display on startup"
assert "overflow:auto" in price_ui and "position:fixed" in price_ui, "Supplier price overlay requires independent scrolling"
assert "nova-price-list-approve" in app and "nova-price-list-rollback" in app, "Price audit endpoints missing"
assert "nova_bulk_prices_ui.js" in html, "Supplier price UI not connected to pharmacy"
assert "def nova_manual_sale_price(" in app, "Missing latest manual sale-price edit"
assert "nova-manual-sale-price" in app and "nova-sale-price-catalog" in app, "Manual sale-price endpoints missing"
assert "def nova_price_list_preview(" in app and "confirmed_matches" in app, "Manual supplier candidate matching missing"
assert "l.qty_base>0" in app and "l.status='sellable'" in app, "Supplier preview stock restriction missing"
assert "السعر أو الرصيد تغير" in app, "Supplier approval must recheck current sellable stock"
assert "nova_manual_price_editor.js" in html, "Manual price editor not included in standalone pharmacy"
assert (root / "pharmacy/static/nova_manual_price_editor.js").is_file(), "Manual price editor asset not staged"
insurance_js=(root / "pharmacy/static/nova_pharmacy_batch08.js").read_text(encoding="utf-8")
assert "nova-admin-insured-enroll" in app and "nova-admin-patient-search" in app, "Insurance admin registration routes missing"
assert "nova-admin-insured-enroll" in insurance_js, "Advance beneficiary registration UI missing"
assert "commercial_pharmacy_patients" in app, "New enrollment must use independent pharmacy patient records"
assert "nova-hospital-patient-search" not in insurance_js, "Standalone POS still calls hospital patient search"
print("COMMERCIAL_MODERN_NOVA_SYNC_VALIDATED")
