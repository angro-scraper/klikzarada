from fastapi.testclient import TestClient
import app.main

def login(c, email, password):
    r=c.post("/login", data={"email":email,"password":password}, follow_redirects=False)
    print("LOGIN", email, r.status_code, r.headers.get("location"))
    return r.status_code in (302,303)

def check(c,path,ok=(200,303)):
    r=c.get(path)
    good=r.status_code in ok
    print(("OK" if good else "FAIL"), path, r.status_code)
    return good

c=TestClient(app.main.app)
public=["/","/zadaci","/zadaci-kategorija/ankete","/za-korisnike","/za-oglasivace","/cenovnik","/reklame","/kontakt","/blog","/api/v1/v11/design-map"]
res=True
print("PUBLIC")
for p in public: res=check(c,p,(200,)) and res
print("ADMIN")
login(c,"admin@klikzarada.rs","Admin123!")
admin=["/admin/v11","/admin/mapa-platforme","/admin/funkcija/kampanje","/admin/kampanje","/admin/reklame-v111","/admin/cene-v111","/admin/dokazi","/admin/finansije","/admin/workflows-v10"]
for p in admin: res=check(c,p,(200,303)) and res
print("ADVERTISER")
c=TestClient(app.main.app); login(c,"oglasivac@demo.rs","Demo123!")
for p in ["/oglasivac/panel","/oglasivac/kampanje","/oglasivac/reklame-v111","/oglasivac/boost-v111","/oglasivac/budzet"]: res=check(c,p,(200,303)) and res
print("USER")
c=TestClient(app.main.app); login(c,"korisnik@demo.rs","Demo123!")
for p in ["/korisnik/panel","/korisnik/zadaci","/korisnik/dokazi","/korisnik/wallet","/korisnik/isplate","/korisnik/referral"]: res=check(c,p,(200,303)) and res
print("RESULT:", "PASS" if res else "CHECK_FAILED")
raise SystemExit(0 if res else 1)
