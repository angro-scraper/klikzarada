from fastapi.testclient import TestClient
from bs4 import BeautifulSoup
import app.main

app.main.startup()
c=TestClient(app.main.app)

def login_admin():
    cl=TestClient(app.main.app)
    r=cl.post("/login", data={"email":"admin@klikzarada.rs","password":"Admin123!"}, follow_redirects=False)
    ok=r.status_code in (302,303)
    print(("OK" if ok else "FAIL"), "ADMIN_LOGIN", r.status_code, r.headers.get("location"))
    return cl, ok

ok=True
admin, local = login_admin()
ok = ok and local

r = c.get("/api/v1/v11/banner-slots-health")
local = r.status_code == 200 and r.json().get("count") == 9 and r.json().get("expected") == 9
print(("OK" if local else "FAIL"), "BANNER_SLOTS_HEALTH", r.status_code, r.json() if r.status_code == 200 else r.text[:200])
ok = ok and local

r = admin.get("/admin/reklame-v111")
local = r.status_code == 200
print(("OK" if local else "FAIL"), "ADMIN_REKLAME_PAGE", r.status_code)
ok = ok and local

soup = BeautifulSoup(r.text, "html.parser")
slot_forms = [f for f in soup.find_all("form") if "/admin/reklame-v111/slot/" in (f.get("action") or "")]
local = len(slot_forms) == 9
print(("OK" if local else "FAIL"), "SLOT_FORMS_9", len(slot_forms))
ok = ok and local

codes = [x["code"] for x in c.get("/api/v1/v11/banner-slots-health").json()["slots"]]
for code in codes:
    local = code in r.text
    print(("OK" if local else "FAIL"), "SLOT_VISIBLE", code)
    ok = ok and local

quick = soup.find("form", attrs={"action":"/admin/reklame-v111/quick-banner"})
local = quick is not None
print(("OK" if local else "FAIL"), "QUICK_BANNER_FORM")
ok = ok and local

if slot_forms:
    first = slot_forms[0]
    action = first.get("action")
    data = {
        "title":"Audit slot naslov",
        "placement":"home_top",
        "width_label":"half",
        "price_rsd":"5555",
        "is_active":"yes"
    }
    rr = admin.post(action, data=data, follow_redirects=False)
    local = rr.status_code in (302,303)
    print(("OK" if local else "FAIL"), "SLOT_EDIT_POST", action, rr.status_code, rr.headers.get("location"))
    ok = ok and local

# create quick banner on first slot
health = c.get("/api/v1/v11/banner-slots-health").json()
slot_id = health["slots"][0]["id"]
# Find advertiser id from select
adv_option = quick.find("select", attrs={"name":"advertiser_id"}).find("option") if quick else None
if adv_option:
    adv_id = adv_option.get("value")
    rr = admin.post("/admin/reklame-v111/quick-banner", data={
        "advertiser_id": adv_id,
        "slot_id": str(slot_id),
        "title": "Audit banner 9 slotova",
        "body": "Test admin banner podešavanja.",
        "target_url": "/",
        "price_rsd": "0",
        "status": "active"
    }, follow_redirects=False)
    local = rr.status_code in (302,303)
    print(("OK" if local else "FAIL"), "QUICK_BANNER_POST", rr.status_code, rr.headers.get("location"))
    ok = ok and local
else:
    print("FAIL", "NO_ADVERTISER_OPTION")
    ok = False

r2 = admin.get("/admin/reklame-v111")
local = r2.status_code == 200 and "Audit banner 9 slotova" in r2.text
print(("OK" if local else "FAIL"), "QUICK_BANNER_VISIBLE", r2.status_code)
ok = ok and local

print("RESULT:", "PASS" if ok else "CHECK_FAILED")
raise SystemExit(0 if ok else 1)
