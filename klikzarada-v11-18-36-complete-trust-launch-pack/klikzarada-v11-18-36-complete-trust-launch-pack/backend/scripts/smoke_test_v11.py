from pathlib import Path
import sys

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import sys
try:
    from fastapi.testclient import TestClient
except RuntimeError as e:
    print('Nedostaje paket za smoke test. Pokreni: pip install httpx==0.28.1')
    raise


from app.main import app

ROUTES = [
    "/",
    "/login",
    "/registracija",
    "/api/v1/v11/health",
    "/api/v1/v11/smoke",
    "/lp/za-korisnike",
    "/legal/uslovi-koriscenja",
]

client = TestClient(app)
failed = []

for route in ROUTES:
    r = client.get(route, follow_redirects=False)
    ok = r.status_code in (200, 303, 307)
    print(f"{route}: {r.status_code} {'OK' if ok else 'FAIL'}")
    if not ok:
        failed.append((route, r.status_code))

if failed:
    print("FAILED:", failed)
    sys.exit(1)

print("V11 smoke test OK")
