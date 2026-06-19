from __future__ import annotations

import json
import sys

from fastapi.testclient import TestClient

import app.main as main_module


client = TestClient(main_module.app)


def get_json(path: str) -> dict:
    response = client.get(path)
    print(path, response.status_code)
    if response.status_code != 200:
        print(response.text[:1000])
        raise SystemExit(1)
    return response.json()


def main() -> int:
    health = get_json("/healthz")
    audit = get_json("/pilot-live/production-env-audit")
    go = get_json("/pilot-live/go-no-go")
    public_live = get_json("/pilot-live/public-live-check")

    summary = {
        "health_ok": health.get("ok"),
        "closed_pilot": go.get("decision"),
        "closed_pilot_score": go.get("closed_pilot_score"),
        "public_live": go.get("public_decision"),
        "public_live_score": go.get("public_live_score"),
        "production_env_score": audit.get("score"),
        "production_env_ok": audit.get("ok"),
        "public_live_ok": public_live.get("ok"),
        "blockers": [item.get("label") for item in audit.get("blockers", [])],
        "next_actions": audit.get("next_actions", []),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    if not health.get("ok"):
        print("PRODUCTION AUDIT FAILED: healthz nije OK")
        return 1
    if not go.get("ok"):
        print("PRODUCTION AUDIT FAILED: zatvoreni pilot nije GO")
        return 1
    if not audit.get("ok"):
        print("PRODUCTION AUDIT WARNING: env nije spreman za javni live")
        return 2

    print("PRODUCTION AUDIT PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
