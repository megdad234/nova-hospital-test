Commercial Windows packaging is not yet verified.
Do not distribute an installer until both executables and full acceptance evidence exist.

Installer safety (2026-11-04): automatic Windows service registration in the Inno Setup candidate is disabled. The two EXE candidates alone do not bundle the extracted pharmacy server source or dedicated Python environment. Do not distribute or install the candidate as a working pharmacy. The standalone source preflight now rejects missing server_host.py and absent NOVA_COMMERCIAL_PORT; it is not a live server test.

Windows service registration requires machine-scoped NOVA_COMMERCIAL_SOURCE_ROOT and NOVA_COMMERCIAL_PYTHON pointing to existing commercial source and a dedicated Python runtime. A process-local variable does not configure the Windows service. Building an unverified installer candidate requires NOVA_COMMERCIAL_ALLOW_UNVERIFIED_INSTALLER=YES; this does not authorize release.
