"""Shared account authentication for the JSON and legacy login forms."""

import hashlib
import hmac
import ipaddress
import os
from datetime import datetime, timedelta

from fastapi import HTTPException, Request
from sqlalchemy.orm import Session

from .models import LoginAttemptV11, User
from .security import SECRET_KEY, running_in_production, verify_password


FAILURE_WINDOW = timedelta(minutes=15)
MAX_FAILURES = 8
MAX_IP_FAILURES = 30
INVALID_LOGIN = "Pogrešan email, lozinka ili blokiran nalog."


def _digest(value: str) -> str:
    return hmac.new(SECRET_KEY.encode(), value.encode(), hashlib.sha256).hexdigest()


def _client_hash(request: Request | None) -> str | None:
    if request is None:
        return None
    # Render supplies the real client as the first X-Forwarded-For address.
    forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    remote = forwarded or (request.client.host if request.client else "")
    try:
        return _digest(f"ip:{ipaddress.ip_address(remote)}")
    except ValueError:
        return None


def throttle_public_action(db: Session, request: Request, action: str, email: str, limit: int, minutes: int, ip_limit: int = 30) -> None:
    """Bound email delivery and account creation across application workers."""
    since = datetime.utcnow() - timedelta(minutes=minutes)
    identities = [(f"{action}:email", _digest(f"email:{email.strip().lower()}"), "email", limit)]
    ip_hash = _client_hash(request)
    if ip_hash:
        identities.append((f"{action}:ip", ip_hash, "ip_address", ip_limit))
    for note, identity, column, allowed in identities:
        if db.query(LoginAttemptV11.id).filter(
            getattr(LoginAttemptV11, column) == identity,
            LoginAttemptV11.note == note,
            LoginAttemptV11.created_at >= since,
        ).count() >= allowed:
            raise HTTPException(429, "Previše zahteva. Pokušaj ponovo kasnije.", headers={"Retry-After": str(minutes * 60)})
    for note, identity, column, _ in identities:
        db.add(LoginAttemptV11(**{column: identity, "note": note, "success": False}))
    db.commit()


def admin_identity_allowed(user: User) -> bool:
    if user.role != "admin":
        return True
    owner_id = os.getenv("ADMIN_OWNER_USER_ID", "").strip()
    if owner_id:
        return str(user.id) == owner_id
    owner_email = (os.getenv("ADMIN_OWNER_EMAIL") or os.getenv("ADMIN_BOOTSTRAP_EMAIL") or "").strip().lower()
    return (not running_in_production() or bool(owner_email)) and (not owner_email or user.email.strip().lower() == owner_email)


def authenticate_login(db: Session, email: str, password: str, request: Request | None = None) -> User:
    normalized_email = email.strip().lower()
    # A keyed digest permits account-level throttling without storing attempted addresses.
    identity = _digest(normalized_email)
    recent_failures = db.query(LoginAttemptV11.id).filter(
        LoginAttemptV11.email == identity,
        LoginAttemptV11.success.is_(False),
        LoginAttemptV11.note == "auth_failure",
        LoginAttemptV11.created_at >= datetime.utcnow() - FAILURE_WINDOW,
    ).count()
    if recent_failures >= MAX_FAILURES:
        raise HTTPException(429, "Previše neuspelih pokušaja. Pokušaj ponovo za 15 minuta.", headers={"Retry-After": "900"})

    ip_hash = _client_hash(request)
    if ip_hash and db.query(LoginAttemptV11.id).filter(
        LoginAttemptV11.ip_address == ip_hash,
        LoginAttemptV11.success.is_(False),
        LoginAttemptV11.note == "auth_failure",
        LoginAttemptV11.created_at >= datetime.utcnow() - FAILURE_WINDOW,
    ).count() >= MAX_IP_FAILURES:
        raise HTTPException(429, "Previše neuspelih pokušaja. Pokušaj ponovo za 15 minuta.", headers={"Retry-After": "900"})

    user = db.query(User).filter(User.email == normalized_email).first()
    if not user or user.status != "active" or not verify_password(password, user.password_hash) or not admin_identity_allowed(user):
        db.add(LoginAttemptV11(email=identity, ip_address=ip_hash, success=False, note="auth_failure"))
        db.commit()
        raise HTTPException(401, INVALID_LOGIN)
    return user
