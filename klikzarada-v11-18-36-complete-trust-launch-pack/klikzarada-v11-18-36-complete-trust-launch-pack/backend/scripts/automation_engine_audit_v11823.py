from fastapi.testclient import TestClient
from datetime import datetime, timedelta
import app.main
from app.database import SessionLocal
from app.models import User, HomeBannerSlotV111, PaidAdBannerV111, AutoEngineLogV114, Withdrawal

app.main.startup()

def login_admin():
    c = TestClient(app.main.app)
    r = c.post("/login", data={"email": "admin@klikzarada.rs", "password": "Admin123!"}, follow_redirects=False)
    ok = r.status_code in (302, 303)
    print(("OK" if ok else "FAIL"), "ADMIN_LOGIN", r.status_code, r.headers.get("location"))
    return c, ok

ok=True
admin, local = login_admin()
ok = ok and local

# Seed test data
db = SessionLocal()
try:
    adv = db.query(User).filter(User.email=="oglasivac@demo.rs").first()
    if not adv:
        adv = db.query(User).filter(User.role=="oglasivac").first()
    adv.advertiser_budget_rsd = float(adv.advertiser_budget_rsd or 0) + 10000
    slot = db.query(HomeBannerSlotV111).filter(HomeBannerSlotV111.code=="home_bottom_2").first()
    if not slot:
        slot = db.query(HomeBannerSlotV111).first()

    expired = PaidAdBannerV111(
        advertiser_id=adv.id,
        slot_id=slot.id,
        title="Audit expired automation banner",
        body="Should expire automatically",
        image_url="/static/img/banner_generic.svg",
        target_url="/",
        price_rsd=0,
        days_count=1,
        status="active",
        starts_at=datetime.utcnow() - timedelta(days=3),
        ends_at=datetime.utcnow() - timedelta(days=1)
    )
    rejected = PaidAdBannerV111(
        advertiser_id=adv.id,
        slot_id=slot.id,
        title="Audit rejected reserved banner",
        body="Should release reserved",
        image_url="/static/img/banner_generic.svg",
        target_url="/",
        price_rsd=1200,
        days_count=7,
        status="rejected",
        admin_note="[BANNER_RESERVED_PAID]"
    )
    adv.advertiser_reserved_rsd = float(adv.advertiser_reserved_rsd or 0) + 1200
    old_withdrawal = Withdrawal(
        user_id=db.query(User).filter(User.role=="korisnik").first().id,
        amount_rsd=500,
        payment_method="bank",
        payment_details="audit",
        status="pending",
        created_at=datetime.utcnow() - timedelta(days=5)
    )
    db.add(expired)
    db.add(rejected)
    db.add(old_withdrawal)
    db.commit()
    expired_id = expired.id
    rejected_id = rejected.id
    withdrawal_id = old_withdrawal.id
finally:
    db.close()

r = admin.post("/admin/automation/run-v11823", follow_redirects=False)
local = r.status_code in (302, 303)
print(("OK" if local else "FAIL"), "ADMIN_RUN_AUTOMATION", r.status_code, r.headers.get("location"))
ok = ok and local

db = SessionLocal()
try:
    expired = db.query(PaidAdBannerV111).filter(PaidAdBannerV111.id==expired_id).first()
    rejected = db.query(PaidAdBannerV111).filter(PaidAdBannerV111.id==rejected_id).first()
    w = db.query(Withdrawal).filter(Withdrawal.id==withdrawal_id).first()
    log_count = db.query(AutoEngineLogV114).filter(AutoEngineLogV114.event_type=="automation_run").count()

    local = expired.status == "expired"
    print(("OK" if local else "FAIL"), "EXPIRED_BANNER_STATUS", expired.status)
    ok = ok and local

    local = "[BANNER_RESERVED_PAID]" not in (rejected.admin_note or "")
    print(("OK" if local else "FAIL"), "REJECTED_RESERVED_RELEASED", rejected.admin_note)
    ok = ok and local

    local = "72h" in (w.admin_note or "")
    print(("OK" if local else "FAIL"), "STALE_WITHDRAWAL_FLAGGED", w.admin_note)
    ok = ok and local

    local = log_count > 0
    print(("OK" if local else "FAIL"), "AUTOMATION_LOG_CREATED", log_count)
    ok = ok and local
finally:
    db.close()

r = TestClient(app.main.app).get("/api/v1/v11/automation-health")
local = r.status_code == 200 and r.json().get("version") == "11.18.23"
print(("OK" if local else "FAIL"), "AUTOMATION_HEALTH", r.status_code, r.json() if r.status_code == 200 else r.text[:100])
ok = ok and local

r = TestClient(app.main.app).get("/api/v1/v11/automation-run")
local = r.status_code == 200 and r.json().get("status") == "ok"
print(("OK" if local else "FAIL"), "AUTOMATION_API_RUN", r.status_code)
ok = ok and local

r = admin.get("/admin/auto-engine-v114")
local = r.status_code == 200 and "Pokreni automatizaciju" in r.text
print(("OK" if local else "FAIL"), "ADMIN_AUTO_PAGE_BUTTON", r.status_code)
ok = ok and local

print("RESULT:", "PASS" if ok else "CHECK_FAILED")
raise SystemExit(0 if ok else 1)
