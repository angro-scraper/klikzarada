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
admin_pages=[
    ("/admin-centar",["kz112-admin-button-grid"]),
    ("/admin/v11",["kz112-admin-main"]),
    ("/admin/mapa-platforme",["kz112-admin-main"]),
    ("/admin/kampanje",["kz1110-campaign-grid"]),
    ("/admin/dokazi",["admin-proofs-layout-marker"]),
    ("/admin/isplate",["kz1111-proof-grid"]),
    ("/admin/finansije",["kz1111-finance-grid"]),
    ("/admin/cene-v111",["kz112-admin-main"]),
    ("/admin/reklame-v111",["kz1110-ad-grid"]),
    ("/admin/workflows-v10",["kz112-admin-main"]),
    ("/api/v1/v11/admin-clean-audit",None),
]
for p,m in admin_pages:
    res=check(c,p,m) and res

print("RESULT:", "PASS" if res else "CHECK_FAILED")
raise SystemExit(0 if res else 1)
