import base64, hashlib, hmac, os, secrets
from typing import Optional

APP_ENV = os.getenv("APP_ENV", "development").strip().lower()
_configured_secret = os.getenv("KLIKZARADA_SECRET_KEY", "").strip()
if APP_ENV in {"production", "prod"} and not _configured_secret:
    raise RuntimeError("KLIKZARADA_SECRET_KEY mora biti postavljen u produkciji.")

# A local-only fallback keeps onboarding simple, but production never starts
# with a predictable signing key.
SECRET_KEY = _configured_secret or "CHANGE_ME_BEFORE_LIVE_KLIKZARADA_V3"
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
def create_session_token(user_id: int) -> str:
    payload = base64.urlsafe_b64encode(str(user_id).encode()).decode().rstrip("=")
    sig = hmac.new(SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{sig}"
def read_session_token(token: Optional[str]) -> Optional[int]:
    if not token or "." not in token: return None
    payload, sig = token.split(".", 1)
    expected = hmac.new(SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected): return None
    try:
        return int(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)).decode())
    except Exception:
        return None
def make_referral_code(name: str = "") -> str:
    clean = "".join(ch for ch in name.upper() if ch.isalnum())[:5] or "KZ"
    return f"{clean}{secrets.token_hex(3).upper()}"
