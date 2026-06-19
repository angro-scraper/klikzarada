from fastapi.testclient import TestClient

import app.main as main_module


client = TestClient(main_module.app)

paths = [
    "/healthz",
    "/pilot-live/readiness",
    "/pilot-live/deploy-status",
    "/pilot-live/pwa-status",
    "/pilot-live/legal-status",
    "/pilot-live/partner-ops-status",
    "/pilot-live/customer-flow-status",
    "/pilot-live/finance-closeout-status",
    "/pilot-live/monitoring-status",
    "/pilot-live/launch-monitor-status",
    "/pilot-live/database-status",
    "/pilot-live/production-env-audit",
    "/pilot-live/go-no-go",
    "/pilot-live/live-readiness",
    "/pilot-live/public-live-check",
    "/pocetna",
    "/ponude",
    "/partner/onboarding",
    "/partner/live",
    "/moje-rezervacije",
    "/go-live",
]

for path in paths:
    response = client.get(path)
    print(path, response.status_code)
    if response.status_code != 200:
        print(response.text[:1000])
        raise SystemExit(1)

deploy = client.get("/pilot-live/deploy-status").json()
if not deploy.get("ok"):
    raise SystemExit("Deploy paket nije kompletan")

pwa = client.get("/pilot-live/pwa-status").json()
if not pwa.get("ok"):
    raise SystemExit("PWA nije kompletan")

print("LIVE VERIFY PASSED")
