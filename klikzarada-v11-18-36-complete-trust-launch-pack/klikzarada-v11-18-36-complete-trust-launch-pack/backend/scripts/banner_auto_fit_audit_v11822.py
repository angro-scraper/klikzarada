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

png = b"\x89PNG\r\n\x1a\n" + b"0"*256

r = adv.post(
    "/oglasivac/reklame-v111/maker",
    data={
        "slot_id": str(slot_id),
        "title": "Auto Fit Banner Test",
        "body": "Test auto fit slike.",
        "target_url": "/",
        "days_count": "7",
        "theme": "blue",
        "accent": "#ffffff",
        "icon": "cart",
        "cta": "Klikni",
        "image_fit": "cover",
    },
    files={"upload_image": ("wide-test.png", png, "image/png")},
    follow_redirects=False
)
local = r.status_code in (302, 303)
print(("OK" if local else "FAIL"), "ADV_AUTO_FIT_POST", r.status_code, r.headers.get("location"))
ok = ok and local

db = SessionLocal()
try:
    b = db.query(PaidAdBannerV111).filter(PaidAdBannerV111.title=="Auto Fit Banner Test").order_by(PaidAdBannerV111.id.desc()).first()
    local = b is not None and b.image_url and b.image_url.startswith("/static/generated_banners/") and b.image_url.endswith(".svg")
    print(("OK" if local else "FAIL"), "BANNER_IMAGE_IS_FITTED_SVG", getattr(b, "image_url", None))
    banner_id = b.id if b else None
finally:
    db.close()
ok = ok and local

if banner_id:
    r = admin.post(f"/admin/reklame-v111/banner/{banner_id}/active", data={"admin_note":"auto fit audit"}, follow_redirects=False)
    local = r.status_code in (302, 303)
    print(("OK" if local else "FAIL"), "ADMIN_PUBLISH", r.status_code, r.headers.get("location"))
    ok = ok and local

    r = TestClient(app.main.app).get("/")
    local = r.status_code == 200 and "Auto Fit Banner Test" in r.text and "/static/generated_banners/" in r.text and "banner-image-only" in r.text
    print(("OK" if local else "FAIL"), "HOME_USES_FITTED_IMAGE_ONLY", r.status_code)
    ok = ok and local

# Static generated svg should be accessible
if banner_id:
    db = SessionLocal()
    try:
        b = db.query(PaidAdBannerV111).filter(PaidAdBannerV111.id==banner_id).first()
        path = b.image_url
    finally:
        db.close()
    r = TestClient(app.main.app).get(path)
    local = r.status_code == 200 and "preserveAspectRatio" in r.text and "xMidYMid slice" in r.text
    print(("OK" if local else "FAIL"), "FITTED_SVG_STATIC", r.status_code)
    ok = ok and local

print("RESULT:", "PASS" if ok else "CHECK_FAILED")
raise SystemExit(0 if ok else 1)
