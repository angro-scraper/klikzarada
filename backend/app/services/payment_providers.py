from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import quote, urlencode

from .. import models


def public_base_url() -> str:
    return os.getenv("PUBLIC_BASE_URL", "http://127.0.0.1:8000").rstrip("/")


def active_payment_provider() -> str:
    return os.getenv("PAYMENT_PROVIDER", "pay_on_pickup").strip().lower() or "pay_on_pickup"


def money_for_ips(amount: float) -> str:
    # NBS IPS format uses currency prefix and decimal comma, e.g. RSD1234,56
    return "RSD" + f"{float(amount or 0):.2f}".replace(".", ",")


def compact_reference(code: str) -> str:
    prefix = os.getenv("PAYMENT_REFERENCE_PREFIX", "SH").strip().upper() or "SH"
    safe = "".join(ch for ch in str(code or "").upper() if ch.isalnum())
    return f"{prefix}{safe}"[:35]


def reservation_url(code: str) -> str:
    return f"{public_base_url()}/reservation?code={quote(str(code).upper())}"


def checkout_url(code: str) -> str:
    return f"{public_base_url()}/checkout?code={quote(str(code).upper())}"


def qr_ticket_url(code: str) -> str:
    return f"{public_base_url()}/qr/reservation/{quote(str(code).upper())}.svg"


def qr_payment_url(code: str) -> str:
    return f"{public_base_url()}/qr/payment/{quote(str(code).upper())}.svg"


def paypal_amount_from_reservation(reservation: models.Reservation) -> float:
    """Converts reservation payable amount to the PayPal currency for MVP checkout.

    Prices in the app are normally in RSD. PayPal checkout in this MVP uses EUR/USD/etc.
    The conversion rate is deliberately configurable in .env so the founder controls it.
    """
    amount = float(getattr(reservation, "payable_amount", 0) or 0)
    source_currency = (getattr(reservation, "currency", "RSD") or "RSD").upper()
    target_currency = paypal_currency()
    if source_currency == target_currency:
        return round(amount, 2)
    if source_currency == "RSD" and target_currency == "EUR":
        try:
            rate = float(os.getenv("PAYPAL_RSD_TO_EUR_RATE", "117.0") or "117.0")
        except Exception:
            rate = 117.0
        if rate <= 0:
            rate = 117.0
        return round(amount / rate, 2)
    if source_currency == "RSD" and target_currency == "USD":
        try:
            rate = float(os.getenv("PAYPAL_RSD_TO_USD_RATE", "108.0") or "108.0")
        except Exception:
            rate = 108.0
        if rate <= 0:
            rate = 108.0
        return round(amount / rate, 2)
    return round(amount, 2)


def paypal_currency() -> str:
    return (os.getenv("PAYPAL_CURRENCY", "EUR").strip().upper() or "EUR")[:3]


def paypal_checkout_url(reservation: models.Reservation) -> str:
    business = os.getenv("PAYPAL_BUSINESS_EMAIL", "").strip()
    if not business:
        raise ValueError("Nedostaje PAYPAL_BUSINESS_EMAIL u .env fajlu. Unesi PayPal Business email ili koristi plaćanje pri preuzimanju.")
    mode = os.getenv("PAYPAL_MODE", "live").strip().lower()
    base = "https://www.sandbox.paypal.com/cgi-bin/webscr" if mode == "sandbox" else "https://www.paypal.com/cgi-bin/webscr"
    code = str(reservation.reservation_code).upper()
    currency = paypal_currency()
    amount = paypal_amount_from_reservation(reservation)
    params = {
        "cmd": "_xclick",
        "business": business,
        "item_name": f"Sačuvaj Hranu rezervacija {code}",
        "item_number": code,
        "amount": f"{amount:.2f}",
        "currency_code": currency,
        "custom": code,
        "invoice": code,
        "no_shipping": "1",
        "return": reservation_url(code),
        "cancel_return": checkout_url(code),
        "notify_url": f"{public_base_url()}/payments/paypal/ipn",
    }
    return f"{base}?{urlencode(params)}"


@dataclass
class CheckoutData:
    provider: str
    provider_ready: bool
    method: str
    checkout_url: str
    reservation_url: str
    reservation_qr_url: str
    payment_qr_url: str | None
    instructions: str
    provider_message: str | None = None
    ips_payload: str | None = None
    provider_redirect_url: str | None = None
    provider_amount: float | None = None
    provider_currency: str | None = None
    can_pay_on_pickup: bool = True


def build_ips_payload(reservation: models.Reservation) -> str:
    account = os.getenv("MERCHANT_ACCOUNT", "").strip().replace(" ", "")
    if not account:
        raise ValueError("Nedostaje MERCHANT_ACCOUNT u .env fajlu. Bez računa primaoca nema stvarnog IPS QR plaćanja.")

    merchant_name = os.getenv("MERCHANT_NAME", "Sačuvaj Hranu").strip() or "Sačuvaj Hranu"
    merchant_address = os.getenv("MERCHANT_ADDRESS", "Beograd").strip() or "Beograd"
    payment_code = os.getenv("MERCHANT_PAYMENT_CODE", "189").strip() or "189"
    amount = money_for_ips(float(getattr(reservation, "payable_amount", 0) or 0))
    payer = f"{reservation.customer_name}\n{reservation.customer_phone}".strip()
    purpose_template = os.getenv("MERCHANT_PAYMENT_PURPOSE", "Sačuvaj Hranu rezervacija {code}")
    purpose = purpose_template.format(code=reservation.reservation_code)
    reference = compact_reference(reservation.reservation_code)

    # NBS IPS QR textual payload for payment order. Field names are standardized; merchant data is taken from .env.
    parts = [
        "K:PR",
        "V:01",
        "C:1",
        f"R:{account}",
        f"N:{merchant_name}\n{merchant_address}",
        f"I:{amount}",
        f"P:{payer}",
        f"SF:{payment_code}",
        f"S:{purpose}",
        f"RO:{reference}",
    ]
    return "|".join(parts)


def checkout_for_reservation(reservation: models.Reservation) -> CheckoutData:
    provider = active_payment_provider()
    code = reservation.reservation_code
    base_checkout = checkout_url(code)
    base_reservation = reservation_url(code)
    ticket_qr = qr_ticket_url(code)

    if provider in {"paypal", "paypal_standard", "paypal_checkout"}:
        currency = paypal_currency()
        amount = paypal_amount_from_reservation(reservation)
        try:
            url = paypal_checkout_url(reservation)
            message = None
            if (reservation.currency or "RSD").upper() != currency:
                message = f"Iznos u aplikaciji je {float(reservation.payable_amount or 0):.2f} {reservation.currency or 'RSD'}, a PayPal naplata je približno {amount:.2f} {currency}. Kurs se podešava u .env."
            return CheckoutData(
                provider="paypal",
                provider_ready=True,
                method=f"PayPal {currency}",
                checkout_url=base_checkout,
                reservation_url=base_reservation,
                reservation_qr_url=ticket_qr,
                payment_qr_url=None,
                provider_redirect_url=url,
                provider_amount=amount,
                provider_currency=currency,
                instructions="Klikni na PayPal dugme. Posle plaćanja vratićeš se na digitalnu kartu. U MVP režimu admin potvrđuje uplatu u finansijama ako nema webhook/IPN potvrde.",
                provider_message=message,
                can_pay_on_pickup=True,
            )
        except ValueError as exc:
            return CheckoutData(
                provider="paypal",
                provider_ready=False,
                method=f"PayPal {currency}",
                checkout_url=base_checkout,
                reservation_url=base_reservation,
                reservation_qr_url=ticket_qr,
                payment_qr_url=None,
                provider_amount=amount,
                provider_currency=currency,
                instructions="PayPal je izabran, ali nije podešen Business email. Kupac može da izabere plaćanje pri preuzimanju.",
                provider_message=str(exc),
                can_pay_on_pickup=True,
            )

    if provider in {"pickup", "pay_on_pickup", "cash", "cash_on_pickup"}:
        return CheckoutData(
            provider="pay_on_pickup",
            provider_ready=True,
            method="Plaćanje pri preuzimanju",
            checkout_url=base_checkout,
            reservation_url=base_reservation,
            reservation_qr_url=ticket_qr,
            payment_qr_url=None,
            instructions="Online plaćanje nije obavezno. Rezerviši proizvod i plati direktno prodavcu pri preuzimanju. Platformska provizija ostaje interna evidencija za obračun sa prodavcem.",
            provider_message="Online plaćanje je trenutno isključeno. Kupac plaća kod prodavca.",
            can_pay_on_pickup=True,
        )

    if provider in {"ips", "ips_qr", "nbs_ips"}:
        try:
            payload = build_ips_payload(reservation)
            return CheckoutData(
                provider="ips_qr",
                provider_ready=True,
                method="IPS SCAN QR",
                checkout_url=base_checkout,
                reservation_url=base_reservation,
                reservation_qr_url=ticket_qr,
                payment_qr_url=qr_payment_url(code),
                instructions="Skeniraj IPS QR kod kroz m-banking aplikaciju. Posle plaćanja prodavac/admin potvrđuje uplatu u sistemu ili se povezuje bankarski callback.",
                ips_payload=payload,
                can_pay_on_pickup=True,
            )
        except ValueError as exc:
            return CheckoutData(
                provider="ips_qr",
                provider_ready=False,
                method="IPS SCAN QR",
                checkout_url=base_checkout,
                reservation_url=base_reservation,
                reservation_qr_url=ticket_qr,
                payment_qr_url=None,
                instructions="IPS QR je izabran, ali nije podešen račun primaoca. Kupac može da izabere plaćanje pri preuzimanju.",
                provider_message=str(exc),
                can_pay_on_pickup=True,
            )

    if provider in {"monri", "wspay", "monri_wspay"}:
        monri_checkout = os.getenv("MONRI_CHECKOUT_URL", "").strip()
        merchant_id = os.getenv("MONRI_MERCHANT_ID", "").strip()
        ready = bool(monri_checkout and merchant_id)
        return CheckoutData(
            provider="monri_wspay",
            provider_ready=ready,
            method="Kartica / Monri WSPay",
            checkout_url=base_checkout,
            reservation_url=base_reservation,
            reservation_qr_url=ticket_qr,
            payment_qr_url=ticket_qr,
            provider_redirect_url=monri_checkout if ready else None,
            instructions="Za kartično plaćanje korisnik se preusmerava na payment gateway stranicu provajdera. Potrebni su merchant podaci i callback URL od provajdera.",
            provider_message=None if ready else "Monri/WSPay adapter je spreman, ali u .env još nisu uneti MONRI_CHECKOUT_URL i MONRI_MERCHANT_ID.",
            can_pay_on_pickup=True,
        )

    # Demo fallback remains for local testing.
    return CheckoutData(
        provider="demo",
        provider_ready=True,
        method="Demo plaćanje",
        checkout_url=base_checkout,
        reservation_url=base_reservation,
        reservation_qr_url=ticket_qr,
        payment_qr_url=ticket_qr,
        instructions="Demo režim ne naplaćuje stvarnu karticu. Koristi se samo za lokalno testiranje toka plaćanja.",
        can_pay_on_pickup=True,
    )


def get_payment_provider_status() -> dict:
    """Small status payload for admin readiness screens."""
    provider = active_payment_provider()
    missing: list[str] = []
    ready = True
    if provider in {"ips", "ips_qr", "nbs_ips"}:
        ready = bool(os.getenv("MERCHANT_ACCOUNT", "").strip())
        if not ready:
            missing.append("MERCHANT_ACCOUNT")
    elif provider in {"paypal", "paypal_standard", "paypal_checkout"}:
        ready = bool(os.getenv("PAYPAL_BUSINESS_EMAIL", "").strip())
        if not ready:
            missing.append("PAYPAL_BUSINESS_EMAIL")
    elif provider in {"monri", "wspay", "monri_wspay"}:
        for key in ["MONRI_CHECKOUT_URL", "MONRI_MERCHANT_ID"]:
            if not os.getenv(key, "").strip():
                missing.append(key)
        ready = not missing
    elif provider in {"pickup", "pay_on_pickup", "cash", "cash_on_pickup"}:
        ready = True
    return {
        "provider": provider,
        "provider_ready": ready,
        "missing": missing,
        "public_base_url": public_base_url(),
        "paypal_currency": paypal_currency(),
        "pay_on_pickup_available": True,
    }
