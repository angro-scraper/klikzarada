from fastapi.testclient import TestClient
import app.main

c=TestClient(app.main.app)
ok=True

for path, need in [
    ("/", ["kz1186-page", "SPONZORSKI BANNERI", "KAMPANJA NA PRVOM MESTU"]),
    ("/pocetna", ["kz1186-page", "kz1186-top-ads", "kz1186-bottom-ads"]),
]:
    r=c.get(path)
    text=r.text
    local = r.status_code == 200 and all(x in text for x in need)
    print(("OK" if local else "FAIL"), path, r.status_code)
    ok = ok and local

r=c.get("/static/css/style.css?v=1187")
css=r.text
css_need = [
    "V11.18.7B REAL KZ1186 CONTRAST FIX",
    ".kz1186-sponsors .sponsor",
    ".kz1186-top-ads .top-ad",
    ".kz1186-bottom-ads .bottom-ad",
    "color:#ffffff!important"
]
local = r.status_code == 200 and all(x in css for x in css_need)
print(("OK" if local else "FAIL"), "/static/css/style.css", r.status_code)
ok = ok and local

print("RESULT:", "PASS" if ok else "CHECK_FAILED")
raise SystemExit(0 if ok else 1)
