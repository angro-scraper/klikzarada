from fastapi.testclient import TestClient
from PIL import Image
from io import BytesIO
import app.main
from app.database import SessionLocal
from app.models import User, HomeBannerSlotV111, PaidAdBannerV111

app.main.startup()

def login(email, password):
    c = TestClient(app.main.app)
    r = c.post("/login", data={"email": email, "password": password}, follow_redirects=False)
    ok = r.status_code in (302, 303)
    print(("OK" if ok else "FAIL"), "LOGIN", email, r.status_code)
    return c, ok

ok=True
admin, ok_admin = login("admin@klikzarada.rs", "Admin123!")
adv, ok_adv = login("oglasivac@demo.rs", "Demo123!")
ok = ok and ok_admin and ok_adv

# prepare portrait image, to prove physical crop/resize packs it into banner size
img = Image.new("RGB", (300, 900), (220, 80, 80))
buf = BytesIO()
img.save(buf, format="PNG")
raw = buf.getvalue()

db = SessionLocal()
try:
    u = db.query(User).filter(User.email=="oglasivac@demo.rs").first()
    u.advertiser_budget_rsd = 100000
    slot = db.query(HomeBannerSlotV111).filter(HomeBannerSlotV111.code=="home_top_left").first()
    slot_id = slot.id
    db.commit()
finally:
    db.close()

title = "Packed Readable Banner Test"
body = "Tekst mora jasno da se vidi preko slike."

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
    files={"upload_image": ("portrait-test.png", raw, "image/png")},
    follow_redirects=False
)
local = r.status_code in (302,303)
print(("OK" if local else "FAIL"), "ADV_UPLOAD_PACK", r.status_code, r.headers.get("location"))
ok = ok and local

db = SessionLocal()
try:
    b = db.query(PaidAdBannerV111).filter(PaidAdBannerV111.title==title).order_by(PaidAdBannerV111.id.desc()).first()
    banner_id = b.id if b else None
    local = b is not None and b.image_url and "-packed-1400x360-" in b.image_url and b.image_url.endswith(".jpg")
    print(("OK" if local else "FAIL"), "PACKED_URL", getattr(b, "image_url", None))
finally:
    db.close()
ok = ok and local

r = admin.post(f"/admin/reklame-v111/banner/{banner_id}/active", data={"admin_note":"pack audit"}, follow_redirects=False)
local = r.status_code in (302,303)
print(("OK" if local else "FAIL"), "PUBLISH", r.status_code)
ok = ok and local

db = SessionLocal()
try:
    b = db.query(PaidAdBannerV111).filter(PaidAdBannerV111.id==banner_id).first()
    img_url = b.image_url
finally:
    db.close()

r = TestClient(app.main.app).get(img_url)
local = r.status_code == 200
print(("OK" if local else "FAIL"), "STATIC_PACKED_IMAGE", r.status_code)
ok = ok and local

if local:
    im = Image.open(BytesIO(r.content))
    local = im.size == (1400, 360)
    print(("OK" if local else "FAIL"), "PHYSICAL_DIMENSIONS", im.size)
    ok = ok and local

r = TestClient(app.main.app).get("/")
local = r.status_code == 200 and title in r.text and body in r.text and "banner-overlay-copy" in r.text and "-packed-1400x360-" in r.text
print(("OK" if local else "FAIL"), "HOME_OVERLAY_READABLE", r.status_code)
ok = ok and local

css = TestClient(app.main.app).get("/static/css/style.css")
local = css.status_code == 200 and "V11.18.28 final homepage banner polishing" in css.text
print(("OK" if local else "FAIL"), "CSS_MARKER", css.status_code)
ok = ok and local

print("RESULT:", "PASS" if ok else "CHECK_FAILED")
raise SystemExit(0 if ok else 1)
