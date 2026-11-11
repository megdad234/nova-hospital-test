# Royal Lab real-data staging verification — 2026-11-11

## Verified GitHub Actions evidence
- Recovery repo: megdad234/Royallab-Recovery
- Isolated branch: feature/nova-real-data-validation-20261111
- Successful workflow run: https://github.com/megdad234/Royallab-Recovery/actions/runs/43034179137
- NOVA feature branch: feature/royallab-full-migration-20261111
- Actual source: recovered RoyalLabDB.bak catalog JSON, NOT synthetic fixtures.
- Disposable SQLite database, no clinical patient data, no production migration.

## Observed
- 367 source tests staged
- 1,245 analytes staged
- 2,551 unresolved source options staged without loss
- 64 analytes detached from a source test ID
- Field adapter counts across linked analytes: 734 text, 638 dropdown, 10 mixed dropdown/free-text, 81 unknown.
- 87 tests have at least one review flag.
- Idempotence and unchanged pre-existing hospital_lab_tests test row confirmed.

## Important boundaries
- This proves that source catalog staging and format adaptation can process the recovered source.
- It does NOT prove actual NOVA UI integration, correct clinical ranges, complete lab reporting, cashier/reception integration, printing, or Windows installer readiness.
- Do not publish catalog for clinical use until field-format anomalies, missing references, and clinical validation are resolved.
- Keep the production database and original NOVA main untouched.
