"""Provera konfiguracije domacih RSD bankarskih tokova."""

import re

from sqlalchemy.orm import Session

from .models import SystemSetting


def normalize_rs_account(value: str) -> str | None:
    text = (value or "").strip()
    if not re.fullmatch(r"[0-9 -]+", text):
        return None
    digits = re.sub(r"[ -]", "", text)
    return digits if len(digits) == 18 else None


def company_bank_config(db: Session) -> dict:
    keys = (
        "advertiser_payment_account", "advertiser_payment_holder",
        "user_payout_account", "user_payout_holder", "payment_reference",
        "payout_reference", "bank_note",
    )
    rows = db.query(SystemSetting).filter(SystemSetting.key.in_(keys)).all()
    values = {row.key: (row.value or "").strip() for row in rows}
    def clean(key: str) -> str:
        value = values.get(key, "")
        return "" if value.lower().startswith(("dodaj ", "podesi ")) else value

    payment_account = normalize_rs_account(clean("advertiser_payment_account"))
    payout_account = normalize_rs_account(clean("user_payout_account"))
    payment_holder = clean("advertiser_payment_holder")
    payout_holder = clean("user_payout_holder")
    return {
        "advertiser_payment_account": payment_account or "",
        "advertiser_payment_holder": payment_holder,
        "user_payout_account": payout_account or "",
        "user_payout_holder": payout_holder,
        "payment_reference": clean("payment_reference") or "KlikZarada budzet",
        "payout_reference": clean("payout_reference") or "KlikZarada isplata",
        "bank_note": clean("bank_note"),
        "bank_payments_ready": bool(payment_account and payment_holder),
        "bank_payouts_ready": bool(payout_account and payout_holder),
    }
