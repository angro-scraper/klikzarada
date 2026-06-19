
from fastapi import FastAPI
from fastapi.testclient import TestClient
import app.main as main_module

fastapi_app = getattr(main_module, 'app', None)
if not isinstance(fastapi_app, FastAPI):
    candidates = [v for v in vars(main_module).values() if isinstance(v, FastAPI)]
    if not candidates:
        raise SystemExit('Could not find FastAPI instance in app.main')
    fastapi_app = candidates[0]

client = TestClient(fastapi_app)
checks = [
    ('/admin/finance-console', 'V67 Finance Console Pro'),
    ('/seller/finance-console?seller_id=1', 'Seller Finance Console'),
    ('/admin/finance-console/invoice/1/print', 'Print / Save PDF'),
]
for path, marker in checks:
    r = client.get(path)
    print(path, r.status_code, r.headers.get('content-type'))
    if r.status_code != 200 or marker not in r.text:
        print(r.text[:1000])
        raise SystemExit(1)
print('V67 FINANCE CONSOLE PRO PASSED')
