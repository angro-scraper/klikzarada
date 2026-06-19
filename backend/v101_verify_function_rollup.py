# -*- coding: utf-8 -*-
from fastapi import FastAPI
from fastapi.testclient import TestClient
import app.main as main_module

app = getattr(main_module, "app", None)
if not isinstance(app, FastAPI):
    candidates = [v for v in vars(main_module).values() if isinstance(v, FastAPI)]
    if not candidates:
        raise SystemExit("Ne mogu da pronađem FastAPI aplikaciju")
    app = candidates[0]

client = TestClient(app)

required = [
    "/api/v101/status",
    "/api/v101/features",
    "/api/v101/home/map",
    "/api/v101/map/offers",
    "/api/v101/reservations/demo",
    "/api/v101/partner/today",
    "/api/v101/launch/readiness",
    "/api/v101/analytics/summary",
    "/api/v101/notifications/outbox",
    "/api/v101/integrations/status",
    "/api/v101/security/checks",
    "/api/v101/support/tickets",
    "/api/v101/pilot/checklist",
]

for path in required:
    r = client.get(path)
    print(path, r.status_code)
    if r.status_code != 200:
        print(r.text[:500])
        raise SystemExit(1)

home = client.get("/pocetna")
print("/pocetna", home.status_code)
if home.status_code == 200:
    has_v101_map = "v101-home-map" in home.text
    has_locked_design_live_map = "openstreetmap.org/export/embed.html" in home.text and "useLiveLocation" in home.text
    if not (has_v101_map or has_locked_design_live_map):
        raise SystemExit("Mapa nije dostupna na /pocetna")
else:
    print("Upozorenje: /pocetna nije dostupna, ali V101 API radi.")

print("V101 FUNCTION ROLLUP NO DESIGN PASSED")
