from fastapi.testclient import TestClient
import app.main
c=TestClient(app.main.app)
ok=True
need=[
"kz1189-page","Premium banner za oglašivače","Zarada za korisnike","dashboard-card",
"SPONZORSKI BANNERI NA POČETNOJ","KAMPANJA NA PRVOM MESTU","ISTAKNUTI ZADACI",
"kz1189-stats","Spremni da počnete","kz1189-ad-slots","kz1189-footer"
]
for path in ["/","/pocetna"]:
    r=c.get(path)
    local=r.status_code==200 and all(x in r.text for x in need)
    print(("OK" if local else "FAIL"), path, r.status_code)
    ok=ok and local
r=c.get("/static/css/style.css?v=1189")
local=r.status_code==200 and "V11.18.9 FULL PREMIUM HOME" in r.text and ".kz1189-hero .dashboard-card" in r.text
print(("OK" if local else "FAIL"), "/static/css/style.css", r.status_code)
ok=ok and local
for p in ["/static/img/icon-wallet.svg","/static/img/ad-megaphone.svg","/static/img/trophy.svg"]:
    rr=c.get(p)
    local=rr.status_code==200 and "<svg" in rr.text
    print(("OK" if local else "FAIL"), p, rr.status_code)
    ok=ok and local
print("RESULT:", "PASS" if ok else "CHECK_FAILED")
raise SystemExit(0 if ok else 1)
