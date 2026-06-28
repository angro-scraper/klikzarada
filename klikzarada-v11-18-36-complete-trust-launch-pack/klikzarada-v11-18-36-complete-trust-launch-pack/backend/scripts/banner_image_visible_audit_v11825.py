from fastapi.testclient import TestClient
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

r = adv.post(
    "/oglasivac/reklame-v111/maker",
    data={
        "slot_id": str(slot_id),
        "title": "Visible Image Banner Test",
        "body": "Slika mora da se vidi direktno.",
        "target_url": "/",
        "days_count": "7",
        "theme": "blue",
        "accent": "#ffffff",
        "icon": "cart",
        "cta": "Klikni",
        "image_fit": "cover",
    },
    files={"upload_image": ("visible-banner.png", png, "image/png")},
    follow_redirects=False
)
local = r.status_code in (302,303)
print(("OK" if local else "FAIL"), "UPLOAD_BANNER_POST", r.status_code, r.headers.get("location"))
ok = ok and local

db = SessionLocal()
try:
    b = db.query(PaidAdBannerV111).filter(PaidAdBannerV111.title=="Visible Image Banner Test").order_by(PaidAdBannerV111.id.desc()).first()
    banner_id = b.id if b else None
    local = b is not None and b.image_url and b.image_url.startswith("/static/uploads/banners/") and not b.image_url.endswith("-fit.svg")
    print(("OK" if local else "FAIL"), "RAW_UPLOAD_IMAGE_URL", getattr(b, "image_url", None))
finally:
    db.close()
ok = ok and local

r = admin.post(f"/admin/reklame-v111/banner/{banner_id}/active", data={"admin_note":"visible image audit"}, follow_redirects=False)
local = r.status_code in (302,303)
print(("OK" if local else "FAIL"), "ADMIN_PUBLISH", r.status_code, r.headers.get("location"))
ok = ok and local

r = TestClient(app.main.app).get("/")
local = r.status_code == 200 and "Visible Image Banner Test" in r.text and "/static/uploads/banners/" in r.text and "banner-image-only" in r.text
print(("OK" if local else "FAIL"), "HOME_DIRECT_IMAGE", r.status_code)
ok = ok and local

db = SessionLocal()
try:
    b = db.query(PaidAdBannerV111).filter(PaidAdBannerV111.id==banner_id).first()
    r = TestClient(app.main.app).get(b.image_url)
    local = r.status_code == 200
    print(("OK" if local else "FAIL"), "UPLOADED_IMAGE_STATIC", r.status_code)
finally:
    db.close()
ok = ok and local

css = TestClient(app.main.app).get("/static/css/style.css")
local = css.status_code == 200 and "V11.18.25 visible uploaded banner images" in css.text
print(("OK" if local else "FAIL"), "CSS_FIX_MARKER", css.status_code)
ok = ok and local

print("RESULT:", "PASS" if ok else "CHECK_FAILED")
raise SystemExit(0 if ok else 1)
