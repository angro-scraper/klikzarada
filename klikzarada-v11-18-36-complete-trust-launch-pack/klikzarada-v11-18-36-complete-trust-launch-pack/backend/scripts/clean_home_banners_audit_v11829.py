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
    "clean top ads": "kz-clean-top-ads" in html,
    "clean banner class": html.count("kz-clean-banner") >= 10,
    "clean sponsor grid": "kz-clean-sponsor-grid" in html,
    "clean bottom slots": "kz-clean-bottom-slots" in html,
    "no inline banner image vars": "--banner-img" not in html,
    "top fallback asset": "promo_top_shopping.svg" in html,
    "bottom fallback asset": "promo_bottom_finance.svg" in html,
}
for name, passed in checks.items():
    print(("OK" if passed else "FAIL"), name)
    ok = ok and passed

css = c.get("/static/css/style.css")
local = css.status_code == 200 and "V11.18.29 CLEAN HOME BANNERS" in css.text
print(("OK" if local else "FAIL"), "CSS_MARKER", css.status_code)
ok = ok and local

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
    local = rr.status_code == 200
    print(("OK" if local else "FAIL"), "ASSET", path, rr.status_code)
    ok = ok and local

print("RESULT:", "PASS" if ok else "CHECK_FAILED")
raise SystemExit(0 if ok else 1)
