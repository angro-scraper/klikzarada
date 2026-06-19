
import os
os.environ['ADMIN_GUARD_ENABLED'] = 'false'

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

paths = [
    '/api/admin/finance/dashboard-data',
    '/api/admin/finance/reports/aging',
    '/api/admin/finance/reports/monthly-summary',
    '/api/admin/finance/monthly-close/preview',
    '/api/admin/finance/reconciliation/check',
    '/api/admin/finance/export/invoices.csv',
    '/api/admin/finance/export/ledger.csv',
    '/api/admin/finance/export/payments.csv',
    '/admin/finance-reports-console',
]

for path in paths:
    r = client.get(path)
    print(path, r.status_code, r.headers.get('content-type'))
    if r.status_code != 200:
        print(r.text)
        raise SystemExit(1)

print('V68 FINANCE REPORTS COMMAND CENTER PASSED')
