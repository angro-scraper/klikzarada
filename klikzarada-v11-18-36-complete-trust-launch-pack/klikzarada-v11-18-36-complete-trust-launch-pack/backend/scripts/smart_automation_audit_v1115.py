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
    return ok

res=True
c=TestClient(app.main.app)
login(c,"admin@klikzarada.rs","Admin123!")
for p,m in [
    ("/admin/smart-v115",["kz115-score-grid"]),
    ("/admin/auto-engine-v114",["kz114-log-list"]),
    ("/api/v1/v11/smart-automation-audit",None),
]:
    res=check(c,p,m) and res

c=TestClient(app.main.app)
login(c,"korisnik@demo.rs","Demo123!")
for p,m in [
    ("/korisnik/motivacija-v115",["kz115-user-status"]),
    ("/zadaci/1",["rezervisi-v115"]),
]:
    res=check(c,p,m) and res

c=TestClient(app.main.app)
login(c,"oglasivac@demo.rs","Demo123!")
for p,m in [
    ("/oglasivac/saveti-v115",["kz115-suggestion-grid"]),
    ("/oglasivac/boost-v111",["kz114-campaign-boost-grid"]),
]:
    res=check(c,p,m) and res

print("RESULT:", "PASS" if res else "CHECK_FAILED")
raise SystemExit(0 if res else 1)
