# NOVA — Pharmacy and Cashier Batch 05 (1 Nov 2026)

## Scope and decisions
The user approved these pharmacy and cashier improvements while explicitly postponing all Admin dashboard development. Do not mix NOVA with ALPHA, MADAR, NIVARA, GAMA or MedForce. Reuse central SQLite and existing pharmacy billing, inventory and hospital finance functions, no browser-local database or online services.

### Pharmacy changes
- Server-side per-employee held POS carts via `nova_pos_held`; saves only product IDs and quantities, customer and insurance references. Does **not** reserve, allocate or deduct stock or lock prices; full validation remains on `sell()`.
- Pharmacy task cards sourced from live DB: held carts, incomplete purchase receipts, reorder shortages, expiry within 90 days, unpriced packs. Staff-triggered refresh, no background scheduler.
- Multi-partial returns clamp aggregate insurer credit to original coverage; on full invoice return, distribute the remainder to the last returned line within its amount.
- Pre-existing stock/price/receipt functions preserved.

### Hospital cashier changes
- One server-side searchable paginated queue for unified `nova_invoices` and pre-existing unpaid lab-only requests not already adopted or receipted. Filters for pending, partially paid, settled, and all; 40 rows per page; foreground auto-refresh.
- Premium checkout links to existing finance invoice/payment APIs.
- Explicit cashier-only quick patient and service request route `/api/hospital/nova-cashier-quick-invoice`, and read-only price quote authorization; do not give cashier administrator privileges.
- 80mm individual payment receipt, reprint each installment with post-installment remaining balance, preserve existing full invoice print.
- Hospital cashier shift-opening prevents a second open shift for same staff member. Existing end-of-shift expected/count variance remains.
- Free services: `nova_free_approved` stores admin approvals for a particular zero-price lab/service item. Zero price without explicit approval must never release an invoice to the clinical department. User's Admin dashboard redesign is postponed; only minimal free approval control added to existing service pricing.
- Frontdesk combined role receives cashier permissions for existing cashier endpoints. Receiver, bank and insurance role boundaries remain checked on server.

### CI and source of truth
Main repo: https://github.com/megdad234/nova-hospital-test
Source archive: `NOVA_Hospital_GitHub_Ready_Source.zip`.
Patch order in `.github/workflows/nova_build.yml`:
1. `.github/ci/nova_batch01_patch.py`
2. `.github/ci/nova_batch02_patch.py`
3. `.github/ci/nova_batch03_patch.py`
4. `.github/ci/nova_batch04_lab_reception.py`
5. `.github/ci/nova_batch05_cashier_pharmacy.py`
6. `.github/ci/nova_batch05_ui.py`
7. `.github/ci/nova_batch05_free_policy.py`
8. `.github/ci/nova_batch05_test_expectations.py`
Before these source patches, the Windows build also applies the earlier preflight hash and test-connection cleanup patches.

Fast workflow `.github/workflows/nova_batch05_fast.yml` tests Python compilation, JS syntax (and corrects a prior orphaned laboratory print JavaScript from Batch04), synthetic held carts and insurer rounding, existing HTTP finance/returns regressions, and direct cashier order/queue HTTP acceptance. Windows workflow performs full build plus install, upgrade preserving records and rollback on synthetic data. Installer is **NOT** accepted until the latest Windows workflow concludes successfully.

## Outstanding / testing limitations
- New screens and thermal printer require user acceptance on their physical Windows LAN, real barcode equipment and printer; browser syntax and CI are not a real device test.
- The user has not approved Admin dashboard changes or clinical OPD expansion.
- Held carts remain saved until the employee explicitly deletes them; resuming itself does not delete the draft.
- Real database migration must have a verified backup. CI uses disposable synthetic records, not live patient data.
- Keep separate 80mm receipt for every installment and detailed A4 invoice.
- Don't claim production-certified hospital system just because synthetic CI passed.
