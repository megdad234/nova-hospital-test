"""Windows SCM adapter for independent commercial pharmacy server.

Requires pywin32 and an audited extracted pharmacy source tree.
Never registers or modifies the hospital service.
"""
from __future__ import annotations
import os
from pathlib import Path
import subprocess
import sys

SERVICE_NAME = "NOVACommercialPharmacyServer"

def pharmacy_command(root: Path):
    entry = root / "pharmacy" / "server_host.py"
    if not entry.is_file():
        raise FileNotFoundError(str(entry))
    python = os.environ.get("NOVA_COMMERCIAL_PYTHON")
    if not python or not Path(python).is_file():
        raise RuntimeError("Dedicated commercial Python runtime has not been configured")
    return [python, str(entry)]

def run_service():
    try:
        import win32event
        import win32service
        import win32serviceutil
    except ImportError as exc:
        raise RuntimeError("pywin32 is required for Windows SCM service mode") from exc

    class CommercialPharmacyService(win32serviceutil.ServiceFramework):
        _svc_name_ = SERVICE_NAME
        _svc_display_name_ = "NOVA Commercial Pharmacy Server"
        _svc_description_ = "Independent pharmacy server; does not depend on NOVA Hospital."

        def __init__(self, args):
            super().__init__(args)
            self.stop_event = win32event.CreateEvent(None, 0, 0, None)
            self.process = None

        def SvcStop(self):
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            win32event.SetEvent(self.stop_event)
            if self.process is not None:
                self.process.terminate()

        def SvcDoRun(self):
            root = Path(os.environ.get("NOVA_COMMERCIAL_SOURCE_ROOT", Path(sys.executable).parent)).resolve()
            command = pharmacy_command(root)
            env = dict(os.environ)
            env.setdefault("NOVA_COMMERCIAL_DATA_DIR", str(Path(os.environ.get("PROGRAMDATA", "C:/ProgramData")) / "NOVACommercialPharmacy"))
            env.setdefault("NOVA_COMMERCIAL_PORT", "18763")
            self.process = subprocess.Popen(command, cwd=str(root), env=env)
            try:
                self.process.wait()
            finally:
                self.process = None

    if "--service" in sys.argv:
        import servicemanager
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(CommercialPharmacyService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(CommercialPharmacyService)

if __name__ == "__main__":
    run_service()
