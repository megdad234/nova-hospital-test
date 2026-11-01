# NOVA Pharmacy Batch08 — Preserve existing purchase screen (2 Nov 2026)

Approved: keep current purchase layout and all controls; add an unobtrusive invoice-wide price markup input, editable per-line sale prices, and purchase drafts persisted on the server. Keep supplier selection, invoice metadata, search/barcode, pack conversions, bonus, discounts, batch expiry, partial receiving, late receipts, supplier returns and payment methods, imports and all historical records.

On successful purchase, receive physical inventory and save sale prices atomically in one database transaction. New previously unpriced sibling packages may be priced proportionally without overwriting existing positive prices. Never rewrite historic purchase/sale prices.

Keep existing POS cash, bank, mixed, credit, held carts, returns, insurance and audit controls; make empty-cart instructions and unpriced-stock causes visible. Add dashboard expiry warnings for 7, 30, 90 days and expired stock, listing batch and quantity.

Add permission-protected pharmacy comprehensive report by date range: net sales, sale returns, cost of goods sold from sale lines, returned cost, gross profit, recorded operating expenses, operating result, gross/net margin, purchases and supplier returns in a separate section, patient cash/bank collections. Distinguish the current stock snapshot from historical figures. Purchases are not automatically expenses; the reported operating result excludes unrecorded salaries, accruals and other hospital modules. Print to PDF via browser, Excel-compatible CSV.

Source patch: .github/ci/nova_batch08_pharmacy_recovery.py runs after batch07; additional front-end file pharmacy/static/nova_pharmacy_batch08.js loads after the existing ux_v14 module. Do not touch live user DB. Require synthetic DB integration, JS syntax and Windows install/upgrade/rollback tests before trial. Real-device acceptance remains outstanding.