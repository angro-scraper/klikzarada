from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent

REQUIRED_FILES = [
    "Dockerfile",
    "render.yaml",
    "requirements-production.txt",
    "app/main.py",
    "app/database.py",
    "docs/RENDER_BACKEND_DEPLOY_SR.md",
    "run_remote_smoke.ps1",
    "run_live_verify.ps1",
]

REQUIRED_RENDER_ENV = [
    "APP_ENV",
    "PRODUCTION_MODE",
    "PUBLIC_BASE_URL",
    "ALLOWED_ORIGINS",
    "ADMIN_GUARD_ENABLED",
    "ADMIN_COOKIE_SECURE",
    "DATABASE_URL",
    "ADMIN_PIN",
    "ADMIN_SESSION_SECRET",
]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def main() -> int:
    files = [{"path": item, "exists": (ROOT / item).exists()} for item in REQUIRED_FILES]
    dockerfile = read_text(ROOT / "Dockerfile")
    render = read_text(ROOT / "render.yaml")
    requirements = read_text(ROOT / "requirements-production.txt")

    checks = {
        "docker_uses_production_requirements": "requirements-production.txt" in dockerfile,
        "docker_uses_dynamic_port": "${PORT:-8000}" in dockerfile,
        "render_has_healthcheck": "healthCheckPath: /healthz" in render,
        "render_uses_docker": "env: docker" in render,
        "production_requirements_excludes_playwright": "playwright" not in requirements.lower(),
        "production_requirements_has_postgres": "psycopg" in requirements,
        "production_requirements_has_mysql": "pymysql" in requirements,
    }
    render_env = {
        key: (f"key: {key}" in render)
        for key in REQUIRED_RENDER_ENV
    }
    ok = all(item["exists"] for item in files) and all(checks.values()) and all(render_env.values())
    report = {
        "ok": ok,
        "files": files,
        "checks": checks,
        "render_env": render_env,
        "next_step": "Deploy backend na Render/Railway/VPS, pa pokreni run_remote_smoke.ps1 nad dobijenim URL-om.",
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
