from fastapi.testclient import TestClient
import app.main

def check(c,path,must=None):
    r=c.get(path)
    text=r.text
    ok=r.status_code==200
    if must:
        ok=ok and all(x in text for x in must)
    print(("OK" if ok else "FAIL"), path, r.status_code)
    if not ok:
        print(text[:400].replace("\n"," "))
    return ok

res=True
c=TestClient(app.main.app)
res=check(c,"/",[
    "kz1182-page",
    "kz1182-top-ads",
    "POVEĆAJTE PRODAJU",
    "VAŠ BIZNIS",
    "Zarada za korisnike",
    "kz1182-sponsors",
    "KAMPANJA NA PRVOM MESTU",
    "kz1182-tasks",
    "kz1182-stats",
    "kz1182-bottom-ads",
    "kz1182-footer"
]) and res
res=check(c,"/pocetna",["kz1182-page","kz1182-top-ads","kz1182-bottom-ads"]) and res
print("RESULT:", "PASS" if res else "CHECK_FAILED")
raise SystemExit(0 if res else 1)
