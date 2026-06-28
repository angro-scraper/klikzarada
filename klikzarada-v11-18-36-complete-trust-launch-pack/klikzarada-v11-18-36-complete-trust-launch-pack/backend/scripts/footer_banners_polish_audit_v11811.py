from fastapi.testclient import TestClient
from bs4 import BeautifulSoup
import app.main

app.main.startup()
c=TestClient(app.main.app)
ok=True

for path in ["/", "/pocetna"]:
    r=c.get(path)
    local = r.status_code == 200 and "kz1189-footer" in r.text and "kz1189-ad-slots" in r.text
    print(("OK" if local else "FAIL"), path, r.status_code)
    ok = ok and local

r=c.get("/")
soup=BeautifulSoup(r.text, "html.parser")
for href in sorted(set(a.get("href") for a in soup.find_all("a", href=True))):
    rr=c.get(href, follow_redirects=False)
    good=rr.status_code in (200,301,302,303,307,308)
    print(("OK" if good else "FAIL"), "LINK", href, rr.status_code, rr.headers.get("location"))
    ok = ok and good

css=c.get("/static/css/style.css?v=11811")
need=[
    "V11.18.11 FOOTER + 3 BANNERS FINAL POLISH",
    ".kz1189-ad-slots a{",
    "min-height:112px",
    ".kz1189-footer{",
    "min-height:148px"
]
local=css.status_code==200 and all(x in css.text for x in need)
print(("OK" if local else "FAIL"), "CSS", css.status_code)
ok = ok and local

print("RESULT:", "PASS" if ok else "CHECK_FAILED")
raise SystemExit(0 if ok else 1)
