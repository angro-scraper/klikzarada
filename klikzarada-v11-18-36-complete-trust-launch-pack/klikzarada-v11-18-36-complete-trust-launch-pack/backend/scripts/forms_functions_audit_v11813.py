from fastapi.testclient import TestClient
from bs4 import BeautifulSoup
import time, re
import app.main

app.main.startup()

def c():
    return TestClient(app.main.app)

def login(email, password):
    cl = c()
    r = cl.post("/login", data={"email": email, "password": password}, follow_redirects=False)
    ok = r.status_code in (302, 303)
    print(("OK" if ok else "FAIL"), "LOGIN", email, r.status_code, r.headers.get("location"))
    return cl, ok

def check_get(cl, path, label):
    r = cl.get(path, follow_redirects=False)
    ok = r.status_code in (200, 301, 302, 303, 307, 308)
    print(("OK" if ok else "FAIL"), label, path, r.status_code, r.headers.get("location"))
    return ok, r

def check_post_redirect(cl, path, data, label, expected=(200, 302, 303, 307, 308, 400, 422)):
    r = cl.post(path, data=data, follow_redirects=False)
    ok = r.status_code in expected
    print(("OK" if ok else "FAIL"), label, path, r.status_code, r.headers.get("location"))
    if not ok:
        print(r.text[:500].replace("\n", " "))
    return ok, r

ok=True

# 1. Login forms
admin, ok_admin = login("admin@klikzarada.rs", "Admin123!")
user, ok_user = login("korisnik@demo.rs", "Demo123!")
adv, ok_adv = login("oglasivac@demo.rs", "Demo123!")
ok = ok and ok_admin and ok_user and ok_adv

# Bad login should not crash
r = c().post("/login", data={"email":"nema@test.rs","password":"pogresno"}, follow_redirects=False)
local = r.status_code in (200, 302, 303, 400, 401)
print(("OK" if local else "FAIL"), "LOGIN_BAD", r.status_code)
ok = ok and local

# 2. Registration page and demo registration POST with unique email
stamp = int(time.time())
reg_data = {
    "full_name": "Audit Korisnik",
    "email": f"audit{stamp}@demo.rs",
    "password": "Demo123!",
    "role": "korisnik",
    "city": "Niš",
    "phone": f"+38160{stamp % 1000000:06d}",
    "age_group": "25-34",
    "interests": "test",
    "device": "desktop",
}
local, _ = check_get(c(), "/registracija", "REG_PAGE")
ok = ok and local
r = c().post("/registracija", data=reg_data, follow_redirects=False)
local = r.status_code in (302, 303, 200)
print(("OK" if local else "FAIL"), "REG_POST_KORISNIK", r.status_code, r.headers.get("location"))
ok = ok and local

# 3. Public task flow: task list and detail buttons
local, r = check_get(c(), "/zadaci", "TASK_LIST")
ok = ok and local
soup = BeautifulSoup(r.text, "html.parser")
task_links = [a.get("href") for a in soup.find_all("a", href=True) if re.match(r"^/zadaci/\d+$", a.get("href",""))]
if task_links:
    local, _ = check_get(user, task_links[0], "TASK_DETAIL_USER")
    ok = ok and local
else:
    print("FAIL", "TASK_DETAIL_LINK_MISSING")
    ok = False

# 4. User protected functions/pages
for path in ["/korisnik/panel", "/korisnik/wallet", "/korisnik/isplate", "/korisnik/bedzevi", "/korisnik/referral", "/korisnik/dokazi", "/korisnik/motivacija-v115"]:
    local, _ = check_get(user, path, "USER_PAGE")
    ok = ok and local

# 5. Withdrawal request form existence / safe post
# It may require min balance; acceptable statuses include redirect or validation page.
check_post_redirect(user, "/korisnik/isplate/zahtev", {"amount_rsd":"500", "method":"bank", "note":"audit test"}, "USER_WITHDRAWAL_POST", expected=(200,302,303,400,422))

# 6. Advertiser protected functions/pages
for path in ["/oglasivac/panel", "/oglasivac/kampanje", "/oglasivac/nova-kampanja", "/oglasivac/budzet", "/oglasivac/reklame-v111", "/oglasivac/boost-v111", "/oglasivac/izvestaji", "/oglasivac/fakture", "/oglasivac/dokazi"]:
    local, _ = check_get(adv, path, "ADV_PAGE")
    ok = ok and local

# 7. Advertiser budget topup request
local, _ = check_post_redirect(adv, "/oglasivac/budzet/zahtev", {"amount_rsd":"1000", "note":"audit dopuna"}, "ADV_BUDGET_POST", expected=(302,303,200,400,422))
ok = ok and local

# 8. Advertiser banner/create ad form if present
local, r = check_get(adv, "/oglasivac/reklame-v111", "ADV_ADS_PAGE")
ok = ok and local
soup = BeautifulSoup(r.text, "html.parser")
forms = [(f.get("method","get").lower(), f.get("action","")) for f in soup.find_all("form")]
print("INFO", "ADV_ADS_FORMS", forms)
# Don't force ad creation because field names vary; page must render and forms must have action.
for method, action in forms:
    local = bool(action)
    print(("OK" if local else "FAIL"), "ADV_ADS_FORM_ACTION", method.upper(), action)
    ok = ok and local

# 9. Admin pages and visible forms
for path in ["/admin/v11", "/admin/kampanje", "/admin/reklame-v111", "/admin/analitika-v117", "/admin/finansije", "/admin/isplate", "/admin/dokazi"]:
    local, r = check_get(admin, path, "ADMIN_PAGE")
    ok = ok and local
    if local:
        soup = BeautifulSoup(r.text, "html.parser")
        for f in soup.find_all("form"):
            action = f.get("action","")
            method = f.get("method","get").lower()
            local2 = bool(action)
            print(("OK" if local2 else "FAIL"), "ADMIN_FORM_ACTION", path, method.upper(), action)
            ok = ok and local2

# 10. Unauthorized protected pages should protect, not crash
for path in ["/korisnik/panel", "/oglasivac/panel", "/admin/v11"]:
    r = c().get(path, follow_redirects=False)
    local = r.status_code in (302, 303, 401, 403)
    print(("OK" if local else "FAIL"), "AUTH_GUARD", path, r.status_code, r.headers.get("location"))
    ok = ok and local

print("RESULT:", "PASS" if ok else "CHECK_FAILED")
raise SystemExit(0 if ok else 1)
