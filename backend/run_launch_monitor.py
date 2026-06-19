from __future__ import annotations

import argparse
from datetime import datetime, timezone
from http.cookiejar import CookieJar
import json
from pathlib import Path
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import HTTPCookieProcessor, Request, build_opener


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
REPORT_PATH = DATA_DIR / "launch_monitor_latest.json"
HISTORY_PATH = DATA_DIR / "launch_monitor_history.json"


class MonitorClient:
    def __init__(self, base_url: str, timeout: int):
        self.base_url = base_url.rstrip("/") + "/"
        self.timeout = timeout
        self.opener = build_opener(HTTPCookieProcessor(CookieJar()))

    def get(self, path: str) -> dict:
        started = time.perf_counter()
        req = Request(urljoin(self.base_url, path.lstrip("/")), headers={"User-Agent": "sacuvaj-hranu-launch-monitor/1.0"})
        try:
            with self.opener.open(req, timeout=self.timeout) as response:
                text = response.read().decode("utf-8", errors="replace")
                return {"ok": 200 <= response.status < 400, "status": response.status, "ms": round((time.perf_counter() - started) * 1000), "bytes": len(text), "json": try_json(text), "error": None}
        except HTTPError as exc:
            text = exc.read().decode("utf-8", errors="replace")
            return {"ok": False, "status": exc.code, "ms": round((time.perf_counter() - started) * 1000), "bytes": len(text), "json": try_json(text), "error": text[:300]}
        except URLError as exc:
            return {"ok": False, "status": 0, "ms": round((time.perf_counter() - started) * 1000), "bytes": 0, "json": None, "error": str(exc.reason)}


def try_json(text: str):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def write_report(report: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    history = []
    if HISTORY_PATH.exists():
        try:
            loaded = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
            if isinstance(loaded, list):
                history = loaded
        except Exception:
            history = []
    history.append(report)
    HISTORY_PATH.write_text(json.dumps(history[-500:], ensure_ascii=False, indent=2), encoding="utf-8")


def json_check(client: MonitorClient, key: str, path: str) -> dict:
    result = client.get(path)
    data = result.get("json")
    ok = result["ok"] and isinstance(data, dict)
    details = {"http": result["status"], "ms": result["ms"], "bytes": result["bytes"]}
    if isinstance(data, dict):
        for field in ("ok", "decision", "public_decision", "score", "closed_pilot_score", "public_live_score"):
            if field in data:
                details[field] = data[field]
        if path.endswith("/monitoring-status"):
            details.update(data.get("signals", {}))
    if result["error"]:
        details["error"] = result["error"]
    return {"key": key, "path": path, "ok": ok, "details": details}


def html_check(client: MonitorClient, key: str, path: str) -> dict:
    result = client.get(path)
    details = {"http": result["status"], "ms": result["ms"], "bytes": result["bytes"]}
    if result["error"]:
        details["error"] = result["error"]
    return {"key": key, "path": path, "ok": result["ok"] and result["bytes"] > 500, "details": details}


def main() -> int:
    parser = argparse.ArgumentParser(description="Launch-day monitor za Sacuvaj Hranu.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--timeout", type=int, default=15)
    parser.add_argument("--strict-public-live", action="store_true")
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args()

    client = MonitorClient(args.base_url, args.timeout)
    checks = [
        json_check(client, "healthz", "/healthz"),
        json_check(client, "go_no_go", "/pilot-live/go-no-go"),
        json_check(client, "monitoring_status", "/pilot-live/monitoring-status"),
        json_check(client, "database_status", "/pilot-live/database-status"),
        json_check(client, "finance_closeout_status", "/pilot-live/finance-closeout-status"),
        json_check(client, "public_live_check", "/pilot-live/public-live-check"),
        json_check(client, "production_env_audit", "/pilot-live/production-env-audit"),
        html_check(client, "home", "/pocetna"),
        html_check(client, "offers", "/ponude"),
        html_check(client, "customer_reservations", "/moje-rezervacije"),
        html_check(client, "partner_live", "/partner/live"),
        html_check(client, "support_page", "/podrska"),
    ]
    if args.strict_public_live:
        for item in checks:
            if item["key"] in {"production_env_audit", "public_live_check"}:
                item["ok"] = item["ok"] and item["details"].get("ok") is True

    warning_keys = {"production_env_audit", "public_live_check"}
    failed = [item for item in checks if not item["ok"]]
    hard_failed = [item for item in failed if args.strict_public_live or item["key"] not in warning_keys]
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "base_url": args.base_url,
        "ok": not hard_failed,
        "score": round(sum(1 for item in checks if item["ok"]) / max(1, len(checks)) * 100),
        "checks": checks,
        "failed": failed,
        "hard_failed": hard_failed,
        "next_actions": [item["path"] for item in hard_failed] or ["Nema tvrdih blokera u monitoringu."],
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not args.no_write:
        write_report(report)
        print(f"Launch monitor report: {REPORT_PATH}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
