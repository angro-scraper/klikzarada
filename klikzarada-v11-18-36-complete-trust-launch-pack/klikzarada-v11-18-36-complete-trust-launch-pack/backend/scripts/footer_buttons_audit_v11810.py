
from fastapi.testclient import TestClient
from bs4 import BeautifulSoup
import app.main
app.main.startup()
c=TestClient(app.main.app)
need=['/','/blog','/cenovnik','/faq','/kontakt','/login','/pravila','/registracija','/za-korisnike','/za-oglasivace','/zadaci','/podrska','/politika-privatnosti','/uslovi-isplate']
ok=True
for p in need:
    r=c.get(p, follow_redirects=False)
    good = r.status_code in (200,301,302,303,307,308)
    print(('OK' if good else 'FAIL'), p, r.status_code, r.headers.get('location'))
    ok = ok and good
r=c.get('/')
soup=BeautifulSoup(r.text,'html.parser')
hrefs=sorted(set(a.get('href') for a in soup.find_all('a', href=True)))
for href in hrefs:
    rr=c.get(href, follow_redirects=False)
    good=rr.status_code in (200,301,302,303,307,308)
    print(('OK' if good else 'FAIL'),'HOME_LINK',href,rr.status_code,rr.headers.get('location'))
    ok = ok and good
css=c.get('/static/css/style.css?v=11810')
good = css.status_code==200 and 'V11.18.10 footer + buttons + ad slots polish' in css.text and '.kz1189-ad-slots a{min-height:92px' in css.text
print(('OK' if good else 'FAIL'),'CSS',css.status_code)
ok=ok and good
print('RESULT:', 'PASS' if ok else 'CHECK_FAILED')
raise SystemExit(0 if ok else 1)
