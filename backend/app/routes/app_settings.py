from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from ..services.admin_auth import require_admin_session
from ..services.json_store import read_json, write_json, utc_now

router = APIRouter(prefix="/app-settings", tags=["app-settings"])
SETTINGS_FILE = "app_settings.json"

DEFAULT_SETTINGS = {
    "app_name": "Sačuvaj Hranu",
    "market": "Srbija",
    "default_currency": "RSD",
    "platform_commission_percent": 25,
    "loyalty_discounts": [1, 2, 3, 4, 5],
    "payment_note": "Aplikacija podržava online plaćanje kada je provider podešen. IPS QR se potvrđuje ručno u finansijama dok se ne poveže bankarski webhook.",
    "cities": ["Beograd", "Novi Sad", "Niš", "Kragujevac", "Subotica", "Zrenjanin", "Pančevo", "Čačak", "Kraljevo", "Novi Pazar", "Leskovac", "Valjevo", "Sombor", "Kruševac", "Užice", "Šabac", "Požarevac", "Vršac", "Smederevo", "Zaječar"],
    "belgrade_areas": ["Novi Beograd", "Zemun", "Vračar", "Stari grad", "Dorćol", "Palilula", "Zvezdara", "Voždovac", "Čukarica", "Banovo brdo", "Rakovica", "Savski venac", "Mirijevo", "Karaburma", "Banjica", "Beograd na vodi"],
    "categories": ["pekara", "restoran", "market", "mlečni proizvodi", "voće i povrće", "mesara", "ribarnica", "poslastice", "gotova jela", "zdrava hrana", "delikates", "pića", "smrznuta hrana", "sendviči", "salate", "korpa iznenađenja"],
    "product_rules": {
        "require_image_for_public_products": True,
        "near_expiry_requires_seller_confirmation": True,
        "auto_hide_expired": True,
        "max_reservation_quantity": 50
    },
    "feature_flags": {
        "online_payments": True,
        "ips_qr": True,
        "customer_otp": True,
        "sms_notifications": True,
        "seller_onboarding": True,
        "support_tickets": True,
        "ai_buyer_assistant": True
    },
    "legal_contact": {
        "company_name": "Sačuvaj Hranu DOO",
        "email": "support@foodsaver.local",
        "city": "Beograd"
    },
    "updated_at": None
}


class SettingsUpdate(BaseModel):
    settings: dict = Field(default_factory=dict)


def _settings() -> dict:
    saved = read_json(SETTINGS_FILE, {})
    if not isinstance(saved, dict):
        saved = {}
    merged = dict(DEFAULT_SETTINGS)
    for key, value in saved.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            nested = dict(merged[key])
            nested.update(value)
            merged[key] = nested
        else:
            merged[key] = value
    return merged


@router.get("/public", response_model=dict)
def public_settings():
    s = _settings()
    return {
        "app_name": s.get("app_name"),
        "market": s.get("market"),
        "default_currency": s.get("default_currency"),
        "cities": s.get("cities", []),
        "belgrade_areas": s.get("belgrade_areas", []),
        "categories": s.get("categories", []),
        "feature_flags": s.get("feature_flags", {}),
        "product_rules": s.get("product_rules", {}),
        "legal_contact": s.get("legal_contact", {}),
    }


@router.get("", response_model=dict)
def get_settings(request: Request, _: bool = Depends(require_admin_session)):
    return _settings()


@router.put("", response_model=dict)
def update_settings(payload: SettingsUpdate, request: Request, _: bool = Depends(require_admin_session)):
    current = _settings()
    incoming = dict(payload.settings or {})
    for key, value in incoming.items():
        if isinstance(value, dict) and isinstance(current.get(key), dict):
            nested = dict(current[key])
            nested.update(value)
            current[key] = nested
        else:
            current[key] = value
    current["updated_at"] = utc_now()
    return write_json(SETTINGS_FILE, current)


@router.post("/reset", response_model=dict)
def reset_settings(request: Request, _: bool = Depends(require_admin_session)):
    payload = dict(DEFAULT_SETTINGS)
    payload["updated_at"] = utc_now()
    return write_json(SETTINGS_FILE, payload)
