from fastapi.testclient import TestClient
import app.main
from app.database import SessionLocal
from app.models import User, TaskSubmission, Task, Dispute, EmailOutboxV8, PayoutHoldV11, UserScoreV115, Withdrawal

app.main.startup()

def login(email, password):
    c = TestClient(app.main.app)
    r = c.post("/login", data={"email": email, "password": password}, follow_redirects=False)
    ok = r.status_code in (302, 303)
    print(("OK" if ok else "FAIL"), "LOGIN", email, r.status_code, r.headers.get("location"))
    return c, ok

ok = True
admin, ok_admin = login("admin@klikzarada.rs", "Admin123!")
user_client, ok_user = login("korisnik@demo.rs", "Demo123!")
adv_client, ok_adv = login("oglasivac@demo.rs", "Demo123!")
ok = ok and ok_admin and ok_user and ok_adv

# Prepare data
db = SessionLocal()
try:
    user = db.query(User).filter(User.email == "korisnik@demo.rs").first()
    adv = db.query(User).filter(User.email == "oglasivac@demo.rs").first()
    user.balance_rsd = 2000
    user.pending_rsd = 0
    user.email_verified = True
    user.phone_verified = False
    user.phone = ""
    user.payment_details = ""
    user.payment_method = ""
    adv.advertiser_budget_rsd = 10000
    adv.advertiser_reserved_rsd = 0
    adv.advertiser_spent_rsd = 0
    db.commit()
    user_id = user.id
    adv_id = adv.id
finally:
    db.close()

# KYC blocks payout
r = user_client.post("/korisnik/isplate/zahtev-v11836", data={
    "amount_rsd": "600",
    "payment_method": "bank_transfer",
    "payment_details": "",
}, follow_redirects=False)
local = r.status_code in (302,303) and "kyc_required" in (r.headers.get("location") or "")
print(("OK" if local else "FAIL"), "KYC_BLOCKS_PAYOUT", r.status_code, r.headers.get("location"))
ok = ok and local

db = SessionLocal()
try:
    hold = db.query(PayoutHoldV11).filter(PayoutHoldV11.user_id == user_id).order_by(PayoutHoldV11.id.desc()).first()
    local = hold is not None and hold.status == "active"
    print(("OK" if local else "FAIL"), "PAYOUT_HOLD_CREATED", getattr(hold, "reason", None))
finally:
    db.close()
ok = ok and local

# User fills KYC
r = user_client.post("/korisnik/kyc-v11836", data={
    "phone": "+38160111222",
    "payment_method": "bank_transfer",
    "payment_details": "IBAN RS35160005010000123456",
}, follow_redirects=False)
local = r.status_code in (302,303)
print(("OK" if local else "FAIL"), "USER_KYC_SAVE", r.status_code)
ok = ok and local

# Admin verifies
r = admin.post(f"/admin/trust-v11836/users/{user_id}/verify", data={"note": "audit verified"}, follow_redirects=False)
local = r.status_code in (302,303) and "verified" in (r.headers.get("location") or "")
print(("OK" if local else "FAIL"), "ADMIN_VERIFY_KYC", r.status_code, r.headers.get("location"))
ok = ok and local

# Payout now allowed
r = user_client.post("/korisnik/isplate/zahtev-v11836", data={
    "amount_rsd": "600",
    "payment_method": "bank_transfer",
    "payment_details": "IBAN RS35160005010000123456",
}, follow_redirects=False)
local = r.status_code in (302,303) and "created" in (r.headers.get("location") or "")
print(("OK" if local else "FAIL"), "VERIFIED_PAYOUT_ALLOWED", r.status_code, r.headers.get("location"))
ok = ok and local

# Risk score row
db = SessionLocal()
try:
    score = db.query(UserScoreV115).filter(UserScoreV115.user_id == user_id).first()
    local = score is not None and score.risk_score >= 0 and score.quality_score >= 0
    print(("OK" if local else "FAIL"), "RISK_SCORE_ROW", getattr(score, "risk_score", None), getattr(score, "quality_score", None), getattr(score, "level_name", None))
finally:
    db.close()
ok = ok and local

# Dispute flow
db = SessionLocal()
try:
    user = db.query(User).filter(User.id == user_id).first()
    adv = db.query(User).filter(User.id == adv_id).first()
    task = Task(advertiser_id=adv.id, title="Audit dispute task v11836", task_type="visit_site", target_url="/", description="audit", instructions="audit", proof_required="audit", reward_rsd=50, platform_fee_percent=20, total_slots=1, status="active")
    db.add(task); db.flush()
    sub = TaskSubmission(user_id=user.id, task_id=task.id, proof="audit proof", status="rejected", reward_rsd=50, platform_fee_rsd=10, advertiser_cost_rsd=60, review_note="audit reject")
    db.add(sub); db.commit()
    sub_id = sub.id
finally:
    db.close()

r = user_client.post(f"/korisnik/dokazi/{sub_id}/zalba-v11836", data={"reason": "Mislim da je dokaz ispravan."}, follow_redirects=False)
local = r.status_code in (302,303) and "dispute_opened" in (r.headers.get("location") or "")
print(("OK" if local else "FAIL"), "OPEN_DISPUTE", r.status_code, r.headers.get("location"))
ok = ok and local

db = SessionLocal()
try:
    d = db.query(Dispute).filter(Dispute.submission_id == sub_id).order_by(Dispute.id.desc()).first()
    dispute_id = d.id if d else None
    local = d is not None and d.status == "open"
    print(("OK" if local else "FAIL"), "DISPUTE_DB_OPEN", dispute_id)
finally:
    db.close()
ok = ok and local

r = admin.post(f"/admin/disputes-v11836/{dispute_id}/accept", data={"decision": "audit accept"}, follow_redirects=False)
local = r.status_code in (302,303) and "accept" in (r.headers.get("location") or "")
print(("OK" if local else "FAIL"), "ADMIN_ACCEPT_DISPUTE", r.status_code, r.headers.get("location"))
ok = ok and local

db = SessionLocal()
try:
    sub = db.query(TaskSubmission).filter(TaskSubmission.id == sub_id).first()
    local = sub is not None and sub.status == "pending"
    print(("OK" if local else "FAIL"), "DISPUTE_RETURNS_TO_PENDING", getattr(sub, "status", None))
finally:
    db.close()
ok = ok and local

# Pages
for path, needle in [
    ("/admin/trust-v11836", "Trust / KYC / Fraud"),
    ("/admin/disputes-v11836", "Dispute / žalbe"),
    ("/admin/daily-v11836", "Daily report"),
    ("/admin/launch-v11836", "Launch checklist"),
    ("/oglasivac/performance-v11836", "Performance dashboard"),
]:
    client = admin if path.startswith("/admin") else adv_client
    r = client.get(path)
    local = r.status_code == 200 and needle in r.text
    print(("OK" if local else "FAIL"), "PAGE", path, r.status_code)
    ok = ok and local

# Daily email queue
r = admin.post("/admin/daily-v11836/email", follow_redirects=False)
local = r.status_code in (302,303) and "email_queued" in (r.headers.get("location") or "")
print(("OK" if local else "FAIL"), "DAILY_EMAIL_QUEUE", r.status_code, r.headers.get("location"))
ok = ok and local

db = SessionLocal()
try:
    e = db.query(EmailOutboxV8).order_by(EmailOutboxV8.id.desc()).first()
    local = e is not None and e.status == "queued"
    print(("OK" if local else "FAIL"), "EMAIL_OUTBOX_DB", getattr(e, "subject", None))
finally:
    db.close()
ok = ok and local

# Health
r = TestClient(app.main.app).get("/api/v1/v11/trust-launch-health")
local = r.status_code == 200 and r.json().get("version") == "11.18.36"
print(("OK" if local else "FAIL"), "TRUST_HEALTH", r.status_code, r.json() if r.status_code == 200 else r.text[:100])
ok = ok and local

# Handoff files exist
from pathlib import Path
root = Path(__file__).resolve().parents[2]
local = (root / "AGENTS.md").exists() and (root / "CODEX_HANDOFF.md").exists()
print(("OK" if local else "FAIL"), "CODEX_HANDOFF_FILES")
ok = ok and local

print("RESULT:", "PASS" if ok else "CHECK_FAILED")
raise SystemExit(0 if ok else 1)
