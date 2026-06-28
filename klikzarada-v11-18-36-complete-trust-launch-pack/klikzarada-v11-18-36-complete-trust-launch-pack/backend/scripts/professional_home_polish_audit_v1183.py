from fastapi.testclient import TestClient
import app.main
c=TestClient(app.main.app)
need=["kz1183-page","kz1183-top-ads","PROMO PROSTOR","ISTAKNUTI OGLAS","kz1183-sponsors","kz1183-bottom-ads","kz1183-footer","SPONZORSKI BANNERI NA POČETNOJ","KAMPANJA NA PRVOM MESTU","Spremni da počnete?"]
r=c.get('/')
ok=r.status_code==200 and all(x in r.text for x in need)
print('OK /', r.status_code if ok else 'FAIL')
r2=c.get('/pocetna')
ok=ok and r2.status_code==200 and 'kz1183-page' in r2.text
print('OK /pocetna' if r2.status_code==200 else 'FAIL /pocetna')
print('RESULT:', 'PASS' if ok else 'CHECK_FAILED')
raise SystemExit(0 if ok else 1)
