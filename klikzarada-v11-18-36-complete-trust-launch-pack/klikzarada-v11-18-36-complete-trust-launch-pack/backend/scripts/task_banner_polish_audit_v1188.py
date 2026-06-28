from fastapi.testclient import TestClient
import app.main

c=TestClient(app.main.app)
ok=True
for path, need in [
    ("/", ["kz1186-tasks", "kz1186-top-ads", "Popuni anketu", "Povećajte prodaju"]),
    ("/pocetna", ["kz1186-tasks", "kz1186-top-ads", "kz1186-bottom-ads"]),
]:
    r=c.get(path)
    local = r.status_code == 200 and all(x in r.text for x in need)
    print(("OK" if local else "FAIL"), path, r.status_code)
    ok = ok and local

r=c.get("/static/css/style.css?v=1188")
need_css=[
    "V11.18.8 TASK + BANNER POLISH",
    ".kz1186-tasks .task-card .meta span:last-child",
    ".kz1186-top-ads .top-ad",
    "grid-template-columns:repeat(5,minmax(0,1fr))"
]
local = r.status_code == 200 and all(x in r.text for x in need_css)
print(("OK" if local else "FAIL"), "/static/css/style.css", r.status_code)
ok = ok and local

print("RESULT:", "PASS" if ok else "CHECK_FAILED")
raise SystemExit(0 if ok else 1)
