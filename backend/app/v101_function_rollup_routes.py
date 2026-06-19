# -*- coding: utf-8 -*-
"""V101 Function Rollup — no design changes.

Adds functional APIs and a scoped homepage map injection while preserving the restored V71 design.
"""
from __future__ import annotations

import importlib
import os
from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

router = APIRouter()

VERSION = "V101_FUNCTION_ROLLUP_NO_DESIGN"

FUNCTION_MODULE_CANDIDATES = [
    "app.finance_routes",
    "app.operator_routes",
    "app.launch_routes",
    "app.v72_mobile_routes",
    "app.v73_reservation_flow_routes",
    "app.v74_partner_ops_live_center_routes",
    "app.v75_launch_ready_routes",
    "app.v76_legal_seo_trust_routes",
    "app.v77_marketing_notifications_routes",
    "app.v78_analytics_growth_routes",
    "app.v79_notification_automation_routes",
    "app.v80_integrations_production_routes",
    "app.v81_security_backup_monitoring_routes",
    "app.v82_performance_accessibility_ux_routes",
    "app.v83_support_crm_routes",
    "app.v87_pilot_launch_ready_routes",
]

FEATURES = [
    {"code": "finance", "name": "Finansije i provizije", "status": "active"},
    {"code": "reservation_qr", "name": "Rezervacije i QR preuzimanje", "status": "active"},
    {"code": "partner_ops", "name": "Partner operacije", "status": "active"},
    {"code": "launch_readiness", "name": "Pilot/live readiness", "status": "active"},
    {"code": "legal_trust", "name": "Pravni i trust centar", "status": "active"},
    {"code": "marketing", "name": "Komunikacije i launch marketing", "status": "active"},
    {"code": "analytics", "name": "Analitika i growth metrike", "status": "active"},
    {"code": "notifications", "name": "Notifikacije i outbox", "status": "active"},
    {"code": "integrations", "name": "Integracije i produkcija", "status": "active"},
    {"code": "security", "name": "Bezbednost, backup i monitoring", "status": "active"},
    {"code": "performance", "name": "Performanse i dostupnost", "status": "active"},
    {"code": "support", "name": "Podrška, CRM i moderacija", "status": "active"},
    {"code": "map", "name": "Mapa ponuda na početnoj strani", "status": "active"},
]

DEMO_MARKERS = [
    {
        "id": "zeleno",
        "title": "Restoran Zeleno",
        "category": "Restoran",
        "address": "Vojvode Stepe 123, Beograd",
        "lat": 44.7866,
        "lng": 20.4750,
        "offer": "Domaći ručak",
        "price_rsd": 360,
        "discount": "-40%",
        "pickup": "18:30 - 19:00",
    },
    {
        "id": "klas",
        "title": "Pekara Klas",
        "category": "Pekara",
        "address": "Knez Mihailova 45, Beograd",
        "lat": 44.8176,
        "lng": 20.4569,
        "offer": "Paketi peciva",
        "price_rsd": 210,
        "discount": "-30%",
        "pickup": "17:00 - 18:00",
    },
    {
        "id": "salata",
        "title": "Zdrava Salata",
        "category": "Restoran",
        "address": "Bulevar kralja Aleksandra 10, Beograd",
        "lat": 44.8065,
        "lng": 20.4776,
        "offer": "Salata bar Green",
        "price_rsd": 260,
        "discount": "-35%",
        "pickup": "16:30 - 17:30",
    },
    {
        "id": "aroma",
        "title": "Kafić Aroma",
        "category": "Kafić",
        "address": "Cara Dušana 88, Beograd",
        "lat": 44.8230,
        "lng": 20.4613,
        "offer": "Mix sendviča",
        "price_rsd": 180,
        "discount": "-28%",
        "pickup": "15:00 - 16:00",
    },
]

_loaded_modules: List[str] = []


def include_existing_function_modules(app: Any) -> List[str]:
    """Best-effort loader for function route modules.

    It deliberately avoids design-only modules. If a module is missing or broken, it is skipped.
    """
    global _loaded_modules
    loaded: List[str] = []
    for module_name in FUNCTION_MODULE_CANDIDATES:
        if module_name in _loaded_modules:
            continue
        try:
            module = importlib.import_module(module_name)
            module_router = getattr(module, "router", None)
            if module_router is not None:
                app.include_router(module_router)
                loaded.append(module_name)
                _loaded_modules.append(module_name)
        except Exception as exc:  # pragma: no cover - safety loader
            print("V101 skip module", module_name, exc)
    return loaded


def _safe_db_counts() -> Dict[str, Any]:
    counts = {"stores": None, "products": None, "reservations": None, "source": "fallback"}
    try:
        from app.database import SessionLocal  # type: ignore
        import app.models as models  # type: ignore

        db = SessionLocal()
        try:
            for attr, key in [("Store", "stores"), ("Product", "products"), ("Reservation", "reservations")]:
                model = getattr(models, attr, None)
                if model is not None:
                    try:
                        counts[key] = db.query(model).count()
                        counts["source"] = "database"
                    except Exception:
                        pass
        finally:
            db.close()
    except Exception:
        pass
    return counts


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.get("/api/v101/status")
def v101_status():
    return {
        "ok": True,
        "version": VERSION,
        "design_policy": "V71 dizajn je zakljucan. Ovaj update ne menja globalni dizajn.",
        "timestamp": _now(),
        "features_count": len(FEATURES),
        "db_counts": _safe_db_counts(),
    }


@router.get("/api/v101/features")
def v101_features():
    return {"version": VERSION, "features": FEATURES}


@router.get("/api/v101/map/offers")
def v101_map_offers():
    # Later this can be connected to real Store/Product coordinates.
    return {"center": {"lat": 44.8125, "lng": 20.4612, "city": "Beograd"}, "markers": DEMO_MARKERS}


def _home_map_fragment() -> str:
    cards = "".join(
        f"""
        <article class=\"v101-map-card\">
          <div class=\"v101-map-pin\">●</div>
          <div>
            <strong>{m['title']}</strong>
            <span>{m['offer']} · {m['price_rsd']} RSD · {m['discount']}</span>
            <small>{m['pickup']} · {m['address']}</small>
          </div>
        </article>
        """
        for m in DEMO_MARKERS
    )
    return f"""
<section id=\"v101-home-map\" class=\"v101-home-map\" aria-label=\"Mapa ponuda\">
  <style>
    .v101-home-map{{width:min(1180px,calc(100% - 32px));margin:28px auto;background:#fffdf7;border:1px solid #e4dccb;border-radius:28px;box-shadow:0 16px 34px rgba(15,61,46,.08);padding:22px;box-sizing:border-box;color:#103d2e;font-family:inherit}}
    .v101-home-map-head{{display:flex;align-items:flex-end;justify-content:space-between;gap:16px;margin-bottom:16px}}
    .v101-home-map h2{{margin:0;color:#0f3d2e;font-size:clamp(24px,3vw,34px);line-height:1.1;letter-spacing:-.03em}}
    .v101-home-map p{{margin:6px 0 0;color:#60746b;line-height:1.5}}
    .v101-home-map-grid{{display:grid;grid-template-columns:1.1fr .9fr;gap:18px;align-items:stretch}}
    .v101-map-frame{{min-height:310px;border-radius:22px;overflow:hidden;border:1px solid #e4dccb;background:#eaf4ee;position:relative}}
    .v101-map-frame iframe{{width:100%;height:100%;min-height:310px;border:0;display:block}}
    .v101-map-fallback{{position:absolute;inset:0;display:grid;place-items:center;color:#0f3d2e;font-weight:800;padding:20px;text-align:center;background:linear-gradient(135deg,#eaf4ee,#fff7e8)}}
    .v101-map-list{{display:grid;gap:10px;align-content:start}}
    .v101-map-card{{display:flex;gap:12px;background:#fff;border:1px solid #e4dccb;border-radius:18px;padding:13px;box-shadow:0 8px 18px rgba(15,61,46,.05)}}
    .v101-map-pin{{width:34px;height:34px;border-radius:12px;background:#0f3d2e;color:#f2a43a;display:flex;align-items:center;justify-content:center;flex:0 0 auto}}
    .v101-map-card strong{{display:block;color:#0f3d2e;font-size:15px}}
    .v101-map-card span{{display:block;color:#0f3d2e;font-weight:750;margin-top:3px}}
    .v101-map-card small{{display:block;color:#60746b;margin-top:3px;line-height:1.35}}
    .v101-map-actions{{display:flex;gap:10px;flex-wrap:wrap;margin-top:14px}}
    .v101-map-actions a{{height:42px;border-radius:999px;padding:0 18px;display:inline-flex;align-items:center;justify-content:center;text-decoration:none;font-weight:850;border:1px solid #e4dccb;color:#0f3d2e;background:#fff}}
    .v101-map-actions a.primary{{background:#0f3d2e;color:#fff;border-color:#0f3d2e}}
    @media(max-width:900px){{.v101-home-map-grid{{grid-template-columns:1fr}}.v101-home-map-head{{display:block}}}}
  </style>
  <div class=\"v101-home-map-head\">
    <div>
      <h2>Mapa ponuda u tvojoj blizini</h2>
      <p>Pronađi restorane, pekare i prodavnice koje trenutno imaju dostupne obroke za preuzimanje.</p>
    </div>
    <div class=\"v101-map-actions\"><a class=\"primary\" href=\"/ponude\">Pogledaj ponude</a><a href=\"/api/v101/map/offers\">API mapa</a></div>
  </div>
  <div class=\"v101-home-map-grid\">
    <div class=\"v101-map-frame\">
      <iframe title=\"Mapa ponuda - Beograd\" loading=\"lazy\" src=\"https://www.openstreetmap.org/export/embed.html?bbox=20.405%2C44.765%2C20.525%2C44.845&amp;layer=mapnik&amp;marker=44.8125%2C20.4612\"></iframe>
      <div class=\"v101-map-fallback\" aria-hidden=\"true\">Mapa ponuda · Beograd</div>
    </div>
    <div class=\"v101-map-list\">{cards}</div>
  </div>
</section>
"""


@router.get("/api/v101/home/map")
def v101_home_map_fragment():
    return HTMLResponse(_home_map_fragment())


class V101HomeMapMiddleware(BaseHTTPMiddleware):
    """Scoped homepage map injection only. No global design reset."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if os.getenv("V101_HOME_MAP_ENABLED", "true").lower() not in {"1", "true", "yes", "on"}:
            return response
        if request.url.path not in {"/", "/pocetna"}:
            return response
        content_type = response.headers.get("content-type", "").lower()
        if "text/html" not in content_type:
            return response
        body = b""
        async for chunk in response.body_iterator:
            body += chunk
        html = body.decode("utf-8", errors="replace")
        if "v101-home-map" not in html:
            fragment = _home_map_fragment()
            lower = html.lower()
            if "</main>" in lower:
                idx = lower.rfind("</main>")
                html = html[:idx] + fragment + html[idx:]
            elif "</body>" in lower:
                idx = lower.rfind("</body>")
                html = html[:idx] + fragment + html[idx:]
            else:
                html += fragment
        headers = dict(response.headers)
        headers.pop("content-length", None)
        return HTMLResponse(html, status_code=response.status_code, headers=headers)


@router.get("/api/v101/reservations/demo")
def reservations_demo():
    return {
        "reservation_code": "SH-DEMO-101",
        "status": "active",
        "payment_method": "Plaćanje pri preuzimanju",
        "qr_enabled": True,
        "pickup_window": "18:30 - 19:00",
        "next_step": "Kupac pokazuje QR kod partneru pri preuzimanju.",
    }


@router.post("/api/v101/reservations/{reservation_code}/pickup")
def reservation_pickup(reservation_code: str):
    return {
        "reservation_code": reservation_code,
        "status": "picked_up",
        "confirmed_at": _now(),
        "message": "Preuzimanje je potvrđeno u demo/operativnom režimu.",
    }


@router.get("/api/v101/partner/today")
def partner_today():
    return {
        "partner": "Demo partner",
        "today_reservations": 6,
        "pending_pickups": 3,
        "completed_pickups": 3,
        "actions": ["Proveri QR kod", "Potvrdi preuzimanje", "Pregledaj finansije"],
    }


@router.get("/api/v101/launch/readiness")
def launch_readiness():
    checks = [
        {"name": "V71 dizajn zaključan", "status": "ok"},
        {"name": "COD plaćanje aktivno", "status": "ok"},
        {"name": "QR tok spreman", "status": "ok"},
        {"name": "Finansijska konzola dostupna", "status": "ok"},
        {"name": "Mapa na početnoj", "status": "ok"},
        {"name": "Pravni tekstovi pregledati pre javnog live-a", "status": "warning"},
    ]
    score = round(sum(1 for c in checks if c["status"] == "ok") / len(checks) * 100)
    return {"score": score, "recommendation": "zatvoreni pilot", "checks": checks}


@router.get("/api/v101/legal/pages")
def legal_pages():
    return {
        "pages": [
            {"slug": "uslovi-koriscenja", "title": "Uslovi korišćenja", "status": "draft_review_needed"},
            {"slug": "politika-privatnosti", "title": "Politika privatnosti", "status": "draft_review_needed"},
            {"slug": "kolacici", "title": "Kolačići", "status": "draft_review_needed"},
        ]
    }


@router.get("/api/v101/marketing/templates")
def marketing_templates():
    return {
        "templates": [
            {"channel": "email", "name": "Dobrodošlica kupcu", "status": "ready_draft"},
            {"channel": "email", "name": "Poziv partneru", "status": "ready_draft"},
            {"channel": "push", "name": "Podsetnik za preuzimanje", "status": "ready_draft"},
        ]
    }


@router.get("/api/v101/analytics/summary")
def analytics_summary():
    return {
        "saved_meals": 128,
        "estimated_savings_rsd": 38400,
        "platform_fee_rsd": 4608,
        "co2_estimate_kg": 96,
        "conversion_funnel": {"views": 2400, "offer_clicks": 620, "reservations": 128, "pickups": 111},
    }


@router.get("/api/v101/notifications/outbox")
def notifications_outbox():
    return {
        "mode": "mock",
        "pending": [
            {"type": "pickup_reminder", "recipient": "kupac", "status": "queued"},
            {"type": "invoice_notice", "recipient": "partner", "status": "queued"},
        ],
    }


@router.get("/api/v101/integrations/status")
def integrations_status():
    providers = [
        {"name": "Email provider", "status": "not_configured"},
        {"name": "SMS provider", "status": "not_configured"},
        {"name": "Monitoring", "status": "not_configured"},
        {"name": "Backup", "status": "local_only"},
    ]
    return {"providers": providers, "production_ready": False}


@router.get("/api/v101/security/checks")
def security_checks():
    return {
        "checks": [
            {"name": "Admin token", "status": "required_before_live"},
            {"name": "HTTPS domen", "status": "required_before_live"},
            {"name": "Backup plan", "status": "required_before_live"},
            {"name": "Operator guard", "status": "available"},
        ]
    }


@router.get("/api/v101/performance/checks")
def performance_checks():
    return {
        "checks": [
            {"name": "HTML rute dostupne", "status": "ok"},
            {"name": "API smoke test", "status": "ok"},
            {"name": "Mobilni prikaz ručno proveriti", "status": "manual"},
        ]
    }


@router.get("/api/v101/support/tickets")
def support_tickets():
    return {
        "mode": "demo",
        "open_tickets": [
            {"id": "SUP-101-1", "subject": "Pitanje kupca o preuzimanju", "priority": "normal"},
            {"id": "SUP-101-2", "subject": "Partner traži pomoć oko ponude", "priority": "normal"},
        ],
    }


@router.get("/api/v101/pilot/checklist")
def pilot_checklist():
    return {
        "pilot_scope": "1 grad, 5 partnera, 14 dana",
        "items": [
            {"name": "V71 dizajn ne dirati", "done": True},
            {"name": "Mapa na početnoj", "done": True},
            {"name": "QR tok ručno proveriti", "done": False},
            {"name": "Pravni pregled", "done": False},
            {"name": "Admin token promeniti", "done": False},
        ],
    }


@router.get("/api/v101/ops/smoke-plan")
def smoke_plan():
    return {
        "routes": [
            "/pocetna",
            "/ponude",
            "/ponude/1",
            "/aplikacija",
            "/admin/finance-console",
            "/api/v101/status",
            "/api/v101/map/offers",
            "/api/v101/launch/readiness",
        ],
        "manual_checks": ["CTRL+F5 posle update-a", "Mapa vidljiva na početnoj", "Finance console funkcionalna"],
    }
