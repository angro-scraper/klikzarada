from __future__ import annotations

import argparse
from http.cookiejar import CookieJar
import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import HTTPCookieProcessor, Request, build_opener


class SmokeClient:
    def __init__(self, base_url: str, timeout: int = 15):
        self.base_url = base_url.rstrip("/") + "/"
        self.timeout = timeout
        self.opener = build_opener(HTTPCookieProcessor(CookieJar()))

    def request(self, method: str, path: str, payload: dict | None = None) -> tuple[int, str, object | None]:
        data = None
        headers = {"User-Agent": "sacuvaj-hranu-remote-smoke/1.0"}
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = Request(urljoin(self.base_url, path.lstrip("/")), data=data, headers=headers, method=method)
        try:
            with self.opener.open(req, timeout=self.timeout) as response:
                text = response.read().decode("utf-8", errors="replace")
                return response.status, text, try_json(text)
        except HTTPError as exc:
            text = exc.read().decode("utf-8", errors="replace")
            return exc.code, text, try_json(text)
        except URLError as exc:
            return 0, str(exc.reason), None


def try_json(text: str) -> object | None:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def row(label: str, ok: bool, detail: str) -> dict:
    status = "OK" if ok else "FAIL"
    print(f"[{status}] {label}: {detail}")
    return {"label": label, "ok": ok, "detail": detail}


def main() -> int:
    parser = argparse.ArgumentParser(description="Remote smoke test za Sacuvaj Hranu domen posle deploy-a.")
    parser.add_argument("--base-url", default=os.getenv("PUBLIC_BASE_URL"), help="Base URL, npr. https://sacuvajhranu.rs")
    parser.add_argument("--admin-pin", default=os.getenv("ADMIN_PIN"), help="Admin PIN za proveru zasticenih ekrana.")
    parser.add_argument("--strict", action="store_true", help="Padni ako javni production audit nije potpuno OK.")
    parser.add_argument("--timeout", type=int, default=15)
    args = parser.parse_args()

    if not args.base_url:
        print("Nedostaje --base-url ili PUBLIC_BASE_URL.", file=sys.stderr)
        return 1

    client = SmokeClient(args.base_url, timeout=args.timeout)
    checks: list[dict] = []

    json_paths = [
        ("/healthz", "Health check"),
        ("/pilot-live/public-live-check", "Public live check"),
        ("/pilot-live/production-env-audit", "Production env audit"),
        ("/pilot-live/go-no-go", "Go/No-Go"),
    ]
    for path, label in json_paths:
        status, text, data = client.request("GET", path)
        ok = status == 200 and isinstance(data, dict)
        detail = f"HTTP {status}"
        if isinstance(data, dict):
            if "ok" in data:
                detail += f", ok={data.get('ok')}"
            if "decision" in data:
                detail += f", decision={data.get('decision')}"
            if "public_decision" in data:
                detail += f", public={data.get('public_decision')}"
            if "score" in data:
                detail += f", score={data.get('score')}"
        else:
            detail += f", body={text[:120]}"
        checks.append(row(label, ok, detail))

    html_paths = [
        ("/pocetna", "Pocetna"),
        ("/ponude", "Ponude"),
        ("/podrska", "Podrska"),
        ("/privatnost", "Privatnost"),
    ]
    for path, label in html_paths:
        status, text, _ = client.request("GET", path)
        ok = status == 200 and ("Sacuvaj" in text or "Sačuvaj" in text or "<html" in text.lower())
        checks.append(row(label, ok, f"HTTP {status}, bytes={len(text)}"))

    if args.admin_pin:
        status, text, data = client.request("POST", "/auth/admin/login", {"pin": args.admin_pin})
        login_ok = status == 200 and isinstance(data, dict) and data.get("ok") is True
        checks.append(row("Admin login", login_ok, f"HTTP {status}"))
        for path, label in [("/go-live", "Go-live dashboard"), ("/finance", "Finance admin"), ("/support-admin", "Support admin")]:
            status, text, _ = client.request("GET", path)
            ok = status == 200 and len(text) > 200
            checks.append(row(label, ok, f"HTTP {status}, bytes={len(text)}"))
    else:
        print("[SKIP] Admin zasticeni ekrani: dodaj --admin-pin za proveru.")

    audit = next((item for item in checks if item["label"] == "Production env audit"), None)
    hard_failed = [item for item in checks if not item["ok"]]
    if hard_failed:
        print("REMOTE SMOKE FAILED")
        return 1

    if args.strict:
        _, _, audit_data = client.request("GET", "/pilot-live/production-env-audit")
        if not isinstance(audit_data, dict) or not audit_data.get("ok"):
            print("REMOTE SMOKE STRICT FAILED: production env audit nije OK.")
            return 2

    print("REMOTE SMOKE PASSED")
    if audit:
        print("Napomena: za javni live koristi --strict da audit bude obavezan uslov.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
