import base64, binascii, hashlib, hmac, os, secrets, time
from datetime import datetime, timezone
from typing import Optional

APP_ENV = os.getenv("APP_ENV", "development").strip().lower()


def running_in_production() -> bool:
    return os.getenv("APP_ENV", "development").strip().lower() in {"production", "prod"} or os.getenv("RENDER", "").strip().lower() == "true"


_configured_secret = os.getenv("KLIKZARADA_SECRET_KEY", "").strip()
if running_in_production() and (len(_configured_secret) < 32 or _configured_secret in {"CHANGE_ME_STRONG_RANDOM_SECRET", "CHANGE_ME_BEFORE_LIVE_KLIKZARADA_V3"}):
    raise RuntimeError("KLIKZARADA_SECRET_KEY mora biti nasumična tajna od najmanje 32 znaka u produkciji.")

# A local-only fallback keeps onboarding simple, but production never starts
# with a predictable signing key.
SECRET_KEY = _configured_secret or "CHANGE_ME_BEFORE_LIVE_KLIKZARADA_V3"
SESSION_TTL_SECONDS = 14 * 24 * 60 * 60
ADMIN_SESSION_TTL_SECONDS = 12 * 60 * 60
# Existing signed cookies are accepted briefly while browsers migrate to v2.
LEGACY_SESSION_END = datetime(2026, 10, 5, tzinfo=timezone.utc).timestamp()
def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 180_000).hex()
    return f"{salt}${digest}"
def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt, digest = stored_hash.split("$", 1)
    except ValueError:
        return False
    check = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 180_000).hex()
    return hmac.compare_digest(check, digest)
def _password_marker(password_hash: str) -> str:
    return hmac.new(SECRET_KEY.encode(), password_hash.encode(), hashlib.sha256).hexdigest()[:24]


def create_session_token(user_id: int, password_hash: str = "") -> str:
    if running_in_production() and not password_hash:
        raise ValueError("Produkciona sesija zahteva oznaku lozinke.")
    marker = _password_marker(password_hash) if password_hash else "-"
    payload = base64.urlsafe_b64encode(f"2:{user_id}:{int(time.time())}:{marker}".encode()).decode().rstrip("=")
    sig = hmac.new(SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{sig}"


def _session_payload(token: Optional[str]) -> Optional[str]:
    if not token or "." not in token or len(token) > 256:
        return None
    payload, sig = token.split(".", 1)
    expected = hmac.new(SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected):
        return None
    try:
        return base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)).decode()
    except (ValueError, UnicodeDecodeError, binascii.Error):
        return None


def read_session_token(token: Optional[str]) -> Optional[int]:
    payload = _session_payload(token)
    if payload is None:
        return None
    try:
        if payload.isdecimal():
            return int(payload) if time.time() < LEGACY_SESSION_END else None
        version, user_id, issued_at, marker = payload.split(":", 3)
        age = time.time() - int(issued_at)
        if version != "2" or not 0 <= age <= SESSION_TTL_SECONDS or not marker:
            return None
        return int(user_id)
    except (ValueError, OverflowError):
        return None


def is_legacy_session(token: Optional[str]) -> bool:
    payload = _session_payload(token)
    return bool(payload and payload.isdecimal())


def session_matches_user(token: Optional[str], password_hash: str, role: str, legacy_revoked: bool = False) -> bool:
    payload = _session_payload(token)
    if payload is None or read_session_token(token) is None:
        return False
    if payload.isdecimal():
        return not legacy_revoked
    try:
        _, _, issued_at, marker = payload.split(":", 3)
        if role == "admin" and time.time() - int(issued_at) > ADMIN_SESSION_TTL_SECONDS:
            return False
        return (marker == "-" and not running_in_production()) or hmac.compare_digest(marker, _password_marker(password_hash))
    except (ValueError, OverflowError):
        return False
def make_referral_code(name: str = "") -> str:
    clean = "".join(ch for ch in name.upper() if ch.isalnum())[:5] or "KZ"
    return f"{clean}{secrets.token_hex(3).upper()}"
