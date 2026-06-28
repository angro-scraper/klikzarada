from fastapi.testclient import TestClient
import app.main
c=TestClient(app.main.app)
r=c.get('/')
need=["/static/img/shopmax.svg","/static/img/mega-promo.svg","kz1183-bottom-ads","kz1183-footer","campaign-top.svg"]
ok=r.status_code==200 and all(x in r.text for x in need)
print('HOME',r.status_code,'OK' if ok else 'FAIL')
# static files
for path in ['/static/img/shopmax.svg','/static/img/finance-pro.svg','/static/img/travel-world.svg','/static/img/fit-life.svg','/static/img/campaign-top.svg']:
    rr=c.get(path)
    print(path, rr.status_code)
    ok = ok and rr.status_code==200 and '<svg' in rr.text
print('RESULT:', 'PASS' if ok else 'CHECK_FAILED')
raise SystemExit(0 if ok else 1)
