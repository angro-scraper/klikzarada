
from fastapi import FastAPI
from fastapi.testclient import TestClient
import app.main as main_module

fastapi_app = getattr(main_module, "app", None)
if not isinstance(fastapi_app, FastAPI):
    candidates = [v for v in vars(main_module).values() if isinstance(v, FastAPI)]
    if not candidates:
        raise SystemExit("Ne mogu da pronađem FastAPI instancu u app.main")
    fastapi_app = candidates[0]

client = TestClient(fastapi_app)
for path, expected in [
    ("/admin/finance-console", "Finansijska konzola"),
    ("/seller/finance-console?seller_id=1", "Finansije prodavca"),
    ("/admin/finansije-izvestaji", "Finansijski izveštaji"),
]:
    r = client.get(path)
    print(path, r.status_code)
    if r.status_code != 200:
        print(r.text)
        raise SystemExit(1)
    if expected not in r.text:
        print("Nedostaje tekst:", expected)
        raise SystemExit(1)
print("V70 DIZAJN SISTEM PASSED")
