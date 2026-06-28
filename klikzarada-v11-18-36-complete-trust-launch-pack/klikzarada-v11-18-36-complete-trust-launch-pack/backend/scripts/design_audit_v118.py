from fastapi.testclient import TestClient
import app.main

def check(client, path, expected=(200, 303, 401)):
    r = client.get(path)
    ok = r.status_code in expected
    print(f"{'OK' if ok else 'FAIL'} {path} -> {r.status_code}")
    return ok

def login(client, email, password):
    r = client.post("/login", data={"email": email, "password": password}, follow_redirects=False)
    print(f"LOGIN {email} -> {r.status_code} {r.headers.get('location')}")
    return r.status_code in (302, 303)

client = TestClient(app.main.app)

print("=== PUBLIC ===")
public_pages = ["/", "/zadaci", "/za-korisnike", "/za-oglasivace", "/cenovnik", "/reklame", "/kontakt", "/blog", "/api/v1/v11/health", "/api/v1/v11/design-map"]
public_ok = all(check(client, p, expected=(200,)) for p in public_pages)

print("\\n=== ADMIN ===")
admin_ok = login(client, "admin@klikzarada.rs", "Admin123!")
admin_pages = ["/admin/v11", "/admin/mapa-platforme", "/admin/reklame-v111", "/admin/cene-v111", "/admin/kampanje", "/admin/dokazi", "/admin/finansije", "/admin/workflows-v10"]
for p in admin_pages:
    admin_ok = check(client, p, expected=(200, 303)) and admin_ok

print("\\n=== ADVERTISER ===")
client = TestClient(app.main.app)
adv_ok = login(client, "oglasivac@demo.rs", "Demo123!")
adv_pages = ["/oglasivac/panel", "/oglasivac/reklame-v111", "/oglasivac/boost-v111", "/oglasivac/kampanje", "/oglasivac/budzet"]
for p in adv_pages:
    adv_ok = check(client, p, expected=(200, 303)) and adv_ok

print("\\n=== USER ===")
client = TestClient(app.main.app)
user_ok = login(client, "korisnik@demo.rs", "Demo123!")
user_pages = ["/korisnik/panel", "/korisnik/zadaci", "/korisnik/dokazi", "/korisnik/wallet", "/korisnik/isplate", "/korisnik/referral"]
for p in user_pages:
    user_ok = check(client, p, expected=(200, 303)) and user_ok

print("\\nRESULT:", "PASS" if (public_ok and admin_ok and adv_ok and user_ok) else "CHECK_FAILED")
