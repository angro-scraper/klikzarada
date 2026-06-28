from fastapi.testclient import TestClient
from bs4 import BeautifulSoup
import app.main
from app.database import SessionLocal
from app.models import User, HomeBannerSlotV111, PaidAdBannerV111

app.main.startup()

def login(email, password):
    c = TestClient(app.main.app)
    r = c.post("/login", data={"email": email, "password": password}, follow_redirects=False)
    ok = r.status_code in (302, 303)
    print(("OK" if ok else "FAIL"), "LOGIN", email, r.status_code, r.headers.get("location"))
    return c, ok

ok=True
admin, ok_admin = login("admin@klikzarada.rs", "Admin123!")
adv, ok_adv = login("oglasivac@demo.rs", "Demo123!")
ok = ok and ok_admin and ok_adv

r = adv.get("/oglasivac/reklame-v111")
local = r.status_code == 200 and "data-preview-target" in r.text and "Upload slike sa računara" in r.text and "kzBannerPreviewInit" in r.text
print(("OK" if local else "FAIL"), "ADVERTISER_UPLOAD_PREVIEW_UI", r.status_code)
ok = ok and local

r = admin.get("/admin/reklame-v111")
local = r.status_code == 200 and "data-preview-target" in r.text and "Upload slike sa računara" in r.text and "kzAdminBannerPreviewInit" in r.text
print(("OK" if local else "FAIL"), "ADMIN_UPLOAD_PREVIEW_UI", r.status_code)
ok = ok and local

# Prepare budget and slot
db = SessionLocal()
try:
    u = db.query(User).filter(User.email=="oglasivac@demo.rs").first()
    u.advertiser_budget_rsd = 100000
    slot = db.query(HomeBannerSlotV111).filter(HomeBannerSlotV111.code=="home_bottom_1").first()
    db.commit()
    slot_id = slot.id
finally:
    db.close()

png = b"\x89PNG\r\n\x1a\n" + b"0"*128

# Advertiser maker upload
r = adv.post(
    "/oglasivac/reklame-v111/maker",
    data={
        "slot_id": str(slot_id),
        "title": "Upload Preview Test Oglasivac",
        "body": "Banner upload test",
        "target_url": "/",
        "days_count": "7",
        "theme": "blue",
        "accent": "#ffffff",
        "icon": "cart",
        "cta": "Klikni",
        "image_fit": "cover",
    },
    files={"upload_image": ("test-banner.png", png, "image/png")},
    follow_redirects=False
)
local = r.status_code in (302, 303)
print(("OK" if local else "FAIL"), "ADV_UPLOAD_POST", r.status_code, r.headers.get("location"))
ok = ok and local

db = SessionLocal()
try:
    b = db.query(PaidAdBannerV111).filter(PaidAdBannerV111.title=="Upload Preview Test Oglasivac").order_by(PaidAdBannerV111.id.desc()).first()
    local = b is not None and b.image_url and b.image_url.startswith("/static/uploads/banners/")
    print(("OK" if local else "FAIL"), "ADV_UPLOAD_DB_IMAGE", getattr(b, "image_url", None))
finally:
    db.close()
ok = ok and local

# Admin maker upload
db = SessionLocal()
try:
    adv_user = db.query(User).filter(User.email=="oglasivac@demo.rs").first()
    adv_id = adv_user.id
finally:
    db.close()

r = admin.post(
    "/admin/reklame-v111/maker",
    data={
        "advertiser_id": str(adv_id),
        "slot_id": str(slot_id),
        "title": "Upload Preview Test Admin",
        "body": "Admin upload test",
        "target_url": "/",
        "price_rsd": "0",
        "days_count": "7",
        "status": "active",
        "theme": "green",
        "accent": "#ffffff",
        "icon": "chart",
        "cta": "Pogledaj",
        "image_fit": "cover",
    },
    files={"upload_image": ("admin-banner.png", png, "image/png")},
    follow_redirects=False
)
local = r.status_code in (302, 303)
print(("OK" if local else "FAIL"), "ADMIN_UPLOAD_POST", r.status_code, r.headers.get("location"))
ok = ok and local

db = SessionLocal()
try:
    b = db.query(PaidAdBannerV111).filter(PaidAdBannerV111.title=="Upload Preview Test Admin").order_by(PaidAdBannerV111.id.desc()).first()
    local = b is not None and b.status == "active" and b.image_url and b.image_url.startswith("/static/uploads/banners/")
    print(("OK" if local else "FAIL"), "ADMIN_UPLOAD_DB_IMAGE", getattr(b, "status", None), getattr(b, "image_url", None))
finally:
    db.close()
ok = ok and local

css = TestClient(app.main.app).get("/static/css/style.css")
local = css.status_code == 200 and "V11.18.20 Banner upload + live preview" in css.text
print(("OK" if local else "FAIL"), "CSS_MARKER", css.status_code)
ok = ok and local

print("RESULT:", "PASS" if ok else "CHECK_FAILED")
raise SystemExit(0 if ok else 1)
