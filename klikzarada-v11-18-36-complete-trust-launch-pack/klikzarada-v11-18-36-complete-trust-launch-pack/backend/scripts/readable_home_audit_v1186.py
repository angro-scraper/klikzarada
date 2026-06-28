from fastapi.testclient import TestClient
import app.main
c=TestClient(app.main.app)
need=["kz1186-page","kz1186-top-ads","kz1186-hero","kz1186-sponsors","kz1186-tasks","kz1186-bottom-ads","kz1186-footer","Naruči kampanju"]
r=c.get('/')
ok=r.status_code==200 and all(x in r.text for x in need)
print("HOME",r.status_code,"OK" if ok else "FAIL")
r2=c.get('/pocetna')
ok=ok and r2.status_code==200 and 'kz1186-page' in r2.text
print("POCETNA",r2.status_code,"OK" if 'kz1186-page' in r2.text else "FAIL")
print("RESULT:","PASS" if ok else "CHECK_FAILED")
raise SystemExit(0 if ok else 1)
