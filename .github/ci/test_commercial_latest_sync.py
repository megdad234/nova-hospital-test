# Regression gate for modern NOVA -> independent retail pharmacy transfer.
# Runs only on synthetic extracted source after canonical NOVA patches and isolation.
from pathlib import Path

root = Path(__file__).resolve().parents[2]
app = (root / "pharmacy/app.py").read_text(encoding="utf-8")
js = (root / "pharmacy/static/app.js").read_text(encoding="utf-8")
price_ui = (root / "pharmacy/static/nova_bulk_prices_ui.js").read_text(encoding="utf-8")
html = (root / "pharmacy/static/index.html").read_text(encoding="utf-8")

assert "NOVA_COMMERCIAL_DATA_DIR" in app and "commercial_pharmacy.sqlite3" in app, "Hospital database isolation missing"
assert "def nova_price_list_approve(" in app and "def nova_price_list_rollback(" in app, "Price change rollback missing"
assert "function novaReturnStatus(s)" in js, "Missing current NOVA return status"
assert "مرتجع بالكامل" in js and "مرتجع جزئي" in js, "Missing full and partial return labels"
assert js.count("function sales(){return ") == 1, "Unexpected sales history replacement"
assert "function pos()" in js and js.index("function pos()") < js.index("function novaReturnStatus(s)"), "POS layout/function moved"
assert "panel.hidden=true" in price_ui and "panel.style.display='none'" in price_ui, "Supplier price overlay may block the whole pharmacy screen"
assert "overscroll-behavior:contain" in price_ui, "Price overlay scrolling protection missing"
assert "nova-price-list-approve" in app and "nova-price-list-rollback" in app, "Price audit endpoints missing"
assert "nova_bulk_prices_ui.js" in html, "Supplier price UI not connected to pharmacy"
print("COMMERCIAL_MODERN_NOVA_SYNC_VALIDATED")
