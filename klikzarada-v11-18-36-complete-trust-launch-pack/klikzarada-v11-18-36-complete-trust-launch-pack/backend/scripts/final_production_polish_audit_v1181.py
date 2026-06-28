from fastapi.testclient import TestClient
import app.main

def login(c,email,password):
    r=c.post("/login", data={"email":email,"password":password}, follow_redirects=False)
    print("LOGIN", email, r.status_code, r.headers.get("location"))
    return r.status_code in (302,303)

def check(c,path,must=None,must_not=None):
    r=c.get(path)
    text=r.text
    ok=r.status_code==200
    if must:
        ok=ok and all(x in text for x in must)
    if must_not:
        ok=ok and all(x not in text for x in must_not)
    print(("OK" if ok else "FAIL"), path, r.status_code)
    if not ok:
        print(text[:300].replace("\n"," "))
    return ok

res=True
c=TestClient(app.main.app)
res = check(c,"/",["kz118-approved-final","kz118-hero-card","kz118-banner-grid","kz118-top-campaign-card"],["home171-split"]) and res
res = check(c,"/pocetna",["kz118-approved-final","kz118-hero-card"]) and res

c=TestClient(app.main.app)
login(c,"admin@klikzarada.rs","Admin123!")
res = check(c,"/admin/reklame-v111",["premium-admin-hub","tone-green","active"],["premium-command-bar"]) and res
res = check(c,"/admin/analitika-v117",["premium-admin-hub","tone-amber","active"],["premium-command-bar"]) and res

c=TestClient(app.main.app)
login(c,"korisnik@demo.rs","Demo123!")
res = check(c,"/korisnik/panel",["kz118-quick-panel-links","Novčanik","Bedževi"]) and res
res = check(c,"/korisnik/wallet",["NOVČANIK"]) and res
res = check(c,"/korisnik/isplate",["ISPLATE"]) and res
res = check(c,"/korisnik/bedzevi",["premium-badges-grid"]) and res

c=TestClient(app.main.app)
login(c,"oglasivac@demo.rs","Demo123!")
res = check(c,"/oglasivac/panel",["kz118-quick-panel-links","Banner reklame"]) and res
res = check(c,"/oglasivac/reklame-v111") and res

print("RESULT:", "PASS" if res else "CHECK_FAILED")
raise SystemExit(0 if res else 1)
