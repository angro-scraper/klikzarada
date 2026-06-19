
from fastapi import FastAPI
from fastapi.testclient import TestClient
import app.main as main_module
fastapi_app=getattr(main_module,"app",None)
if not isinstance(fastapi_app, FastAPI):
    candidates=[v for v in vars(main_module).values() if isinstance(v,FastAPI)]
    if not candidates: raise SystemExit("Could not find FastAPI instance in app.main")
    fastapi_app=candidates[0]
client=TestClient(fastapi_app)
checks=[("/admin/finance-console",["Finansijska konzola","Računi","Ukupno fakturisano","Pokreni kompletan demo tok"]),("/seller/finance-console?seller_id=1",["Finansije partnera","Pregled"]),("/admin/finansije-izvestaji",["Finansijski izveštaji","Izveštaj partnera"])]
for path, words in checks:
    r=client.get(path); print(path, r.status_code)
    if r.status_code != 200:
        print(r.text[:1000]); raise SystemExit(1)
    for word in words:
        if word not in r.text: raise SystemExit(f"Missing Serbian UI word {word!r} in {path}")
api=client.get("/api/admin/finance/sr-dashboard"); print("/api/admin/finance/sr-dashboard", api.status_code)
if api.status_code != 200:
    print(api.text[:1000]); raise SystemExit(1)
print("V69 SERBIAN LOCALIZATION PASSED")
