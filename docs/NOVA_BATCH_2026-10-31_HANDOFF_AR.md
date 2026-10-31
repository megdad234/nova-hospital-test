# NOVA — handoff after implementation on 31 October 2026

## Source of truth and safety
- Repository: megdad234/nova-hospital-test (main).
- Base source is still packed in NOVA_Hospital_GitHub_Ready_Source.zip.
- Windows CI extracts that ZIP, then applies .github/ci/nova_batch01_patch.py, nova_batch02_patch.py, and nova_batch03_patch.py in order. It checks out Windows, builds the patched source, tests install/upgrade/rollback, and publishes a DEV artifact only on success.
- Download the generated Windows Setup artifact from the latest successful Actions run, not the unpatched root ZIP.
- No access to or changes in the customer's installed Windows database, server, live accounts, or actual records.

## Implemented in batch scripts
- Pharmacy POS: show only active, in-stock, sellable packages with defined sale price and enough base units. Barcode/quantity paths use the same checks; server rejects zero sale prices.
- Purchases: searchable on-screen product suggestions, quick barcode attachment to an existing package, packaging cost calculator, package factor correction only when safe (no historical purchase/sale records or stock).
- Pharmacy directory: remove duplicated search that only examined rendered DOM rows. Printouts use the saved hospital name instead of MADAR; remaining upstream page labels are cleaned in batch03.
- Lab permissions: add dedicated admin-granted, per-lab-user pricing permission; admin always retains pricing authority. Lab UI has admin catalog access and a staff grant toggle.
- Hospital branding: logo preview after saving, await image decoding before browser print, logo in shared invoice print, brand name in pharmacy receipts.
- Dental: 20 common services under the existing dental category with unpriced (0 SDG) defaults, preserving local price edits.
- Security: preserve transactional and no-negative-stock controls. Batch03 adds positive stock-adjustment expiry validation.
- Tests: legacy pharmacy receipt brand assertion updated; batch03 adds new tests for package correctness, server-side zero-price sale and per-user lab pricing/dental service creation.

## Still not complete / do not claim tested
- Total unification of legacy lab order cashier rendering/collections: the existing adopt-lab-order flow works, but legacy lab requests remain a separate cashier section, not one combined queue.
- Zero-priced lab services: still possible; explicit admin approval semantics for 'free' versus 'not priced' remain to be implemented and tested.
- Historical packaging correction: deliberately refuses overwriting old factors after inventory/transactions. A versioned package replacement workflow with stock reconciliation remains required for already-used packages.
- Patient edit workflow, mandatory reason for amendments of published results, and paginated server-side history still need dedicated fixes.
- True hospital-wide branding for every screen, all browser/thermal print variants, repeated-page print layouts is not fully covered.
- LAN and router changes, actual printers, encrypted network sessions, recovery after real power loss, backup restoration and current real installation remain unverified in a physical hospital.
- User explicitly asked that these be collected and tackled without losing any existing pharmacy/inpatient data. Do not call the system production approved until these are tested.

## How to continue
1. Review the latest main/Actions results; verify the specific revision and whether batch03 passed.
2. Keep modifications isolated to NOVA (never modify MADAR/ALPHA/NIVARA/MedForce or unrelated databases).
3. Implement gaps incrementally in CI-extracted source patch layers, or consolidate into verified source archive after tests.
4. On each change: synthetic payment/refund/stock/reports tests, Windows in-place upgrade + rollback on sample database; do not modify the customer's live data.
5. Seek explicit authorization for actual deployment. A successful CI build is not an instruction to update the user's machine.
