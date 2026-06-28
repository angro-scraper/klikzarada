from fastapi.testclient import TestClient
import subprocess
import sys
from pathlib import Path

import app.main

app.main.startup()
c = TestClient(app.main.app)

ok = True

for path in ["/api/v1/v11/automation-health", "/api/v1/v11/automation-report"]:
    r = c.get(path)
    local = r.status_code == 200
    print(("OK" if local else "FAIL"), "API", path, r.status_code)
    ok = ok and local
    if path.endswith("automation-report") and local:
        data = r.json()
        local2 = data.get("version") == "11.18.24" and "banners" in data and "finance" in data and "last_logs" in data
        print(("OK" if local2 else "FAIL"), "REPORT_SHAPE")
        ok = ok and local2

for p in [
    "scripts/run_automation_once_v11824.py",
    "scripts/automation_scheduler_v11824.py",
    "scripts/install_windows_task_automation_v11824.ps1",
    "scripts/uninstall_windows_task_automation_v11824.ps1",
]:
    local = Path(p).exists()
    print(("OK" if local else "FAIL"), "SCRIPT_EXISTS", p)
    ok = ok and local

proc = subprocess.run([sys.executable, "scripts/run_automation_once_v11824.py"], text=True, capture_output=True, timeout=120)
local = proc.returncode == 0 and '"status": "ok"' in proc.stdout
print(("OK" if local else "FAIL"), "RUN_ONCE_SCRIPT", proc.returncode)
print(proc.stdout[-1000:])
if proc.stderr:
    print(proc.stderr[-1000:])
ok = ok and local

proc = subprocess.run([sys.executable, "scripts/automation_scheduler_v11824.py", "--once"], text=True, capture_output=True, timeout=120)
local = proc.returncode == 0 and '"status": "ok"' in proc.stdout
print(("OK" if local else "FAIL"), "SCHEDULER_ONCE", proc.returncode)
ok = ok and local

# Admin page has buttons/links
admin = TestClient(app.main.app)
r = admin.post("/login", data={"email": "admin@klikzarada.rs", "password": "Admin123!"}, follow_redirects=False)
if r.status_code in (302, 303):
    page = admin.get("/admin/auto-engine-v114")
    local = page.status_code == 200 and "Report JSON" in page.text and "Pokreni automatizaciju" in page.text
    print(("OK" if local else "FAIL"), "ADMIN_AUTO_PAGE_LINKS", page.status_code)
    ok = ok and local
else:
    print("FAIL", "ADMIN_LOGIN")
    ok = False

print("RESULT:", "PASS" if ok else "CHECK_FAILED")
raise SystemExit(0 if ok else 1)
