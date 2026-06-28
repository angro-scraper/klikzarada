from fastapi.testclient import TestClient
from bs4 import BeautifulSoup
import app.main
from app.database import SessionLocal
from app.models import PaidAdBannerV111, HomeBannerSlotV111, User

app.main.startup()

def login_admin():
    c=TestClient(app.main.app)
    r=c.post("/login", data={"email":"admin@klikzarada.rs","password":"Admin123!"}, follow_redirects=False)
    ok=r.status_code in (302,303)
    print(("OK" if ok else "FAIL"), "ADMIN_LOGIN", r.status_code, r.headers.get("location"))
    return c, ok

ok=True
admin, local = login_admin()
ok = ok and local

r = admin.get("/admin/reklame-v111")
local = r.status_code == 200 and "Banneri i objavljivanje" in r.text and "Objavi bez naplate" in r.text
print(("OK" if local else "FAIL"), "ADMIN_BANNER_PAGE_POLISH", r.status_code)
ok = ok and local

soup = BeautifulSoup(r.text, "html.parser")
slot_forms = [f for f in soup.find_all("form") if "/admin/reklame-v111/slot/" in (f.get("action") or "")]
local = len(slot_forms) == 9
print(("OK" if local else "FAIL"), "SLOT_FORMS_9", len(slot_forms))
ok = ok and local

# ensure health has 9 slots
h = admin.get("/api/v1/v11/banner-slots-health")
local = h.status_code == 200 and h.json().get("count") == 9
print(("OK" if local else "FAIL"), "HEALTH_9", h.status_code, h.json() if h.status_code == 200 else "")
ok = ok and local

db = SessionLocal()
try:
    adv = db.query(User).filter(User.role=="oglasivac").first()
    slot = db.query(HomeBannerSlotV111).filter(HomeBannerSlotV111.code=="home_top_left").first()
    adv_id = adv.id
    slot_id = slot.id
finally:
    db.close()

# Create pending banner with high price to test normal publish fails cleanly, then force publish works
rr = admin.post("/admin/reklame-v111/quick-banner", data={
    "advertiser_id": str(adv_id),
    "slot_id": str(slot_id),
    "title": "Audit pending banner publish",
    "body": "Audit test",
    "target_url": "/",
    "price_rsd": "999999999",
    "status": "pending"
}, follow_redirects=False)
local = rr.status_code in (302,303)
print(("OK" if local else "FAIL"), "CREATE_PENDING_BANNER", rr.status_code, rr.headers.get("location"))
ok = ok and local

db = SessionLocal()
try:
    b = db.query(PaidAdBannerV111).filter(PaidAdBannerV111.title=="Audit pending banner publish").order_by(PaidAdBannerV111.id.desc()).first()
    banner_id = b.id if b else None
finally:
    db.close()

local = banner_id is not None
print(("OK" if local else "FAIL"), "BANNER_CREATED_ID", banner_id)
ok = ok and local

if banner_id:
    rr = admin.post(f"/admin/reklame-v111/banner/{banner_id}/active", data={"admin_note":"normal publish audit"}, follow_redirects=False)
    local = rr.status_code in (302,303)
    print(("OK" if local else "FAIL"), "PUBLISH_NORMAL_REDIRECT", rr.status_code, rr.headers.get("location"))
    ok = ok and local

    rr = admin.post(f"/admin/reklame-v111/banner/{banner_id}/active", data={"admin_note":"force publish audit", "force_publish":"yes"}, follow_redirects=False)
    local = rr.status_code in (302,303)
    print(("OK" if local else "FAIL"), "PUBLISH_FORCE_REDIRECT", rr.status_code, rr.headers.get("location"))
    ok = ok and local

    db = SessionLocal()
    try:
        b = db.query(PaidAdBannerV111).filter(PaidAdBannerV111.id==banner_id).first()
        local = b is not None and b.status == "active" and b.starts_at is not None
        print(("OK" if local else "FAIL"), "BANNER_ACTIVE_IN_DB", getattr(b, "status", None), getattr(b, "starts_at", None))
        ok = ok and local
    finally:
        db.close()

# Quick publish active should be active immediately
rr = admin.post("/admin/reklame-v111/quick-banner", data={
    "advertiser_id": str(adv_id),
    "slot_id": str(slot_id),
    "title": "Audit quick active banner",
    "body": "Audit quick active",
    "target_url": "/",
    "price_rsd": "0",
    "status": "active"
}, follow_redirects=False)
local = rr.status_code in (302,303)
print(("OK" if local else "FAIL"), "QUICK_ACTIVE_POST", rr.status_code, rr.headers.get("location"))
ok = ok and local

db = SessionLocal()
try:
    b = db.query(PaidAdBannerV111).filter(PaidAdBannerV111.title=="Audit quick active banner").order_by(PaidAdBannerV111.id.desc()).first()
    local = b is not None and b.status == "active" and b.starts_at is not None
    print(("OK" if local else "FAIL"), "QUICK_ACTIVE_IN_DB", getattr(b, "status", None), getattr(b, "starts_at", None))
    ok = ok and local
finally:
    db.close()

r2 = admin.get("/admin/reklame-v111")
local = r2.status_code == 200 and "Audit quick active banner" in r2.text
print(("OK" if local else "FAIL"), "BANNER_VISIBLE_ADMIN", r2.status_code)
ok = ok and local

print("RESULT:", "PASS" if ok else "CHECK_FAILED")
raise SystemExit(0 if ok else 1)
