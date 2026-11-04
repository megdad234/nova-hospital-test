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

## Automatic backup

`python -m commercial_pharmacy.cli backup-auto --retain 30` creates a timestamped online SQLite backup and retains the latest 30 automatic backups without deleting manual backups. `list-backups` inventories available files. On Windows, `commercial_pharmacy/windows/install-backup-task.ps1` can register an opt-in daily schedule against a verified Python source installation; `uninstall-backup-task.ps1` removes only that task. These scripts do not build or validate a standalone installer.

## Windows installer blueprint

`commercial_pharmacy/windows/commercial-pharmacy-installer.iss` defines a separate Inno Setup product, desktop shortcut, private-LAN firewall rule and service registration/removal. It references commercial EXEs that have **not been produced or verified**. Its output filename explicitly includes `UNVERIFIED`; do not publish or install as a finished product. Clean install, upgrades, service behavior, printer, LAN and coexistence still require Windows acceptance evidence.

## Packaging tools (candidate only)

`commercial_pharmacy/windows/validate-installer-inputs.ps1` verifies that both distinct commercial Windows executables exist and have PE signatures. `build-installer-candidate.ps1` invokes Inno Setup only after this check. `check-commercial-service.ps1` reads the independent service status and TCP listener without touching hospital services. These are preparatory tools: the actual executables, live integration, signed acceptance logs and tested Setup.exe remain outstanding.

## Source launcher and service adapter

`python -m commercial_pharmacy.launch --source-root <extracted-source> --preflight-only` validates the patched pharmacy source, commercial data root and port without starting the server. The launch command can invoke the extracted `pharmacy/server_host.py`, but that server’s actual port handling and hospital independence remain unverified. `commercial_pharmacy/windows_service.py` is a pywin32 SCM adapter prototype, not yet bundled into a tested EXE; it intentionally requires a separately configured `NOVA_COMMERCIAL_PYTHON` runtime. No production service registration should be attempted until end-to-end Windows acceptance.

## LAN desktop launcher

`python -m commercial_pharmacy.desktop_client --host 192.168.1.10 --port 18763` opens the independent pharmacy URL in the default browser. `--print-url` outputs the URL without opening a browser. The host must be a valid IPv4 LAN address or hostname; reserved hospital port 10080 is rejected. This does not provide automatic server discovery or an installable desktop EXE; those still require runtime integration and Windows packaging.

## Windows candidate build workflow

`.github/workflows/commercial_pharmacy_candidates.yml` builds two PyInstaller EXE candidates on the commercial branch, smoke-tests the LAN client URL and checks both executable headers. Artifact: `Commercial-EXE-CANDIDATES-NOT-INSTALLABLE`. The service candidate still needs a dedicated Python runtime, extracted pharmacy source, and live SCM acceptance; do not install it as a production Windows service or distribute it as Setup.exe. The source-only Windows snapshot and release gate remain separate.

## Windows LAN client configuration

On each Windows workstation, `commercial_pharmacy/windows/configure-lan-client.ps1` can create a desktop shortcut targeting the dedicated client EXE with `--host` and `--port`; the client also supports `NOVA_COMMERCIAL_SERVER_HOST` and `NOVA_COMMERCIAL_PORT` environment overrides. Example: `powershell -File configure-lan-client.ps1 -ServerHost 192.168.1.10 -ClientExecutable C:\\Pharmacy\\NOVACommercialPharmacy.exe -ShortcutPath C:\\Users\\Public\\Desktop\\CommercialPharmacy.lnk`. This configures only a shortcut; it does not start or validate a live pharmacy server.

## Opt-in live LAN connectivity smoke

After independently starting the extracted pharmacy server, run `python -m commercial_pharmacy.smoke_http --host 127.0.0.1 --port 18763` on the server or replace the host with its LAN IPv4 address on a workstation. An HTTP response only confirms network reachability; it does not validate sales, stock, printing, insurance, or database isolation and never authorizes release. The candidate Inno installer deliberately has neither automatic service installation nor automatic service removal until the complete runtime is packaged and tested.
