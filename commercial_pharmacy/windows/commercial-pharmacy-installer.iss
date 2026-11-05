; NOVA Commercial Pharmacy — Windows installer blueprint.
; Build only after verified service-aware EXE, desktop EXE and full acceptance.
; Distinct product identity; does not install/uninstall NOVA Hospital.
#define AppName "NOVA Commercial Pharmacy"
#define AppVersion "0.1.0-pre-release"
#define AppExe "NOVACommercialPharmacy.exe"
#define ServerExe "NOVACommercialPharmacyServer.exe"

[Setup]
AppId={{F8927F4B-2B30-4C61-9B8E-4275F948A164}
AppName={#AppName}
AppVersion={#AppVersion}
DefaultDirName={autopf}\NOVA Commercial Pharmacy
DefaultGroupName=NOVA Commercial Pharmacy
OutputDir=..\..\dist\commercial-installer-candidate
OutputBaseFilename=NOVA-Commercial-Pharmacy-UNVERIFIED
PrivilegesRequired=admin
Compression=lzma2
SolidCompression=yes
DisableProgramGroupPage=yes
UninstallDisplayName={#AppName}

[Files]
Source: "..\..\dist\commercial\{#AppExe}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\dist\commercial\{#ServerExe}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\dist\commercial\runtime\*"; DestDir: "{app}\runtime"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\..\dist\commercial\pharmacy\*"; DestDir: "{app}\pharmacy"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\..\dist\commercial\commercial_pharmacy\*"; DestDir: "{app}\commercial_pharmacy"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "install-commercial-service.ps1"; DestDir: "{app}\maintenance"; Flags: ignoreversion
Source: "uninstall-commercial-service.ps1"; DestDir: "{app}\maintenance"; Flags: ignoreversion
Source: "configure-lan-client.ps1"; DestDir: "{app}\maintenance"; Flags: ignoreversion
Source: "check-service-prerequisites.ps1"; DestDir: "{app}\maintenance"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\NOVA Commercial Pharmacy"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\NOVA Commercial Pharmacy"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Tasks]
Name: desktopicon; Description: "Create desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Run]
Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File ""{app}\maintenance\install-commercial-service.ps1"" -ExecutablePath ""{app}\{#ServerExe}"" -Port 18763 -OpenLanFirewall -ServiceAwareExecutableConfirmed"; Flags: runhidden waituntilterminated; StatusMsg: "Starting NOVA Commercial Pharmacy server..."

[UninstallRun]
Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File ""{app}\maintenance\uninstall-commercial-service.ps1"" -RemoveLanFirewallRule"; Flags: runhidden waituntilterminated
