from fastapi.testclient import TestClient
from bs4 import BeautifulSoup
import time
import app.main
from app.database import SessionLocal
from app.models import User, PaidAdBannerV111, HomeBannerSlotV111

app.main.startup()

def login(email, password):
    c = TestClient(app.main.app)
    r = c.post("/login", data={"email":email,"password":password}, follow_redirects=False)
    ok = r.status_code in (302,303)
    print(("OK" if ok else "FAIL"), "LOGIN", email, r.status_code, r.headers.get("location"))
    return c, ok

ok=True
admin, aok = login("admin@klikzarada.rs", "Admin123!")
adv, vok = login("oglasivac@demo.rs", "Demo123!")
ok = ok and aok and vok

r = adv.get("/oglasivac/reklame-v111")
local = r.status_code == 200 and "Plati iz budžeta" in r.text
print(("OK" if local else "FAIL"), "ADVERTISER_BANNER_PAGE", r.status_code)
ok = ok and local
soup = BeautifulSoup(r.text, "html.parser")
slot_options = soup.select('select[name="slot_id"] option')
local = len(slot_options) == 9
print(("OK" if local else "FAIL"), "ADVERTISER_HAS_9_SLOTS", len(slot_options))
ok = ok and local

db = SessionLocal()
try:
    adv_user = db.query(User).filter(User.email=="oglasivac@demo.rs").first()
    adv_user.advertiser_budget_rsd = 100000
    db.commit()
    before_budget = float(adv_user.advertiser_budget_rsd or 0)
    slot = db.query(HomeBannerSlotV111).filter(HomeBannerSlotV111.code=="home_top_left").first()
    slot_id = slot.id
finally:
    db.close()

title = f"Audit Pocetna Banner {int(time.time())}"
rr = adv.post("/oglasivac/reklame-v111", data={
    "slot_id": str(slot_id),
    "title": title,
    "body": "Ovo je test banner koji mora da se pojavi na početnoj.",
    "image_url": "",
    "target_url": "/za-oglasivace",
    "days_count": "7"
}, follow_redirects=False)
local = rr.status_code in (302,303)
print(("OK" if local else "FAIL"), "ADVERTISER_CREATE_BANNER", rr.status_code, rr.headers.get("location"))
ok = ok and local

db = SessionLocal()
try:
    b = db.query(PaidAdBannerV111).filter(PaidAdBannerV111.title==title).order_by(PaidAdBannerV111.id.desc()).first()
    adv_user = db.query(User).filter(User.email=="oglasivac@demo.rs").first()
    local = b is not None and b.status == "pending" and "[BANNER_RESERVED_PAID]" in (b.admin_note or "") and float(adv_user.advertiser_budget_rsd or 0) < before_budget
    print(("OK" if local else "FAIL"), "BANNER_RESERVED_PENDING", getattr(b, "status", None), getattr(b, "admin_note", None), "budget", float(adv_user.advertiser_budget_rsd or 0), "before", before_budget)
    banner_id = b.id if b else None
finally:
    db.close()
ok = ok and local

rr = admin.post(f"/admin/reklame-v111/banner/{banner_id}/active", data={"admin_note":"audit approve"}, follow_redirects=False)
local = rr.status_code in (302,303)
print(("OK" if local else "FAIL"), "ADMIN_PUBLISH_RESERVED", rr.status_code, rr.headers.get("location"))
ok = ok and local

db = SessionLocal()
try:
    b = db.query(PaidAdBannerV111).filter(PaidAdBannerV111.id==banner_id).first()
    local = b is not None and b.status == "active" and b.starts_at is not None
    print(("OK" if local else "FAIL"), "BANNER_ACTIVE_DB", getattr(b, "status", None), getattr(b, "starts_at", None), getattr(b, "admin_note", None))
finally:
    db.close()
ok = ok and local

r = TestClient(app.main.app).get("/")
local = r.status_code == 200 and title in r.text and "Ovo je test banner" in r.text
print(("OK" if local else "FAIL"), "BANNER_VISIBLE_HOME", r.status_code)
ok = ok and local

r = admin.get("/admin/reklame-v111")
local = r.status_code == 200 and title in r.text
print(("OK" if local else "FAIL"), "BANNER_VISIBLE_ADMIN", r.status_code)
ok = ok and local

print("RESULT:", "PASS" if ok else "CHECK_FAILED")
raise SystemExit(0 if ok else 1)
