
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
paths = ['/pocetna','/ponude','/ponude/1','/moje-rezervacije','/profil','/partner/kontrolna-tabla','/dizajn-sistem']
for path in paths:
    r = client.get(path)
    print(path, r.status_code, r.headers.get('content-type'))
    if r.status_code != 200:
        print(r.text[:500])
        raise SystemExit(1)
    if 'Sačuvaj' not in r.text:
        raise SystemExit(f'Missing Serbian brand text in {path}')
print('V71 JAVNE STRANICE DIZAJN PASSED')
