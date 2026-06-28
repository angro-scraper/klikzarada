from fastapi.testclient import TestClient
import app.main

app.main.startup()
c = TestClient(app.main.app)
ok = True

r = c.get("/")
local = r.status_code == 200
print(("OK" if local else "FAIL"), "HOME", r.status_code)
ok = ok and local

html = r.text
checks = {
    "top fallback shopping visual": "promo_top_shopping.svg" in html,
    "top fallback business visual": "promo_top_business.svg" in html,
    "sponsor visual class": "kz-perfect-sponsor" in html,
    "campaign visual class": "kz-perfect-campaign" in html,
    "bottom visual class": "kz-perfect-bottom" in html,
    "no fallback bottom thumb visible in fallback block": "bottom-banner-thumb" not in html or "kz-perfect-bottom" in html,
    "CTA strip exists": "Spremni da počnete" in html,
}
for name, passed in checks.items():
    print(("OK" if passed else "FAIL"), name)
    ok = ok and passed

for path in [
    "/static/img/promo_top_shopping.svg",
    "/static/img/promo_top_business.svg",
    "/static/img/promo_shop.svg",
    "/static/img/promo_finance.svg",
    "/static/img/promo_travel.svg",
    "/static/img/promo_fitness.svg",
    "/static/img/promo_campaign_trophy.svg",
    "/static/img/promo_bottom_finance.svg",
    "/static/img/promo_bottom_tech.svg",
    "/static/img/promo_bottom_fun.svg",
]:
    rr = c.get(path)
    local = rr.status_code == 200 and "<svg" in rr.text[:100]
    print(("OK" if local else "FAIL"), "ASSET", path, rr.status_code)
    ok = ok and local

css = c.get("/static/css/style.css")
local = css.status_code == 200 and "V11.18.27 HOMEPAGE BANNERS PERFECT" in css.text
print(("OK" if local else "FAIL"), "CSS_MARKER", css.status_code)
ok = ok and local

print("RESULT:", "PASS" if ok else "CHECK_FAILED")
raise SystemExit(0 if ok else 1)
