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
# create a few visits
for p in ["/","/zadaci","/login"]:
    c.get(p)
login(c,"admin@klikzarada.rs","Admin123!")
for p,m in [
    ("/admin/analitika-v117",["ANALITIKA PLATFORME","Registrovani korisnici","Registrovani oglašivači"]),
    ("/admin/korisnici-baza-v117",["BAZA KORISNIKA"]),
    ("/admin/oglasivaci-baza-v117",["BAZA OGLAŠIVAČA"]),
    ("/admin/korisnici-baza-v117.csv",None),
    ("/admin/oglasivaci-baza-v117.csv",None),
    ("/api/v1/v11/admin-analytics-audit",None),
]:
    res=check(c,p,m) and res
print("RESULT:", "PASS" if res else "CHECK_FAILED")
raise SystemExit(0 if res else 1)
