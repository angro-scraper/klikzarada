from __future__ import annotations

import io
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session
import segno

from .. import models
from ..database import get_db
from ..services.payment_providers import reservation_url, build_ips_payload
from ..services.pricing import apply_pricing_to_reservation

router = APIRouter(prefix="/qr", tags=["qr"])


def _svg_qr(data: str) -> Response:
    out = io.BytesIO()
    qr = segno.make(data, error="m")
    qr.save(out, kind="svg", scale=5, xmldecl=False, svgns=True)
    return Response(
        out.getvalue(),
        media_type="image/svg+xml",
        headers={
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


def _reservation_by_code(db: Session, reservation_code: str) -> models.Reservation:
    reservation = db.query(models.Reservation).filter(
        models.Reservation.reservation_code == reservation_code.upper()
    ).first()
    if not reservation:
        raise HTTPException(status_code=404, detail="Rezervacija nije pronađena")
    return reservation


@router.get("/reservation/{reservation_code}.svg", include_in_schema=False)
def reservation_ticket_qr(reservation_code: str, db: Session = Depends(get_db)):
    reservation = _reservation_by_code(db, reservation_code)
    return _svg_qr(reservation_url(reservation.reservation_code))


@router.get("/payment/{reservation_code}.svg", include_in_schema=False)
def payment_ips_qr(reservation_code: str, db: Session = Depends(get_db)):
    reservation = _reservation_by_code(db, reservation_code)
    apply_pricing_to_reservation(db, reservation)
    try:
        payload = build_ips_payload(reservation)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return _svg_qr(payload)
