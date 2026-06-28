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
            ok = ok and (m in text)
    print(("OK" if ok else "FAIL"), path, r.status_code)
    return ok

res=True
c=TestClient(app.main.app)
login(c,"admin@klikzarada.rs","Admin123!")
for p,m in [
    ("/admin/auto-engine-v114",["kz114-log-list"]),
    ("/admin/workflows-v10",["kz114-rule-grid"]),
    ("/admin/fraud-v11",["kz114-chip-grid"]),
    ("/admin/cene-v111",["kz113-split-panel"]),
    ("/api/v1/v11/auto-engine-audit",None),
]:
    res=check(c,p,m) and res

c=TestClient(app.main.app)
login(c,"oglasivac@demo.rs","Demo123!")
res=check(c,"/oglasivac/boost-v111",["kz114-campaign-boost-grid"]) and res

c=TestClient(app.main.app)
for p,m in [("/zadaci/1",["kz113-countdown"]),("/api/v1/v11/auto-engine-audit",None)]:
    res=check(c,p,m) and res

print("RESULT:", "PASS" if res else "CHECK_FAILED")
raise SystemExit(0 if res else 1)
