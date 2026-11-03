# NOVA Pharmacy — Batch13 Approved Purchases (3 November 2026)

## Approved by user
- Preserve the existing premium NOVA identity: dark-teal right navigation; invoice **left**, stock-first search and item entry **right**.
- A **single search** by medicine name/scientific name/barcode, with stocked catalog items first; the general imported catalog follows, no manual stock/directory tabs.
- Missing item can be created from an inline compact form, without navigating out of the invoice. Duplicate trade names and already-used barcodes are rejected.
- Barcode field sits immediately under the selected medicine. Optional; scan an empty field and assign it to the selected package, subject to uniqueness checks. Purchase and barcode registration commit atomically and are audited.
- Quantity, actual package, purchase cost and expiry appear on the right; **sale price and markup remain on the invoice/left only**, editable even after applying markup.
- Package sale: entered sale price is the full pack price. Unit/strip sale: the full pack sale price is divided by the entered number of strips; the resulting integer SDG strip price appears at POS, and can be edited explicitly on the left. Never rewrite historical sale prices.
- A fixed-height invoice list displays roughly five items, then scrolls internally. Keep totals and save actions easy to reach.
- Preserve bonuses, discounts, batch numbers, partial receiving, invoice/supplier metadata, bank/cash/credit payments, drafts, returns, Excel import and stock journals.

## Engineering approach
- Frontend module pharmacy/static/nova_batch13_purchase.js overrides only the purchase page presentation and search/quick-entry interaction, reusing purchaseRows and confirmPurchase.
- CSS module pharmacy/static/nova_batch13_purchase.css styles only nova13 selectors.
- Script .github/ci/nova_batch13_purchase.py adds server validation for nova_unit_rules and nova_purchase_barcodes and creates/updates strip packages **within the same purchase transaction**.
- Quick item creation uses a separate permission-gated purchase action; auto-generated SKU is internal and barcode is optional. This action does not create stock or payables.
- For an existing product, Unit requires its base-stock package factor to be divisible by the strip count. Otherwise it fails closed without changing inventory. Historical packaging factors must never be reinterpreted silently.
- All money is integer SDG. Derived strip prices round to nearest integer and remain manually editable before confirming.
- LAN, offline functionality and the central database are unchanged.

## Verification
- Synthetic integration: PYTHONPATH=pharmacy:. python -m unittest -q pharmacy.tests.test_nova_batch13 pharmacy.tests.test_nova_batch08.
- Syntax: node --check pharmacy/static/nova_pharmacy_batch08.js after the patch.
- Windows: build, fresh install, upgrade and rollback on disposable data only.
- Before live use: verify physical pharmacy client, barcode scanner, printer and backup/restore. CI success alone is not acceptance for clinical production.

## Source of truth
Repository: megdad234/nova-hospital-test. Original source ZIP is extracted then Batches 01–13 are layered. Separate from ALPHA, MADAR, NIVARA, GAMA and MedForce.
