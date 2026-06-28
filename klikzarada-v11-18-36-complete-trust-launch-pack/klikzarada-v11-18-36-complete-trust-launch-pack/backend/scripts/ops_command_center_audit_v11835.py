from fastapi.testclient import TestClient
from datetime import datetime, timedelta
import app.main
from app.database import SessionLocal
from app.models import User, TaskSubmission, Withdrawal

app.main.startup()

def login(email, password):
    c = TestClient(app.main.app)
    r = c.post("/login", data={"email": email, "password": password}, follow_redirects=False)
    ok = r.status_code in (302, 303)
    print(("OK" if ok else "FAIL"), "LOGIN", email, r.status_code, r.headers.get("location"))
    return c, ok

ok = True
admin, ok_admin = login("admin@klikzarada.rs", "Admin123!")
ok = ok and ok_admin

# Prepare detectable issue without damaging real larger values
db = SessionLocal()
try:
    user = db.query(User).filter(User.email == "korisnik@demo.rs").first()
    user.balance_rsd = -0.50
    user.pending_rsd = 0
    db.commit()
finally:
    db.close()

r = admin.get("/admin/ops-v11835")
local = r.status_code == 200 and "Ops Command Center" in r.text and "Critical" in r.text
print(("OK" if local else "FAIL"), "ADMIN_OPS_PAGE", r.status_code)
ok = ok and local

r = admin.get("/api/v1/v11/ops-command-health")
data = r.json() if r.status_code == 200 else {}
local = r.status_code == 200 and data.get("version") == "11.18.35" and "issues" in data and data.get("counts", {}).get("total", 0) >= 1
print(("OK" if local else "FAIL"), "OPS_HEALTH", r.status_code, data.get("status"), data.get("counts"))
ok = ok and local

local = any("Negativan balans korisnika" in i.get("title","") for i in data.get("issues", []))
print(("OK" if local else "FAIL"), "NEGATIVE_BALANCE_ISSUE_DETECTED")
ok = ok and local

r = admin.get("/admin/ops-v11835.csv")
local = r.status_code == 200 and "severity,area,title,details" in r.text
print(("OK" if local else "FAIL"), "CSV_EXPORT", r.status_code, r.text[:80])
ok = ok and local

r = admin.post("/admin/ops-v11835/run", follow_redirects=False)
local = r.status_code in (302,303) and "scan_" in (r.headers.get("location") or "")
print(("OK" if local else "FAIL"), "RUN_SCAN", r.status_code, r.headers.get("location"))
ok = ok and local

print("RESULT:", "PASS" if ok else "CHECK_FAILED")
raise SystemExit(0 if ok else 1)
