# NOVA Commercial Pharmacy — implementation status

## Current verified scope
The branch contains isolated commercial storage, backup and offline restore modules, maintenance CLI, synthetic regression tests, extraction and coupling audits. It is **not** a validated Windows application or installer.

## Maintenance CLI (source checkout)
Run from the repository root with Python 3.12:

```powershell
python -m commercial_pharmacy.cli --data-dir "C:\ProgramData\NOVACommercialPharmacy" inspect
python -m commercial_pharmacy.cli --data-dir "C:\ProgramData\NOVACommercialPharmacy" diagnose
python -m commercial_pharmacy.cli --data-dir "C:\ProgramData\NOVACommercialPharmacy" initialize
python -m commercial_pharmacy.cli --data-dir "C:\ProgramData\NOVACommercialPharmacy" check-database
python -m commercial_pharmacy.cli --data-dir "C:\ProgramData\NOVACommercialPharmacy" backup snapshot-001.sqlite3
python -m commercial_pharmacy.cli --data-dir "C:\ProgramData\NOVACommercialPharmacy" verify-backup "C:\ProgramData\NOVACommercialPharmacy\backups\snapshot-001.sqlite3"
```

The `diagnose` command reports configured port availability, data directories and database integrity without creating the database. `initialize` only prepares commercial directories/configuration; it does **not** create a pharmacy administrator or start the POS server.

## Explicit release blockers
1. Integrate the real patched pharmacy server entrypoint with the commercial data directory and port.
2. Remove all remaining hospital API, imports and schema coupling; verify first-admin, insurance, POS, purchasing, stock and receipts.
3. Produce an actual service-aware Windows server and desktop client; avoid registering generic Python binaries as Windows services.
4. Build a standalone Inno Setup installer with distinct service, AppId, port, ProgramData directory and upgrade/uninstall semantics.
5. Run full Windows installation, upgrade, uninstall, LAN, printer and NOVA Hospital coexistence acceptance; collect evidence and installer SHA256.
6. Only then permit the release gate to mark the commercial installer as publishable.

**Never distribute `Commercial-Pharmacy-Audited-Source-NOT-INSTALLABLE` as a setup executable.**
