from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..services.admin_auth import require_admin_session
from ..services.json_store import append_json_row, read_json, update_json_row
from ..services.notifications import send_sms

router = APIRouter(prefix="/support-tickets", tags=["support-tickets"])
TICKETS_FILE = "support_tickets.json"


class SupportTicketCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    phone: str | None = Field(default=None, max_length=80)
    email: str | None = Field(default=None, max_length=160)
    reservation_code: str | None = Field(default=None, max_length=40)
    topic: str = Field(default="general", max_length=80)
    message: str = Field(..., min_length=5, max_length=2000)
    source_page: str | None = Field(default=None, max_length=250)


class TicketUpdate(BaseModel):
    status: str = Field(default="open", pattern="^(open|in_progress|waiting_customer|resolved|closed)$")
    internal_note: str | None = Field(default=None, max_length=2000)
    priority: str | None = Field(default=None, pattern="^(low|normal|high|urgent)$")
    assigned_to: str | None = Field(default=None, max_length=120)


def _ticket_priority(topic: str, message: str) -> str:
    text = f"{topic} {message}".lower()
    if topic == "food_safety" or any(word in text for word in ["trovanje", "pokvar", "alergen", "bezbednost", "neispravno"]):
        return "urgent"
    if topic in {"payment", "pickup"} or any(word in text for word in ["plać", "plac", "refund", "nije preuzeo", "kasni"]):
        return "high"
    return "normal"


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        return None


def _reservation_context(db: Session, code: str | None) -> dict | None:
    if not code:
        return None
    reservation = db.query(models.Reservation).filter(
        models.Reservation.reservation_code == code.strip().upper()
    ).first()
    if not reservation:
        return None
    product = reservation.product
    store = product.store if product else None
    return {
        "reservation_id": reservation.id,
        "reservation_code": reservation.reservation_code,
        "reservation_status": reservation.status,
        "payment_status": reservation.payment_status,
        "customer_name": reservation.customer_name,
        "customer_phone": reservation.customer_phone,
        "payable_amount": reservation.payable_amount,
        "product_id": product.id if product else None,
        "product_name": product.name if product else None,
        "store_id": store.id if store else None,
        "store_name": store.name if store else None,
        "ticket_url": f"/reservation?code={reservation.reservation_code}",
    }


def _enrich_ticket(db: Session, ticket: dict) -> dict:
    enriched = dict(ticket)
    enriched["reservation"] = _reservation_context(db, ticket.get("reservation_code"))
    created = _parse_dt(ticket.get("created_at"))
    if created and ticket.get("status") not in {"resolved", "closed"}:
        enriched["age_minutes"] = max(0, int((datetime.utcnow() - created).total_seconds() // 60))
    else:
        enriched["age_minutes"] = None
    return enriched


@router.post("", response_model=dict)
def create_ticket(payload: SupportTicketCreate):
    priority = _ticket_priority(payload.topic, payload.message)
    ticket = append_json_row(TICKETS_FILE, {
        "name": payload.name.strip(),
        "phone": payload.phone.strip() if payload.phone else None,
        "email": payload.email.strip() if payload.email else None,
        "reservation_code": payload.reservation_code.strip().upper() if payload.reservation_code else None,
        "topic": payload.topic,
        "message": payload.message.strip(),
        "source_page": payload.source_page,
        "status": "open",
        "priority": priority,
        "assigned_to": None,
        "internal_note": None,
    })
    return {"ok": True, "ticket": ticket, "message": "Prijava je primljena. Podrška će je pregledati."}


@router.get("", response_model=list[dict])
def list_tickets(
    request: Request,
    status: str | None = Query(default=None),
    topic: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    q: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
    _: bool = Depends(require_admin_session),
    db: Session = Depends(get_db),
):
    rows = list(reversed(read_json(TICKETS_FILE, [])))
    if status:
        rows = [r for r in rows if r.get("status") == status]
    if topic:
        rows = [r for r in rows if r.get("topic") == topic]
    if priority:
        rows = [r for r in rows if r.get("priority") == priority]
    if q:
        needle = q.strip().lower()
        rows = [
            r for r in rows
            if needle in " ".join(str(r.get(k) or "") for k in ["id", "name", "phone", "email", "reservation_code", "topic", "message", "internal_note"]).lower()
        ]
    return [_enrich_ticket(db, row) for row in rows[:limit]]


@router.get("/summary", response_model=dict)
def support_summary(request: Request, _: bool = Depends(require_admin_session), db: Session = Depends(get_db)):
    rows = read_json(TICKETS_FILE, [])
    if not isinstance(rows, list):
        rows = []
    open_rows = [r for r in rows if r.get("status") not in {"resolved", "closed"}]
    linked = 0
    for row in rows:
        if _reservation_context(db, row.get("reservation_code")):
            linked += 1
    by_status: dict[str, int] = {}
    by_priority: dict[str, int] = {}
    oldest_open = 0
    for row in rows:
        by_status[row.get("status", "open")] = by_status.get(row.get("status", "open"), 0) + 1
        by_priority[row.get("priority", "normal")] = by_priority.get(row.get("priority", "normal"), 0) + 1
    for row in open_rows:
        created = _parse_dt(row.get("created_at"))
        if created:
            oldest_open = max(oldest_open, int((datetime.utcnow() - created).total_seconds() // 60))
    return {
        "ok": True,
        "total": len(rows),
        "open": len(open_rows),
        "urgent_open": sum(1 for r in open_rows if r.get("priority") == "urgent"),
        "waiting_customer": sum(1 for r in rows if r.get("status") == "waiting_customer"),
        "resolved": sum(1 for r in rows if r.get("status") in {"resolved", "closed"}),
        "linked_reservations": linked,
        "oldest_open_minutes": oldest_open,
        "by_status": by_status,
        "by_priority": by_priority,
    }


@router.patch("/{ticket_id}", response_model=dict)
def update_ticket(ticket_id: str, payload: TicketUpdate, request: Request, _: bool = Depends(require_admin_session)):
    updated = update_json_row(TICKETS_FILE, ticket_id, payload.model_dump(exclude_none=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Ticket nije pronađen")
    if updated.get("phone") and payload.status in {"resolved", "closed"}:
        try:
            send_sms(updated["phone"], f"Sačuvaj Hranu: vaša prijava {ticket_id} je označena kao {payload.status}.", purpose="support_status", metadata={"ticket_id": ticket_id})
        except Exception:
            pass
    return {"ok": True, "ticket": updated}
