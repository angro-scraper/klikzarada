from fastapi.testclient import TestClient
import app.main

def login(c,email,password):
    return c.post("/login", data={"email":email,"password":password}, follow_redirects=False).status_code in (302,303)

c=TestClient(app.main.app)
assert login(c,"admin@klikzarada.rs","Admin123!"), "Admin login failed"
for path in ["/admin/reklame-v111","/admin/kampanje","/admin/analitika-v117"]:
    r=c.get(path)
    assert r.status_code==200, f"{path} -> {r.status_code}"
    assert "premium-admin-hub" in r.text, f"missing admin hub in {path}"
    assert "premium-command-bar" not in r.text, f"old command bar found in {path}"
print("RESULT: PASS")
