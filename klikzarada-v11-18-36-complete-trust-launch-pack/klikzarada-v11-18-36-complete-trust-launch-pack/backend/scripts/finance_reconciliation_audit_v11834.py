from fastapi.testclient import TestClient
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

# Prepare small negative rounding case and enough data for snapshot
db = SessionLocal()
try:
    user = db.query(User).filter(User.email == "korisnik@demo.rs").first()
    adv = db.query(User).filter(User.email == "oglasivac@demo.rs").first()
    user.balance_rsd = -0.25
    user.pending_rsd = 0
    adv.advertiser_budget_rsd = 1234
    adv.advertiser_reserved_rsd = 0
    adv.advertiser_spent_rsd = 0
    db.commit()
finally:
    db.close()

r = admin.get("/admin/finance-v11834")
local = r.status_code == 200 and "Finance reconciliation" in r.text and "Korisnički balans" in r.text
print(("OK" if local else "FAIL"), "ADMIN_PAGE", r.status_code)
ok = ok and local

r = admin.get("/api/v1/v11/finance-reconciliation-health")
local = r.status_code == 200 and r.json().get("version") == "11.18.34" and "users" in r.json() and "advertisers" in r.json()
print(("OK" if local else "FAIL"), "HEALTH", r.status_code, r.json().get("status") if r.status_code == 200 else r.text[:100])
ok = ok and local

payload = r.json()
local = any("Negativni korisnički" in w for w in payload.get("warnings", []))
print(("OK" if local else "FAIL"), "NEGATIVE_WARNING_DETECTED", payload.get("warnings"))
ok = ok and local

r = admin.get("/admin/finance-v11834.csv")
local = r.status_code == 200 and "section,metric,value" in r.text and "users,balance_rsd" in r.text
print(("OK" if local else "FAIL"), "CSV_EXPORT", r.status_code, r.text[:80])
ok = ok and local

r = admin.post("/admin/finance-v11834/fix-small-negatives", follow_redirects=False)
local = r.status_code in (302,303) and "fixed_" in (r.headers.get("location") or "")
print(("OK" if local else "FAIL"), "FIX_SMALL_NEGATIVES", r.status_code, r.headers.get("location"))
ok = ok and local

db = SessionLocal()
try:
    user = db.query(User).filter(User.email == "korisnik@demo.rs").first()
    local = round(user.balance_rsd, 2) == 0.00
    print(("OK" if local else "FAIL"), "NEGATIVE_FIXED_DB", user.balance_rsd)
finally:
    db.close()
ok = ok and local

r = admin.get("/api/v1/v11/finance-reconciliation-health")
local = r.status_code == 200 and r.json().get("version") == "11.18.34"
print(("OK" if local else "FAIL"), "HEALTH_AFTER_FIX", r.status_code, r.json().get("warnings") if r.status_code == 200 else None)
ok = ok and local

print("RESULT:", "PASS" if ok else "CHECK_FAILED")
raise SystemExit(0 if ok else 1)
