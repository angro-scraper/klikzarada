from fastapi.testclient import TestClient
import app.main

def login(c,email,password):
    r=c.post("/login", data={"email":email,"password":password}, follow_redirects=False)
    print("LOGIN", email, r.status_code, r.headers.get("location"))
    return r.status_code in (302,303)

def check(c,path,must=None):
    r=c.get(path)
    text=r.text if hasattr(r,"text") else ""
    ok=r.status_code in (200,303)
    if must:
        for m in must:
            ok=ok and (m in text)
    print(("OK" if ok else "FAIL"), path, r.status_code)
    if not ok: print(text[:300].replace("\n"," "))
    return ok

res=True
c=TestClient(app.main.app)
res=check(c,"/",["premium-home-hero","premium-balance-box"]) and res
login(c,"korisnik@demo.rs","Demo123!")
for p,m in [
    ("/korisnik/panel",["kz-user-dashboard-grid"]),
    ("/korisnik/wallet",["NOVČANIK"]),
    ("/korisnik/isplate",["ISPLATE"]),
    ("/korisnik/bedzevi",["premium-badges-grid"]),
    ("/korisnik/motivacija-v115",["Zaključano"]),
    ("/korisnik/referral",["premium-copy-box"]),
    ("/api/v1/v11/user-pages-fix-audit",None),
]:
    res=check(c,p,m) and res
print("RESULT:", "PASS" if res else "CHECK_FAILED")
raise SystemExit(0 if res else 1)
