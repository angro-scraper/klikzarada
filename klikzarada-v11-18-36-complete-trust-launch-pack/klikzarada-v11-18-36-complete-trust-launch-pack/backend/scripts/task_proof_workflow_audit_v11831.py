from fastapi.testclient import TestClient
import time
import app.main
from app.database import SessionLocal
from app.models import User, Task, TaskSubmission, WalletTransaction, AdvertiserBudgetTransaction

app.main.startup()

def login(email, password):
    c = TestClient(app.main.app)
    r = c.post("/login", data={"email": email, "password": password}, follow_redirects=False)
    ok = r.status_code in (302, 303)
    print(("OK" if ok else "FAIL"), "LOGIN", email, r.status_code, r.headers.get("location"))
    return c, ok

ok = True
admin, ok_admin = login("admin@klikzarada.rs", "Admin123!")
adv, ok_adv = login("oglasivac@demo.rs", "Demo123!")
user, ok_user = login("korisnik@demo.rs", "Demo123!")
ok = ok and ok_admin and ok_adv and ok_user

# Prepare advertiser budget
db = SessionLocal()
try:
    a = db.query(User).filter(User.email == "oglasivac@demo.rs").first()
    u = db.query(User).filter(User.email == "korisnik@demo.rs").first()
    a.advertiser_budget_rsd = 100000
    a.advertiser_reserved_rsd = 0
    a.advertiser_spent_rsd = 0
    u.balance_rsd = 0
    u.pending_rsd = 0
    u.lifetime_earned_rsd = 0
    db.commit()
finally:
    db.close()

title = f"Audit workflow task {int(time.time())}"

r = adv.post("/oglasivac/kampanje/v11831", data={
    "title": title,
    "task_type": "visit_site",
    "target_url": "/",
    "description": "Audit kampanja za workflow.",
    "instructions": "Otvori stranicu i pošalji dokaz.",
    "proof_required": "Napiši kratak dokaz.",
    "reward_rsd": "100",
    "total_slots": "3",
    "estimated_minutes": "1",
}, follow_redirects=False)
local = r.status_code in (302, 303)
print(("OK" if local else "FAIL"), "ADVERTISER_CREATE_TASK", r.status_code, r.headers.get("location"))
ok = ok and local

db = SessionLocal()
try:
    task = db.query(Task).filter(Task.title == title).order_by(Task.id.desc()).first()
    task_id = task.id if task else None
    local = task is not None and task.status == "pending" and task.advertiser is not None
    print(("OK" if local else "FAIL"), "TASK_PENDING_DB", task_id, getattr(task, "status", None))
finally:
    db.close()
ok = ok and local

r = admin.post(f"/admin/task-status-v11831/{task_id}", data={"status": "active", "note": "audit approve"}, follow_redirects=False)
local = r.status_code in (302, 303)
print(("OK" if local else "FAIL"), "ADMIN_APPROVE_TASK", r.status_code, r.headers.get("location"))
ok = ok and local

r = user.post(f"/korisnik/zadaci/{task_id}/dokaz-v11831", data={"proof": "Uradio sam zadatak i ovo je audit dokaz.", "proof_file": ""}, follow_redirects=False)
local = r.status_code in (302, 303)
print(("OK" if local else "FAIL"), "USER_SUBMIT_PROOF", r.status_code, r.headers.get("location"))
ok = ok and local

db = SessionLocal()
try:
    sub = db.query(TaskSubmission).filter(TaskSubmission.task_id == task_id).order_by(TaskSubmission.id.desc()).first()
    a = db.query(User).filter(User.email == "oglasivac@demo.rs").first()
    u = db.query(User).filter(User.email == "korisnik@demo.rs").first()
    sub_id = sub.id if sub else None
    local = sub is not None and sub.status == "pending" and sub.proof and round(sub.reward_rsd, 2) == 100.00 and round(sub.platform_fee_rsd, 2) == 20.00 and round(sub.advertiser_cost_rsd, 2) == 120.00 and round(u.pending_rsd, 2) == 100.00 and round(a.advertiser_reserved_rsd, 2) == 120.00
    print(("OK" if local else "FAIL"), "SUBMISSION_PENDING_AND_RESERVED", sub_id, getattr(sub, "status", None), getattr(sub, "proof", None), "pending", getattr(u, "pending_rsd", None), "reserved", getattr(a, "advertiser_reserved_rsd", None))
finally:
    db.close()
ok = ok and local

# Duplicate should not create another pending submission
r = user.post(f"/korisnik/zadaci/{task_id}/dokaz-v11831", data={"proof": "duplikat", "proof_file": ""}, follow_redirects=False)
local = r.status_code in (302, 303) and "already_submitted" in (r.headers.get("location") or "")
print(("OK" if local else "FAIL"), "DUPLICATE_BLOCKED", r.status_code, r.headers.get("location"))
ok = ok and local

r = admin.post(f"/admin/submissions/{sub_id}/approve", data={"note": "audit approved"}, follow_redirects=False)
local = r.status_code in (302, 303) and "approved" in (r.headers.get("location") or "")
print(("OK" if local else "FAIL"), "ADMIN_APPROVE_SUBMISSION", r.status_code, r.headers.get("location"))
ok = ok and local

db = SessionLocal()
try:
    sub = db.query(TaskSubmission).filter(TaskSubmission.id == sub_id).first()
    a = db.query(User).filter(User.email == "oglasivac@demo.rs").first()
    u = db.query(User).filter(User.email == "korisnik@demo.rs").first()
    wtx = db.query(WalletTransaction).filter(WalletTransaction.user_id == u.id, WalletTransaction.tx_type == "task_reward").count()
    btx = db.query(AdvertiserBudgetTransaction).filter(AdvertiserBudgetTransaction.advertiser_id == a.id).count()
    local = sub is not None and sub.status == "approved" and round(u.balance_rsd, 2) == 100.00 and round(u.pending_rsd, 2) == 0.00 and round(a.advertiser_reserved_rsd, 2) == 0.00 and round(a.advertiser_spent_rsd, 2) == 120.00 and wtx > 0 and btx > 0
    print(("OK" if local else "FAIL"), "MONEY_MOVED_ON_APPROVAL", sub.status, "balance", u.balance_rsd, "pending", u.pending_rsd, "reserved", a.advertiser_reserved_rsd, "spent", a.advertiser_spent_rsd, "wtx", wtx, "btx", btx)
finally:
    db.close()
ok = ok and local

r = TestClient(app.main.app).get("/api/v1/v11/task-proof-workflow-health")
local = r.status_code == 200 and r.json().get("version") == "11.18.31"
print(("OK" if local else "FAIL"), "HEALTH", r.status_code, r.json() if r.status_code == 200 else r.text[:120])
ok = ok and local

print("RESULT:", "PASS" if ok else "CHECK_FAILED")
raise SystemExit(0 if ok else 1)
