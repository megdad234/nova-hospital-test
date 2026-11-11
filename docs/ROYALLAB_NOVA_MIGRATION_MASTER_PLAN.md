# Royal Lab → NOVA migration (isolated branch)

Base snapshot: `baf20ee5952d7c814bd124d96b33dd557a58d06b` from NOVA `main`. No changes to main, any backup branches, or pharmacy logic.

Source of truth: private `megdad234/Royallab-Recovery`, branch `recovered-results`, containing original 367 tests, 1,245 analytes, result formats, options and reference ranges.

## Non-negotiable completion criteria
1. Inventory the actual NOVA laboratory schema, result entry UI, persistence, printing, migration and deployment in the original source archive.
2. Preserve Royal Lab definitions and original IDs, including orphaned records for audit. Never silently discard 63 empty/partial tests, 221 quarantined analytes, or 2,551 unlinked options.
3. Make a deterministic, repeatable, reversible lab-catalog replacement, with preflight, backup and rollback. Never drop patient/transaction tables; user has only experimental data but no destructive operation is authorized until migration is validated.
4. Support numeric, free text, dropdown, mixed and tabular tests; verify malaria, urine, stool, CBC, cultures and antibiotic sensitivity by real fixtures.
5. Validate save/reopen/edit, print A4 portrait, single patient header and results, pagination, no partial-report boilerplate, RTL.
6. Run comprehensive automated tests and produce a deployable Windows package; never claim complete until actually tested.
7. No modifications to pharmacy receipt printing, sales, returns or unrelated hospital modules.

## Status
- Isolated feature branch created from immutable NOVA main SHA.
- Royal Lab extraction and structural audits succeeded in separate repository.
- NOVA source audit and cross-repository import integration still pending.
- Production migration not yet performed.
