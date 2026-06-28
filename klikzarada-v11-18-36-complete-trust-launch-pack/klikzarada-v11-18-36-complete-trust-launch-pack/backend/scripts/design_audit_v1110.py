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
admin_checks=[
    ("/admin/v11", ["kz-admin-hero"]),
    ("/admin/mapa-platforme", ["kz1110-function-grid"]),
    ("/admin/kampanje", ["kz1110-campaign-grid"]),
    ("/admin/reklame-v111", ["kz1110-ad-grid"]),
    ("/admin/cene-v111", None),
    ("/admin/dokazi", None),
    ("/admin/finansije", None),
    ("/admin/workflows-v10", None),
]
for p,m in admin_checks:
    res=check(c,p,(200,303),m) and res

print("ADVERTISER")
c=TestClient(app.main.app); login(c,"oglasivac@demo.rs","Demo123!")
for p in ["/oglasivac/panel","/oglasivac/kampanje","/oglasivac/reklame-v111","/oglasivac/boost-v111","/oglasivac/budzet"]:
    res=check(c,p,(200,303)) and res

print("USER")
c=TestClient(app.main.app); login(c,"korisnik@demo.rs","Demo123!")
for p in ["/korisnik/panel","/korisnik/zadaci","/korisnik/dokazi","/korisnik/wallet","/korisnik/isplate","/korisnik/referral"]:
    res=check(c,p,(200,303)) and res

print("RESULT:", "PASS" if res else "CHECK_FAILED")
raise SystemExit(0 if res else 1)
