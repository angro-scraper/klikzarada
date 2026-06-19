from __future__ import annotations

import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

from .pricing import normalize_phone

DATA_DIR = Path(__file__).resolve().parents[1].parent / "data"
NOTIFICATION_FILE = DATA_DIR / "notifications_log.json"


def _now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def sms_provider() -> str:
    return os.getenv("SMS_PROVIDER", "mock").strip().lower() or "mock"


def sms_enabled() -> bool:
    return os.getenv("SMS_ENABLED", "true").lower() in {"1", "true", "yes", "da"}


def sms_dry_run() -> bool:
    return os.getenv("SMS_DRY_RUN", "true").lower() in {"1", "true", "yes", "da"}


def customer_notifications_enabled() -> bool:
    return os.getenv("CUSTOMER_SMS_NOTIFICATIONS", "true").lower() in {"1", "true", "yes", "da"}


def seller_notifications_enabled() -> bool:
    return os.getenv("SELLER_SMS_NOTIFICATIONS", "false").lower() in {"1", "true", "yes", "da"}


def _load_log() -> list[dict[str, Any]]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not NOTIFICATION_FILE.exists():
        return []
    try:
        data = json.loads(NOTIFICATION_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _save_log(rows: list[dict[str, Any]]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    # Keep the local MVP log bounded so the JSON file does not grow forever.
    NOTIFICATION_FILE.write_text(json.dumps(rows[-1000:], ensure_ascii=False, indent=2), encoding="utf-8")


def log_notification(row: dict[str, Any]) -> dict[str, Any]:
    rows = _load_log()
    payload = {
        "id": f"N{int(time.time() * 1000)}",
        "created_at": _now_iso(),
        "channel": row.get("channel", "sms"),
        "provider": row.get("provider", sms_provider()),
        "purpose": row.get("purpose", "general"),
        "to": mask_phone(row.get("to", "")),
        "to_raw_last4": normalize_phone(row.get("to", ""))[-4:],
        "message": row.get("message", ""),
        "status": row.get("status", "created"),
        "error": row.get("error"),
        "metadata": row.get("metadata", {}),
    }
    rows.append(payload)
    _save_log(rows)
    return payload


def list_notifications(limit: int = 100, purpose: str | None = None, status: str | None = None) -> list[dict[str, Any]]:
    rows = list(reversed(_load_log()))
    if purpose:
        rows = [r for r in rows if r.get("purpose") == purpose]
    if status:
        rows = [r for r in rows if r.get("status") == status]
    return rows[: max(1, min(limit, 500))]


def notification_status() -> dict[str, Any]:
    provider = sms_provider()
    configured = True
    missing: list[str] = []
    if provider == "http_api" and not os.getenv("SMS_HTTP_URL"):
        configured = False
        missing.append("SMS_HTTP_URL")
    return {
        "sms_enabled": sms_enabled(),
        "sms_provider": provider,
        "sms_dry_run": sms_dry_run(),
        "customer_sms_notifications": customer_notifications_enabled(),
        "seller_sms_notifications": seller_notifications_enabled(),
        "configured": configured,
        "missing": missing,
        "log_file": str(NOTIFICATION_FILE),
        "note": "mock/dry-run režim ne šalje stvaran SMS, već upisuje poruku u lokalni log.",
    }


def mask_phone(phone: str) -> str:
    normalized = normalize_phone(phone)
    if len(normalized) <= 4:
        return "***"
    return f"***{normalized[-4:]}"


def _http_api_send_sms(phone: str, message: str, purpose: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    url = os.getenv("SMS_HTTP_URL", "").strip()
    token = os.getenv("SMS_HTTP_TOKEN", "").strip()
    sender = os.getenv("SMS_SENDER", "SacuvajHranu").strip()
    timeout = float(os.getenv("SMS_HTTP_TIMEOUT_SECONDS", "10"))
    if not url:
        raise RuntimeError("SMS_HTTP_URL nije podešen")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = {
        "to": normalize_phone(phone),
        "from": sender,
        "text": message,
        "purpose": purpose,
        "metadata": metadata or {},
    }
    response = requests.post(url, headers=headers, json=body, timeout=timeout)
    response.raise_for_status()
    return {"provider_response_status": response.status_code, "provider_response": response.text[:500]}


def send_sms(phone: str, message: str, purpose: str = "general", metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    normalized = normalize_phone(phone)
    if len(normalized) < 5:
        return log_notification({
            "channel": "sms",
            "purpose": purpose,
            "to": phone,
            "message": message,
            "status": "failed",
            "error": "Neispravan broj telefona",
            "metadata": metadata or {},
        })
    if not sms_enabled():
        return log_notification({
            "channel": "sms",
            "purpose": purpose,
            "to": normalized,
            "message": message,
            "status": "skipped",
            "error": "SMS_ENABLED=false",
            "metadata": metadata or {},
        })

    provider = sms_provider()
    if sms_dry_run() or provider == "mock":
        return log_notification({
            "channel": "sms",
            "provider": provider,
            "purpose": purpose,
            "to": normalized,
            "message": message,
            "status": "mock_sent",
            "metadata": metadata or {},
        })

    try:
        provider_meta: dict[str, Any] = {}
        if provider == "http_api":
            provider_meta = _http_api_send_sms(normalized, message, purpose, metadata)
        else:
            raise RuntimeError(f"Nepodržan SMS_PROVIDER: {provider}")
        merged_metadata = dict(metadata or {})
        merged_metadata.update(provider_meta)
        return log_notification({
            "channel": "sms",
            "provider": provider,
            "purpose": purpose,
            "to": normalized,
            "message": message,
            "status": "sent",
            "metadata": merged_metadata,
        })
    except Exception as exc:
        return log_notification({
            "channel": "sms",
            "provider": provider,
            "purpose": purpose,
            "to": normalized,
            "message": message,
            "status": "failed",
            "error": str(exc),
            "metadata": metadata or {},
        })


def otp_message(code: str) -> str:
    template = os.getenv("SMS_OTP_TEMPLATE", "Sačuvaj Hranu kod za prijavu je {code}. Važi 10 minuta.")
    return template.replace("{code}", str(code))


def reservation_created_message(code: str, product_name: str | None, payable_amount: float | None = None) -> str:
    amount_part = f" Iznos za plaćanje: {round(float(payable_amount or 0), 2)} RSD." if payable_amount else ""
    name = product_name or "ponuda"
    return f"Sačuvaj Hranu: rezervacija {code} za {name} je napravljena.{amount_part} Kartu otvori u aplikaciji."


def reservation_status_message(code: str, status: str) -> str:
    labels = {
        "confirmed": "potvrđena",
        "picked_up": "označena kao preuzeta",
        "cancelled": "otkazana",
        "expired": "istekla",
        "pending": "na čekanju",
    }
    return f"Sačuvaj Hranu: rezervacija {code} je {labels.get(status, status)}."
