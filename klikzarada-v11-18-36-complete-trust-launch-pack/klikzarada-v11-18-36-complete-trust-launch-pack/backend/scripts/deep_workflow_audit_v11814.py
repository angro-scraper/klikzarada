from fastapi.testclient import TestClient
from bs4 import BeautifulSoup
import re, time
import app.main
from app.database import SessionLocal
from app.models import User, Task, TaskSubmission, Withdrawal, AdvertiserBudgetTransaction

app.main.startup()

def client():
    return TestClient(app.main.app)

def login(email, password):
    c = client()
    r = c.post("/login", data={"email": email, "password": password}, follow_redirects=False)
    ok = r.status_code in (302, 303)
    print(("OK" if ok else "FAIL"), "LOGIN", email, r.status_code, r.headers.get("location"))
    return c, ok

def get(c, path, label):
    r = c.get(path, follow_redirects=False)
    ok = r.status_code in (200, 301, 302, 303, 307, 308)
    print(("OK" if ok else "FAIL"), label, path, r.status_code, r.headers.get("location"))
    if not ok:
        print(r.text[:400].replace("\n"," "))
    return ok, r

def post(c, path, data, label, accepted=(200, 302, 303, 307, 308, 400, 422)):
    r = c.post(path, data=data, follow_redirects=False)
    ok = r.status_code in accepted
    print(("OK" if ok else "FAIL"), label, path, r.status_code, r.headers.get("location"))
    if not ok:
        print(r.text[:600].replace("\n"," "))
    return ok, r

def db_counts():
    db = SessionLocal()
    try:
        return {
            "users": db.query(User).count(),
            "tasks": db.query(Task).count(),
            "subs": db.query(TaskSubmission).count(),
            "withdrawals": db.query(Withdrawal).count(),
            "budget_txs": db.query(AdvertiserBudgetTransaction).count(),
            "task_ids": [x.id for x in db.query(Task).order_by(Task.id.asc()).limit(10).all()],
        }
    finally:
        db.close()

def find_forms(html):
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for f in soup.find_all("form"):
        out.append({
            "method": (f.get("method") or "get").lower(),
            "action": f.get("action") or "",
            "inputs": sorted(set(i.get("name") for i in f.find_all(["input","textarea","select"]) if i.get("name"))),
        })
    return out

ok=True
before = db_counts()
print("INFO", "COUNTS_BEFORE", before)

admin, aok = login("admin@klikzarada.rs", "Admin123!")
user, uok = login("korisnik@demo.rs", "Demo123!")
adv, vok = login("oglasivac@demo.rs", "Demo123!")
ok = ok and aok and uok and vok

# Health endpoint
local, r = get(client(), "/api/v1/v11/workflow-health", "HEALTH")
ok = ok and local

# 1) User flow: list tasks -> detail -> submission page form exists -> safe submit if route accepts.
local, r = get(user, "/zadaci", "USER_TASK_LIST")
ok = ok and local
soup = BeautifulSoup(r.text, "html.parser")
task_links = [a.get("href") for a in soup.find_all("a", href=True) if re.match(r"^/zadaci/\d+$", a.get("href",""))]
print("INFO", "TASK_LINKS", task_links[:5])
if not task_links:
    print("FAIL", "NO_TASK_LINKS")
    ok = False
else:
    local, detail = get(user, task_links[0], "USER_TASK_DETAIL")
    ok = ok and local
    forms = find_forms(detail.text)
    print("INFO", "TASK_DETAIL_FORMS", forms)
    # Try the first POST form on task detail with generic proof fields, if exists
    post_forms = [f for f in forms if f["method"] == "post" and f["action"]]
    if post_forms:
        action = post_forms[0]["action"]
        data = {
            "proof_text": "Audit dokaz: pregledao/la sam zadatak i šaljem test dokaz.",
            "proof_url": "https://primer.rs/audit",
            "proof_code": "AUDIT123",
            "note": "Audit test",
            "comment": "Audit test komentar",
        }
        local, _ = post(user, action, data, "USER_TASK_SUBMIT", accepted=(200,302,303,400,422))
        ok = ok and local
    else:
        print("OK", "TASK_DETAIL_NO_POST_FORM_BUT_PAGE_OK")

# 2) User withdrawal flow
local, _ = get(user, "/korisnik/isplate", "USER_WITHDRAWAL_PAGE")
ok = ok and local
local, _ = post(user, "/korisnik/isplate/zahtev", {"amount_rsd":"500","method":"bank","note":"audit workflow"}, "USER_WITHDRAWAL_REQUEST", accepted=(200,302,303,400,422))
ok = ok and local

# 3) User payout profile save if form exists
local, r = get(user, "/korisnik/payout-profile-v11", "USER_PAYOUT_PROFILE")
ok = ok and local
forms = find_forms(r.text)
print("INFO", "PAYOUT_PROFILE_FORMS", forms)
for f in forms[:2]:
    if f["method"] == "post" and f["action"]:
        data = {name: "audit" for name in f["inputs"]}
        data.update({"method":"bank","bank_name":"Audit Banka","account_number":"123-456789-00","full_name":"Demo Korisnik"})
        local, _ = post(user, f["action"], data, "USER_PAYOUT_PROFILE_POST", accepted=(200,302,303,400,422))
        ok = ok and local
        break

# 4) Advertiser budget and ad forms
local, _ = get(adv, "/oglasivac/budzet", "ADV_BUDGET_PAGE")
ok = ok and local
local, _ = post(adv, "/oglasivac/budzet/zahtev", {"amount_rsd":"1500","note":"deep workflow audit"}, "ADV_BUDGET_TOPUP", accepted=(200,302,303,400,422))
ok = ok and local

for page in ["/oglasivac/reklame-v111", "/oglasivac/boost-v111", "/oglasivac/nova-kampanja"]:
    local, r = get(adv, page, "ADV_WORKFLOW_PAGE")
    ok = ok and local
    forms = find_forms(r.text)
    print("INFO", "FORMS", page, forms)
    for f in forms:
        local = bool(f["action"])
        print(("OK" if local else "FAIL"), "FORM_ACTION_PRESENT", page, f["method"].upper(), f["action"])
        ok = ok and local

# 5) Admin workflow pages and action forms existence
for page in ["/admin/kampanje", "/admin/dokazi", "/admin/isplate", "/admin/reklame-v111", "/admin/finansije"]:
    local, r = get(admin, page, "ADMIN_WORKFLOW_PAGE")
    ok = ok and local
    forms = find_forms(r.text)
    print("INFO", "ADMIN_FORMS_COUNT", page, len(forms))
    for f in forms:
        local = bool(f["action"])
        print(("OK" if local else "FAIL"), "ADMIN_FORM_ACTION_PRESENT", page, f["method"].upper(), f["action"])
        ok = ok and local

# 6) API stats are alive
for path in ["/api/v1/stats", "/api/v1/tasks", "/api/v1/v11/health", "/api/v1/v11/smoke", "/api/v1/v11/workflow-health"]:
    local, _ = get(client(), path, "API")
    ok = ok and local

after = db_counts()
print("INFO", "COUNTS_AFTER", after)

# Ensure DB still sane
local = after["users"] >= before["users"] and after["tasks"] >= before["tasks"]
print(("OK" if local else "FAIL"), "DB_SANITY")
ok = ok and local

print("RESULT:", "PASS" if ok else "CHECK_FAILED")
raise SystemExit(0 if ok else 1)
