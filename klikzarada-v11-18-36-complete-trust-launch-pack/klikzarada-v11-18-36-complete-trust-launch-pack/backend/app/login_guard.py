"""Shared account authentication for the JSON and legacy login forms."""

import hashlib
import hmac
import os
from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy.orm import Session

from .models import LoginAttemptV11, User
from .security import SECRET_KEY, verify_password


FAILURE_WINDOW = timedelta(minutes=15)
MAX_FAILURES = 8
INVALID_LOGIN = "Pogrešan email, lozinka ili blokiran nalog."


def admin_identity_allowed(user: User) -> bool:
    if user.role != "admin":
        return True
    owner_id = os.getenv("ADMIN_OWNER_USER_ID", "").strip()
    if owner_id:
        return str(user.id) == owner_id
    owner_email = (os.getenv("ADMIN_OWNER_EMAIL") or os.getenv("ADMIN_BOOTSTRAP_EMAIL") or "").strip().lower()
    return not owner_email or user.email.strip().lower() == owner_email


def authenticate_login(db: Session, email: str, password: str) -> User:
    normalized_email = email.strip().lower()
    # A keyed digest permits account-level throttling without storing attempted addresses.
    identity = hmac.new(SECRET_KEY.encode(), normalized_email.encode(), hashlib.sha256).hexdigest()
    recent_failures = db.query(LoginAttemptV11.id).filter(
        LoginAttemptV11.email == identity,
        LoginAttemptV11.success.is_(False),
        LoginAttemptV11.note == "auth_failure",
        LoginAttemptV11.created_at >= datetime.utcnow() - FAILURE_WINDOW,
    ).count()
    if recent_failures >= MAX_FAILURES:
        raise HTTPException(429, "Previše neuspelih pokušaja. Pokušaj ponovo za 15 minuta.", headers={"Retry-After": "900"})

    user = db.query(User).filter(User.email == normalized_email).first()
    if not user or user.status != "active" or not verify_password(password, user.password_hash) or not admin_identity_allowed(user):
        db.add(LoginAttemptV11(email=identity, success=False, note="auth_failure"))
        db.commit()
        raise HTTPException(401, INVALID_LOGIN)
    return user
