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
    "final row exists": "kz-promo-final-row" in html,
    "final card exists": "kz-promo-final-card" in html,
    "campaign in final row": "kz-promo-final-campaign" in html,
    "shop asset": "promo_final_shop.svg" in html,
    "finance asset": "promo_final_finance.svg" in html,
    "travel asset": "promo_final_travel.svg" in html,
    "fit asset": "promo_final_fit.svg" in html,
    "campaign asset": "promo_final_campaign.svg" in html,
    "old sponsor row removed": "kz-clean-sponsor-row" not in html,
}
for name, passed in checks.items():
    print(("OK" if passed else "FAIL"), name)
    ok = ok and passed

for path in [
    "/static/img/promo_final_shop.svg",
    "/static/img/promo_final_finance.svg",
    "/static/img/promo_final_travel.svg",
    "/static/img/promo_final_fit.svg",
    "/static/img/promo_final_campaign.svg",
]:
    rr = c.get(path)
    local = rr.status_code == 200 and "<svg" in rr.text[:120]
    print(("OK" if local else "FAIL"), "ASSET", path, rr.status_code)
    ok = ok and local

css = c.get("/static/css/style.css")
local = css.status_code == 200 and "V11.18.30 FINAL PROMO ROW" in css.text
print(("OK" if local else "FAIL"), "CSS_MARKER", css.status_code)
ok = ok and local

print("RESULT:", "PASS" if ok else "CHECK_FAILED")
raise SystemExit(0 if ok else 1)
