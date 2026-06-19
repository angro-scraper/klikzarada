from __future__ import annotations

from fastapi import APIRouter, Response, HTTPException, status, Request
from pydantic import BaseModel

from ..services.admin_auth import COOKIE_NAME, admin_pin, cookie_secure, create_admin_token, is_request_admin, session_hours

router = APIRouter(prefix="/auth", tags=["auth"])


class AdminLoginRequest(BaseModel):
    pin: str


@router.post("/admin/login", response_model=dict)
def admin_login(payload: AdminLoginRequest, response: Response):
    if payload.pin.strip() != admin_pin():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Pogrešan admin PIN")
    token, max_age = create_admin_token()
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=max_age,
        httponly=True,
        samesite="lax",
        secure=cookie_secure(),
        path="/",
    )
    return {"ok": True, "role": "admin", "session_hours": session_hours()}


@router.get("/admin/session", response_model=dict)
def admin_session(request: Request):
    return {"authenticated": is_request_admin(request), "role": "admin" if is_request_admin(request) else None}


@router.post("/admin/logout", response_model=dict)
def admin_logout(response: Response):
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"ok": True}
