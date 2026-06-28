from fastapi.testclient import TestClient
import app.main
from app.database import SessionLocal
from app.models import User, Withdrawal, WalletTransaction

app.main.startup()

def login(email, password):
    c = TestClient(app.main.app)
    r = c.post("/login", data={"email": email, "password": password}, follow_redirects=False)
    ok = r.status_code in (302, 303)
    print(("OK" if ok else "FAIL"), "LOGIN", email, r.status_code, r.headers.get("location"))
    return c, ok

ok = True
admin, ok_admin = login("admin@klikzarada.rs", "Admin123!")
user, ok_user = login("korisnik@demo.rs", "Demo123!")
ok = ok and ok_admin and ok_user

# Prepare user balance
db = SessionLocal()
try:
    u = db.query(User).filter(User.email == "korisnik@demo.rs").first()
    u.balance_rsd = 2000
    u.payment_details = "IBAN RS35160005010000123456"
    db.commit()
    user_id = u.id
finally:
    db.close()

# Create withdrawal
r = user.post("/korisnik/isplate/zahtev-v11832", data={
    "amount_rsd": "700",
    "payment_method": "bank_transfer",
    "payment_details": "IBAN RS35160005010000123456",
    "note": "audit"
}, follow_redirects=False)
local = r.status_code in (302, 303) and "created" in (r.headers.get("location") or "")
print(("OK" if local else "FAIL"), "CREATE_WITHDRAWAL", r.status_code, r.headers.get("location"))
ok = ok and local

db = SessionLocal()
try:
    u = db.query(User).filter(User.id == user_id).first()
    w = db.query(Withdrawal).filter(Withdrawal.user_id == user_id).order_by(Withdrawal.id.desc()).first()
    wid = w.id if w else None
    local = w is not None and w.status == "pending" and round(w.amount_rsd, 2) == 700.00 and round(u.balance_rsd, 2) == 1300.00 and w.payment_method == "bank_transfer" and "IBAN" in w.payment_details
    print(("OK" if local else "FAIL"), "WITHDRAWAL_PENDING_DB", wid, getattr(w, "status", None), getattr(w, "amount_rsd", None), "balance", getattr(u, "balance_rsd", None))
finally:
    db.close()
ok = ok and local

# Admin marks as paid
r = admin.post(f"/admin/withdrawals-v11832/{wid}/paid", data={"note": "audit paid"}, follow_redirects=False)
local = r.status_code in (302, 303) and "paid" in (r.headers.get("location") or "")
print(("OK" if local else "FAIL"), "ADMIN_PAID", r.status_code, r.headers.get("location"))
ok = ok and local

db = SessionLocal()
try:
    u = db.query(User).filter(User.id == user_id).first()
    w = db.query(Withdrawal).filter(Withdrawal.id == wid).first()
    local = w.status == "paid" and w.processed_at is not None and round(u.balance_rsd, 2) == 1300.00
    print(("OK" if local else "FAIL"), "PAID_NO_BALANCE_RETURN", w.status, "balance", u.balance_rsd)
finally:
    db.close()
ok = ok and local

# Create second withdrawal and reject it
db = SessionLocal()
try:
    u = db.query(User).filter(User.id == user_id).first()
    u.balance_rsd = 1500
    db.commit()
finally:
    db.close()

r = user.post("/korisnik/isplate/zahtev-v11832", data={
    "amount_rsd": "600",
    "payment_method": "paypal",
    "payment_details": "user@example.com",
    "note": "audit reject"
}, follow_redirects=False)
local = r.status_code in (302, 303)
print(("OK" if local else "FAIL"), "CREATE_WITHDRAWAL_REJECT_CASE", r.status_code)
ok = ok and local

db = SessionLocal()
try:
    u = db.query(User).filter(User.id == user_id).first()
    w2 = db.query(Withdrawal).filter(Withdrawal.user_id == user_id).order_by(Withdrawal.id.desc()).first()
    w2id = w2.id
    local = round(u.balance_rsd, 2) == 900.00 and w2.status == "pending"
    print(("OK" if local else "FAIL"), "SECOND_PENDING_RESERVED", w2id, "balance", u.balance_rsd, w2.status)
finally:
    db.close()
ok = ok and local

r = admin.post(f"/admin/withdrawals-v11832/{w2id}/reject", data={"note": "audit rejected"}, follow_redirects=False)
local = r.status_code in (302, 303) and "rejected" in (r.headers.get("location") or "")
print(("OK" if local else "FAIL"), "ADMIN_REJECT", r.status_code, r.headers.get("location"))
ok = ok and local

db = SessionLocal()
try:
    u = db.query(User).filter(User.id == user_id).first()
    w2 = db.query(Withdrawal).filter(Withdrawal.id == w2id).first()
    tx_count = db.query(WalletTransaction).filter(WalletTransaction.user_id == user_id, WalletTransaction.tx_type == "withdrawal_return").count()
    local = w2.status == "rejected" and round(u.balance_rsd, 2) == 1500.00 and tx_count > 0
    print(("OK" if local else "FAIL"), "REJECT_RETURNS_BALANCE", w2.status, "balance", u.balance_rsd, "return_txs", tx_count)
finally:
    db.close()
ok = ok and local

# Insufficient balance blocked
r = user.post("/korisnik/isplate/zahtev-v11832", data={
    "amount_rsd": "999999",
    "payment_method": "bank_transfer",
    "payment_details": "IBAN TEST",
}, follow_redirects=False)
local = r.status_code in (302,303) and "insufficient_balance" in (r.headers.get("location") or "")
print(("OK" if local else "FAIL"), "INSUFFICIENT_BLOCKED", r.status_code, r.headers.get("location"))
ok = ok and local

r = TestClient(app.main.app).get("/api/v1/v11/payout-workflow-health")
local = r.status_code == 200 and r.json().get("version") == "11.18.32"
print(("OK" if local else "FAIL"), "HEALTH", r.status_code, r.json() if r.status_code == 200 else r.text[:100])
ok = ok and local

print("RESULT:", "PASS" if ok else "CHECK_FAILED")
raise SystemExit(0 if ok else 1)
