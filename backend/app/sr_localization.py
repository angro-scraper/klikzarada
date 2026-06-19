
STATUS_LABELS_SR = {
    "DRAFT": "Nacrt",
    "READY_FOR_REVIEW": "Spremno za pregled",
    "ISSUED": "Izdat račun",
    "SENT": "Poslat partneru",
    "PARTIALLY_PAID": "Delimično plaćen",
    "PAID": "Plaćen",
    "OVERDUE": "Kasni",
    "DISPUTED": "Sporan",
    "VOID": "Poništen",
    "PENDING": "Na čekanju",
    "CONFIRMED": "Potvrđeno",
    "FAILED": "Neuspešno",
}
ACTION_LABELS_SR = {
    "ISSUE_INVOICE": "Izdavanje računa",
    "SEND_INVOICE": "Slanje računa",
    "RECORD_MANUAL_PAYMENT": "Ručno evidentirana uplata",
    "MARK_INVOICE_OVERDUE": "Označen kao dospeo / u kašnjenju",
    "MARK_INVOICE_DISPUTED": "Označen kao sporan",
    "VOID_INVOICE": "Poništavanje računa",
    "GENERATE_DEMO_MONTHLY_INVOICE": "Generisan mesečni račun",
    "RESOLVE_RECONCILIATION_EXCEPTION": "Rešena neusaglašenost",
}
def status_sr(value: str | None) -> str:
    if not value:
        return "Nepoznato"
    return STATUS_LABELS_SR.get(str(value).upper(), str(value))
def action_sr(value: str | None) -> str:
    if not value:
        return "Nepoznata akcija"
    return ACTION_LABELS_SR.get(str(value).upper(), str(value))
def money_sr(amount, currency="RSD") -> str:
    try:
        number = float(amount or 0)
    except Exception:
        number = 0.0
    formatted = f"{number:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{formatted} {currency or 'RSD'}"
def date_sr(value) -> str:
    if not value:
        return "-"
    try:
        if hasattr(value, "strftime"):
            return value.strftime("%d.%m.%Y")
        raw = str(value)
        if "T" in raw:
            raw = raw.split("T", 1)[0]
        parts = raw.split("-")
        if len(parts) == 3:
            return f"{parts[2]}.{parts[1]}.{parts[0]}"
        return str(value)
    except Exception:
        return str(value)
