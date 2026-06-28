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
admin=[
    ("/admin-centar",["kz112-admin-button-grid"]),
    ("/admin/cene-v111",["kz113-split-panel"]),
    ("/admin/budget-v11",["kz113-budget-grid"]),
    ("/admin/fraud-v11",["kz113-rule-grid"]),
    ("/admin/workflows-v10",["kz113-rule-grid"]),
    ("/admin/deploy-v11",["kz113-check-grid"]),
    ("/admin/kampanje",["kz1110-campaign-grid"]),
    ("/admin/reklame-v111",["kz1110-section"]),
    ("/admin/dokazi",["admin-proofs-layout-marker"]),
    ("/api/v1/v11/admin-automation-audit",None),
]
for p,m in admin:
    res=check(c,p,m) and res
c=TestClient(app.main.app)
for p,m in [("/zadaci/1",["kz113-countdown"]),("/zadaci",None)]:
    res=check(c,p,m) and res
print("RESULT:", "PASS" if res else "CHECK_FAILED")
raise SystemExit(0 if res else 1)
