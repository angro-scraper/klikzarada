import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.main import app


def main() -> None:
    with TestClient(app) as client:
        client.cookies.set("kz_session", "audit-session", domain="testserver.local", path="/")
        response = client.post("/api/ui/auth/logout")
        assert response.status_code == 204, response.status_code
        assert response.content == b""
        assert "Max-Age=0" in response.headers.get("set-cookie", "")
        assert "kz_session" not in client.cookies
        print("OK: odjava vraca 204 i uklanja sesijski kolacic")


if __name__ == "__main__":
    main()
