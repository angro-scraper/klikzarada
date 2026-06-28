from fastapi.testclient import TestClient
from bs4 import BeautifulSoup
import app.main

app.main.startup()

def new_client():
    return TestClient(app.main.app)

def login(email, password):
    c = new_client()
    r = c.post("/login", data={"email": email, "password": password}, follow_redirects=False)
    ok = r.status_code in (302, 303)
    print(("OK" if ok else "FAIL"), "LOGIN", email, r.status_code, r.headers.get("location"))
    return c, ok

def check_get(c, path, label="GET", allow_auth=False):
    r = c.get(path, follow_redirects=False)
    ok = r.status_code in (200, 301, 302, 303, 307, 308) or (allow_auth and r.status_code in (401, 403))
    print(("OK" if ok else "FAIL"), label, path, r.status_code, r.headers.get("location"))
    return ok, r

def check_css_static():
    c = new_client()
    ok = True
    for path in ["/static/css/style.css?v=11811", "/static/img/icon-wallet.svg", "/static/img/ad-megaphone.svg", "/static/img/trophy.svg"]:
        r = c.get(path, follow_redirects=False)
        local = r.status_code == 200
        print(("OK" if local else "FAIL"), "STATIC", path, r.status_code)
        ok = ok and local
    return ok

def extract_links_from_page(c, page):
    r = c.get(page)
    if r.status_code != 200:
        return set(), set(), r
    soup = BeautifulSoup(r.text, "html.parser")
    hrefs = set()
    actions = set()
    for a in soup.find_all("a", href=True):
        h = a.get("href")
        if h and not h.startswith("#") and not h.startswith("mailto:") and not h.startswith("tel:") and not h.startswith("javascript:") and not h.startswith("http"):
            hrefs.add(h)
    for f in soup.find_all("form", action=True):
        a = f.get("action") or ""
        if a and not a.startswith("http"):
            actions.add(((f.get("method") or "get").lower(), a))
    return hrefs, actions, r

def route_pattern_ok(path):
    return "{" not in path and "}" not in path

def check_home_links():
    c = new_client()
    ok = True
    hrefs, actions, r = extract_links_from_page(c, "/")
    local = r.status_code == 200
    print(("OK" if local else "FAIL"), "PAGE", "/", r.status_code)
    ok = ok and local

    for href in sorted(hrefs):
        if not route_pattern_ok(href):
            print("FAIL", "HOME_LINK_PATTERN", href)
            ok = False
            continue
        rr = new_client().get(href, follow_redirects=False)
        local = rr.status_code in (200, 301, 302, 303, 307, 308)
        print(("OK" if local else "FAIL"), "HOME_LINK", href, rr.status_code, rr.headers.get("location"))
        ok = ok and local

    for method, action in sorted(actions):
        if method == "get":
            rr = new_client().get(action, follow_redirects=False)
            local = rr.status_code in (200, 301, 302, 303, 307, 308)
            code = rr.status_code
        else:
            local = True
            code = "POST_ROUTE_NOT_SUBMITTED"
        print(("OK" if local else "FAIL"), "HOME_FORM", method.upper(), action, code)
        ok = ok and local
    return ok

def check_public_pages():
    public = [
        "/", "/pocetna", "/zadaci", "/za-korisnike", "/za-oglasivace", "/cenovnik", "/blog", "/kontakt",
        "/faq", "/pravila", "/registracija", "/login", "/podrska", "/politika-privatnosti", "/uslovi-isplate",
        "/o-nama", "/kako-funkcionise",
    ]
    ok = True
    for p in public:
        local, _ = check_get(new_client(), p, "PUBLIC")
        ok = ok and local
    return ok

def check_role_pages():
    ok = True

    admin, ok_admin = login("admin@klikzarada.rs", "Admin123!")
    ok = ok and ok_admin
    admin_pages = [
        "/admin/v11", "/admin/reklame-v111", "/admin/kampanje", "/admin/analitika-v117",
        "/admin/korisnici-baza-v117", "/admin/oglasivaci-baza-v117", "/admin/dokazi",
        "/admin/isplate", "/admin/finansije", "/admin/cene-v111", "/admin/fraud-v11",
        "/admin/auto-engine-v114", "/admin/smart-v115", "/admin/deploy-v11", "/admin/mapa-platforme",
        "/admin-centar"
    ]
    for p in admin_pages:
        local, _ = check_get(admin, p, "ADMIN")
        ok = ok and local

    user, ok_user = login("korisnik@demo.rs", "Demo123!")
    ok = ok and ok_user
    user_pages = [
        "/korisnik/panel", "/korisnik/zadaci", "/korisnik/wallet", "/korisnik/isplate",
        "/korisnik/bedzevi", "/korisnik/referral", "/korisnik/dokazi",
        "/korisnik/motivacija-v115", "/korisnik/payout-profile-v11",
        "/korisnik/notifikacije", "/korisnik/tiketi", "/poruke", "/korisnik/profil"
    ]
    for p in user_pages:
        local, _ = check_get(user, p, "USER")
        ok = ok and local

    adv, ok_adv = login("oglasivac@demo.rs", "Demo123!")
    ok = ok and ok_adv
    adv_pages = [
        "/oglasivac/panel", "/oglasivac/kampanje", "/oglasivac/nova-kampanja", "/oglasivac/budzet",
        "/oglasivac/reklame-v111", "/oglasivac/boost-v111", "/oglasivac/saveti-v115",
        "/oglasivac/izvestaji", "/oglasivac/fakture", "/oglasivac/dokazi", "/oglasivac/notifikacije",
        "/oglasivac/tiketi", "/oglasivac/profil", "/oglasivac/segmenti"
    ]
    for p in adv_pages:
        local, _ = check_get(adv, p, "ADVERTISER")
        ok = ok and local

    return ok

def client_for_label(label):
    if label == "ADMIN":
        return login("admin@klikzarada.rs", "Admin123!")[0]
    if label == "USER":
        return login("korisnik@demo.rs", "Demo123!")[0]
    if label == "ADVERTISER":
        return login("oglasivac@demo.rs", "Demo123!")[0]
    return new_client()

def check_visible_panel_links():
    ok = True
    configs = [
        ("ADMIN", ["/admin/v11", "/admin/reklame-v111", "/admin/analitika-v117"]),
        ("USER", ["/korisnik/panel", "/korisnik/wallet"]),
        ("ADVERTISER", ["/oglasivac/panel", "/oglasivac/reklame-v111"]),
    ]

    for label, pages in configs:
        for page in pages:
            page_client = client_for_label(label)
            hrefs, actions, r = extract_links_from_page(page_client, page)
            page_ok = r.status_code == 200
            print(("OK" if page_ok else "FAIL"), label, "VISIBLE_PAGE", page, r.status_code)
            ok = ok and page_ok

            for href in sorted(hrefs):
                if href == "/logout":
                    print("OK", label, "VISIBLE_LINK", page, "->", href, "SKIPPED_STATE_CHANGE")
                    continue
                if not route_pattern_ok(href):
                    print("FAIL", label, "VISIBLE_LINK_PATTERN", page, href)
                    ok = False
                    continue
                link_client = client_for_label(label)
                rr = link_client.get(href, follow_redirects=False)
                local = rr.status_code in (200, 301, 302, 303, 307, 308, 401, 403)
                print(("OK" if local else "FAIL"), label, "VISIBLE_LINK", page, "->", href, rr.status_code)
                ok = ok and local

            for method, action in sorted(actions):
                print("OK", label, "VISIBLE_FORM_EXISTS", page, method.upper(), action)
    return ok

ok = True
ok = check_css_static() and ok
ok = check_public_pages() and ok
ok = check_home_links() and ok
ok = check_role_pages() and ok
ok = check_visible_panel_links() and ok

print("RESULT:", "PASS" if ok else "CHECK_FAILED")
raise SystemExit(0 if ok else 1)
