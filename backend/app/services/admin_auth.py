from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Any

from fastapi import HTTPException, Request, status

COOKIE_NAME = "fs_admin_session"


def admin_pin() -> str:
    return os.getenv("ADMIN_PIN", "246810").strip()


def session_hours() -> int:
    try:
        return int(os.getenv("ADMIN_SESSION_HOURS", "12"))
    except Exception:
        return 12


def cookie_secure() -> bool:
    return os.getenv("ADMIN_COOKIE_SECURE", "false").lower() in {"1", "true", "yes", "da"}


def _secret() -> str:
    # Local MVP default. In production this must be a long random secret in .env.
    return os.getenv("ADMIN_SESSION_SECRET", "food-saver-local-dev-secret-change-me")


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _b64decode(text: str) -> bytes:
    padding = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode((text + padding).encode())


def _sign(payload_b64: str) -> str:
    return hmac.new(_secret().encode(), payload_b64.encode(), hashlib.sha256).hexdigest()


def create_admin_token() -> tuple[str, int]:
    now = int(time.time())
    max_age = session_hours() * 60 * 60
    payload: dict[str, Any] = {
        "sub": "admin",
        "iat": now,
        "exp": now + max_age,
        "nonce": secrets.token_hex(10),
    }
    payload_b64 = _b64(json.dumps(payload, separators=(",", ":")).encode())
    return f"{payload_b64}.{_sign(payload_b64)}", max_age


def verify_admin_token(token: str | None) -> bool:
    if not token or "." not in token:
        return False
    payload_b64, sig = token.rsplit(".", 1)
    expected = _sign(payload_b64)
    if not hmac.compare_digest(sig, expected):
        return False
    try:
        payload = json.loads(_b64decode(payload_b64))
    except Exception:
        return False
    if payload.get("sub") != "admin":
        return False
    if int(payload.get("exp", 0)) < int(time.time()):
        return False
    return True


def is_request_admin(request: Request) -> bool:
    token = request.cookies.get(COOKIE_NAME)
    if verify_admin_token(token):
        return True
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return verify_admin_token(auth.split(" ", 1)[1].strip())
    return False


def require_admin_session(request: Request) -> bool:
    if not is_request_admin(request):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin prijava je potrebna")
    return True
