from fastapi.testclient import TestClient
import app.main

def login(c,email,password):
    r=c.post("/login", data={"email":email,"password":password}, follow_redirects=False)
    return r.status_code in (302,303)

def check(c,path,need=None):
    r=c.get(path)
    text=r.text
    ok=r.status_code==200 and (all(x in text for x in need) if need else True)
    print(("OK" if ok else "FAIL"), path, r.status_code)
    if not ok:
        print(text[:400].replace("\n"," "))
    return ok

res=True
c=TestClient(app.main.app)
res=check(c,"/",["kz1183-page","/static/img/shopmax.svg","kz1183-footer"]) and res

c=TestClient(app.main.app)
res=login(c,"admin@klikzarada.rs","Admin123!") and res
res=check(c,"/admin/reklame-v111",["premium-admin-hub"]) and res
res=check(c,"/admin/analitika-v117",["premium-admin-hub"]) and res

c=TestClient(app.main.app)
res=login(c,"korisnik@demo.rs","Demo123!") and res
res=check(c,"/korisnik/panel",["kz118-quick-panel-links","Novčanik","Bedževi"]) and res
res=check(c,"/korisnik/wallet",["NOVČANIK"]) and res

c=TestClient(app.main.app)
res=login(c,"oglasivac@demo.rs","Demo123!") and res
res=check(c,"/oglasivac/panel",["advertiser-links","Banner reklame"]) and res
res=check(c,"/oglasivac/reklame-v111") and res

for path in ["/static/img/shopmax.svg","/static/img/finance-pro.svg","/static/img/campaign-top.svg"]:
    rr=TestClient(app.main.app).get(path)
    ok=rr.status_code==200 and "<svg" in rr.text
    print(("OK" if ok else "FAIL"), path, rr.status_code)
    res=res and ok

print("RESULT:", "PASS" if res else "CHECK_FAILED")
raise SystemExit(0 if res else 1)
