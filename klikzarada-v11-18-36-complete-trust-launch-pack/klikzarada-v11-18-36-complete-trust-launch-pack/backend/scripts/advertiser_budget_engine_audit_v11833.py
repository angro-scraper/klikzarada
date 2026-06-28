from fastapi.testclient import TestClient
import app.main
from app.database import SessionLocal
from app.models import User, AdvertiserBudgetTransaction

app.main.startup()

def login(email, password):
    c = TestClient(app.main.app)
    r = c.post("/login", data={"email": email, "password": password}, follow_redirects=False)
    ok = r.status_code in (302, 303)
    print(("OK" if ok else "FAIL"), "LOGIN", email, r.status_code, r.headers.get("location"))
    return c, ok

ok = True
admin, ok_admin = login("admin@klikzarada.rs", "Admin123!")
adv_client, ok_adv = login("oglasivac@demo.rs", "Demo123!")
ok = ok and ok_admin and ok_adv

db = SessionLocal()
try:
    adv = db.query(User).filter(User.email == "oglasivac@demo.rs").first()
    adv.advertiser_budget_rsd = 1000
    adv.advertiser_reserved_rsd = 0
    adv.advertiser_spent_rsd = 0
    db.commit()
    adv_id = adv.id
finally:
    db.close()

# Advertiser topup request
r = adv_client.post("/oglasivac/budzet/zahtev-v11833", data={"amount_rsd": "5000", "note": "audit topup request"}, follow_redirects=False)
local = r.status_code in (302, 303) and "created" in (r.headers.get("location") or "")
print(("OK" if local else "FAIL"), "TOPUP_REQUEST", r.status_code, r.headers.get("location"))
ok = ok and local

db = SessionLocal()
try:
    tx = db.query(AdvertiserBudgetTransaction).filter(AdvertiserBudgetTransaction.advertiser_id == adv_id, AdvertiserBudgetTransaction.tx_type == "topup_request").order_by(AdvertiserBudgetTransaction.id.desc()).first()
    local = tx is not None and "5000" in tx.description
    print(("OK" if local else "FAIL"), "TOPUP_REQUEST_TX", getattr(tx, "description", None))
finally:
    db.close()
ok = ok and local

# Admin topup
r = admin.post(f"/admin/oglasivaci/{adv_id}/topup-v11833", data={"amount_rsd": "2500", "reason": "audit admin topup"}, follow_redirects=False)
local = r.status_code in (302, 303) and "topup_done" in (r.headers.get("location") or "")
print(("OK" if local else "FAIL"), "ADMIN_TOPUP", r.status_code, r.headers.get("location"))
ok = ok and local

db = SessionLocal()
try:
    adv = db.query(User).filter(User.id == adv_id).first()
    local = round(adv.advertiser_budget_rsd, 2) == 3500.00
    print(("OK" if local else "FAIL"), "BUDGET_AFTER_TOPUP", adv.advertiser_budget_rsd)
finally:
    db.close()
ok = ok and local

# Reserve budget helper
db = SessionLocal()
try:
    adv = db.query(User).filter(User.id == adv_id).first()
    res = app.main.v11833_reserve_budget(db, adv, 1200, "audit reserve")
    local = res == "reserved" and round(adv.advertiser_budget_rsd, 2) == 2300.00 and round(adv.advertiser_reserved_rsd, 2) == 1200.00
    print(("OK" if local else "FAIL"), "RESERVE_HELPER", res, adv.advertiser_budget_rsd, adv.advertiser_reserved_rsd)
finally:
    db.close()
ok = ok and local

# Spend reserved helper
db = SessionLocal()
try:
    adv = db.query(User).filter(User.id == adv_id).first()
    res = app.main.v11833_spend_reserved(db, adv, 700, "audit spend")
    local = res == "spent" and round(adv.advertiser_reserved_rsd, 2) == 500.00 and round(adv.advertiser_spent_rsd, 2) == 700.00
    print(("OK" if local else "FAIL"), "SPEND_RESERVED_HELPER", res, adv.advertiser_reserved_rsd, adv.advertiser_spent_rsd)
finally:
    db.close()
ok = ok and local

# Release reserved helper
db = SessionLocal()
try:
    adv = db.query(User).filter(User.id == adv_id).first()
    res = app.main.v11833_release_reserved(db, adv, 500, "audit release")
    local = res == "released" and round(adv.advertiser_reserved_rsd, 2) == 0.00 and round(adv.advertiser_budget_rsd, 2) == 2800.00
    print(("OK" if local else "FAIL"), "RELEASE_RESERVED_HELPER", res, adv.advertiser_reserved_rsd, adv.advertiser_budget_rsd)
finally:
    db.close()
ok = ok and local

# Health and snapshot
r = TestClient(app.main.app).get("/api/v1/v11/advertiser-budget-health")
local = r.status_code == 200 and r.json().get("version") == "11.18.33"
print(("OK" if local else "FAIL"), "HEALTH", r.status_code, r.json() if r.status_code == 200 else r.text[:100])
ok = ok and local

r = adv_client.get("/api/v1/v11/advertiser-budget-snapshot")
local = r.status_code == 200 and r.json().get("version") == "11.18.33" and "snapshot" in r.json()
print(("OK" if local else "FAIL"), "SNAPSHOT", r.status_code)
ok = ok and local

print("RESULT:", "PASS" if ok else "CHECK_FAILED")
raise SystemExit(0 if ok else 1)
