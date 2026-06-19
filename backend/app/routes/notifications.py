from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field

from ..services.admin_auth import require_admin_session
from ..services.notifications import list_notifications, notification_status, send_sms

router = APIRouter(prefix="/notifications", tags=["notifications"])


class TestSmsRequest(BaseModel):
    phone: str = Field(..., min_length=5, max_length=40)
    message: str = Field(default="Sačuvaj Hranu test SMS poruka.", max_length=500)


@router.get("/status", response_model=dict)
def get_notification_status(request: Request, _: bool = Depends(require_admin_session)):
    return notification_status()


@router.get("/log", response_model=list[dict])
def get_notification_log(
    request: Request,
    limit: int = Query(default=100, ge=1, le=500),
    purpose: str | None = None,
    status: str | None = None,
    _: bool = Depends(require_admin_session),
):
    return list_notifications(limit=limit, purpose=purpose, status=status)


@router.post("/test-sms", response_model=dict)
def send_test_sms(payload: TestSmsRequest, request: Request, _: bool = Depends(require_admin_session)):
    result = send_sms(payload.phone, payload.message, purpose="admin_test", metadata={"source": "notifications_admin"})
    return {"ok": result.get("status") not in {"failed"}, "notification": result}
