from fastapi.testclient import TestClient
import app.main

def login(c, email, password):
    r=c.post("/login", data={"email":email,"password":password}, follow_redirects=False)
    print("LOGIN", email, r.status_code, r.headers.get("location"))
    return r.status_code in (302,303)

def check(c,path,ok=(200,303), must=None):
    r=c.get(path)
    good=r.status_code in ok
    text=r.text if hasattr(r, "text") else ""
    if must:
        for m in must:
            good = good and (m in text)
    print(("OK" if good else "FAIL"), path, r.status_code)
    return good

res=True
c=TestClient(app.main.app)
print("PUBLIC")
for p in ["/","/zadaci","/zadaci-kategorija/ankete","/za-korisnike","/za-oglasivace","/cenovnik","/reklame","/kontakt","/blog"]:
    res=check(c,p,(200,)) and res

print("ADMIN")
login(c,"admin@klikzarada.rs","Admin123!")
checks=[
    ("/admin/v11", ["kz-admin-hero"]),
    ("/admin/mapa-platforme", ["kz1110-function-grid"]),
    ("/admin/kampanje", ["kz1110-campaign-grid"]),
    ("/admin/reklame-v111", ["kz1110-section"]),
    ("/admin/dokazi", ["admin-proofs-layout-marker"]),
    ("/admin/finansije", ["kz1111-finance-grid"]),
    ("/admin/isplate", ["kz1111-proof-grid"]),
    ("/admin/cene-v111", None),
    ("/admin/workflows-v10", None),
    ("/api/v1/v11/perfect-ui-audit", None),
]
for p,m in checks:
    res=check(c,p,(200,303),m) and res

print("ADVERTISER")
c=TestClient(app.main.app); login(c,"oglasivac@demo.rs","Demo123!")
for p,m in [("/oglasivac/panel",None),("/oglasivac/kampanje",None),("/oglasivac/reklame-v111",None),("/oglasivac/boost-v111",None),("/oglasivac/budzet",None),("/oglasivac/dokazi",["kz1111-proof-grid"])]:
    res=check(c,p,(200,303),m) and res

print("USER")
c=TestClient(app.main.app); login(c,"korisnik@demo.rs","Demo123!")
for p,m in [("/korisnik/panel",None),("/korisnik/zadaci",None),("/korisnik/dokazi",["kz1111-proof-grid"]),("/korisnik/wallet",None),("/korisnik/isplate",None),("/korisnik/referral",None)]:
    res=check(c,p,(200,303),m) and res

print("RESULT:", "PASS" if res else "CHECK_FAILED")
raise SystemExit(0 if res else 1)
