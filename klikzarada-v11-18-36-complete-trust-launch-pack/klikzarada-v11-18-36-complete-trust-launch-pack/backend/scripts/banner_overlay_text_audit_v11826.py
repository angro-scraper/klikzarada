from fastapi.testclient import TestClient
import app.main
from app.database import SessionLocal
from app.models import User, HomeBannerSlotV111, PaidAdBannerV111

app.main.startup()

def login(email, password):
    c = TestClient(app.main.app)
    r = c.post("/login", data={"email": email, "password": password}, follow_redirects=False)
    return c, r.status_code in (302,303)

ok=True
admin, ok_admin = login("admin@klikzarada.rs", "Admin123!")
adv, ok_adv = login("oglasivac@demo.rs", "Demo123!")
ok = ok and ok_admin and ok_adv

db = SessionLocal()
try:
    u = db.query(User).filter(User.email=="oglasivac@demo.rs").first()
    u.advertiser_budget_rsd = 100000
    slot = db.query(HomeBannerSlotV111).filter(HomeBannerSlotV111.code=="home_top_left").first()
    slot_id = slot.id
    db.commit()
finally:
    db.close()

png = b"\x89PNG\r\n\x1a\n" + b"0"*512
title = "Overlay Naslov Test"
body = "Ovo je tekst preko cele slike."

r = adv.post(
    "/oglasivac/reklame-v111/maker",
    data={
        "slot_id": str(slot_id),
        "title": title,
        "body": body,
        "target_url": "/",
        "days_count": "7",
        "theme": "blue",
        "accent": "#ffffff",
        "icon": "cart",
        "cta": "Klikni",
        "image_fit": "cover",
    },
    files={"upload_image": ("overlay-banner.png", png, "image/png")},
    follow_redirects=False
)
local = r.status_code in (302,303)
print(("OK" if local else "FAIL"), "UPLOAD", r.status_code)
ok = ok and local

db = SessionLocal()
try:
    b = db.query(PaidAdBannerV111).filter(PaidAdBannerV111.title==title).order_by(PaidAdBannerV111.id.desc()).first()
    banner_id = b.id
finally:
    db.close()

r = admin.post(f"/admin/reklame-v111/banner/{banner_id}/active", data={"admin_note":"overlay audit"}, follow_redirects=False)
local = r.status_code in (302,303)
print(("OK" if local else "FAIL"), "PUBLISH", r.status_code)
ok = ok and local

r = TestClient(app.main.app).get("/")
local = r.status_code == 200 and title in r.text and body in r.text and "banner-overlay" in r.text and "--banner-img:url('/static/uploads/banners/" in r.text
print(("OK" if local else "FAIL"), "HOME_OVERLAY_TEXT", r.status_code)
ok = ok and local

css = TestClient(app.main.app).get("/static/css/style.css")
local = css.status_code == 200 and "V11.18.26 banner overlay text fix" in css.text
print(("OK" if local else "FAIL"), "CSS", css.status_code)
ok = ok and local

print("RESULT:", "PASS" if ok else "CHECK_FAILED")
raise SystemExit(0 if ok else 1)
