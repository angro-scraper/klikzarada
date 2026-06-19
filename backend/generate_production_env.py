from __future__ import annotations

import argparse
from pathlib import Path
import secrets
import string
import sys


ROOT = Path(__file__).resolve().parent
DEFAULT_TEMPLATE = ROOT / ".env.production.example"
DEFAULT_OUTPUT = ROOT / ".env.production.generated"


def strong_pin(length: int = 12) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def normalize_domain(value: str | None) -> str | None:
    if not value:
        return None
    domain = value.strip().rstrip("/")
    if not domain:
        return None
    if not domain.startswith("https://"):
        domain = "https://" + domain.removeprefix("http://")
    return domain


def parse_env_lines(content: str) -> list[tuple[str | None, str]]:
    parsed: list[tuple[str | None, str]] = []
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in line:
            parsed.append((None, line))
            continue
        key, _ = line.split("=", 1)
        parsed.append((key.strip(), line))
    return parsed


def build_values(args: argparse.Namespace) -> dict[str, str]:
    domain = normalize_domain(args.domain)
    database_url = args.database_url.strip() if args.database_url else None
    allowed_origins = args.allowed_origins.strip() if args.allowed_origins else domain
    admin_pin = args.admin_pin.strip() if args.admin_pin else strong_pin()
    admin_secret = args.admin_secret.strip() if args.admin_secret else secrets.token_urlsafe(64)

    values = {
        "APP_ENV": "production",
        "PRODUCTION_MODE": "true",
        "ADMIN_GUARD_ENABLED": "true",
        "ADMIN_PIN": admin_pin,
        "ADMIN_SESSION_SECRET": admin_secret,
        "ADMIN_COOKIE_SECURE": "true",
        "PAYMENT_PROVIDER": args.payment_provider,
        "SMS_DRY_RUN": "true" if args.sms_dry_run else "false",
    }
    if domain:
        values["PUBLIC_BASE_URL"] = domain
    if allowed_origins:
        values["ALLOWED_ORIGINS"] = allowed_origins
    if database_url:
        values["DATABASE_URL"] = database_url
    return values


def render_env(template: Path, values: dict[str, str]) -> str:
    parsed = parse_env_lines(template.read_text(encoding="utf-8"))
    seen: set[str] = set()
    lines: list[str] = []
    for key, line in parsed:
        if key and key in values:
            lines.append(f"{key}={values[key]}")
            seen.add(key)
        else:
            lines.append(line)
    missing = [key for key in values if key not in seen]
    if missing:
        lines.append("")
        lines.append("# Automatski dodato")
        for key in missing:
            lines.append(f"{key}={values[key]}")
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generise produkcioni .env za Sacuvaj Hranu.")
    parser.add_argument("--template", default=str(DEFAULT_TEMPLATE), help="Putanja do .env.production.example fajla.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Gde se pise generisani env fajl.")
    parser.add_argument("--domain", help="Produkcioni HTTPS domen, npr. https://sacuvajhranu.rs.")
    parser.add_argument("--allowed-origins", help="CORS lista domena. Ako nije zadato, koristi --domain.")
    parser.add_argument("--database-url", help="Stvarni PostgreSQL DATABASE_URL.")
    parser.add_argument("--admin-pin", help="Rucno zadat admin PIN/lozinka. Ako nije zadato, generise se.")
    parser.add_argument("--admin-secret", help="Rucno zadat session secret. Ako nije zadato, generise se.")
    parser.add_argument("--payment-provider", default="pay_on_pickup", help="Payment provider za prvi live.")
    parser.add_argument("--sms-dry-run", action=argparse.BooleanOptionalAction, default=True, help="Da li SMS ostaje u dry-run modu.")
    parser.add_argument("--force", action="store_true", help="Dozvoli prepisivanje output fajla.")
    args = parser.parse_args()

    template = Path(args.template).resolve()
    output = Path(args.output).resolve()
    if not template.exists():
        print(f"Template ne postoji: {template}", file=sys.stderr)
        return 1
    if output.exists() and not args.force:
        print(f"Output vec postoji: {output}", file=sys.stderr)
        print("Dodaj --force ako zelis da ga prepises.", file=sys.stderr)
        return 1

    values = build_values(args)
    output.write_text(render_env(template, values), encoding="utf-8")

    print(f"Generisan produkcioni env: {output}")
    print(f"ADMIN_PIN={values['ADMIN_PIN']}")
    print("ADMIN_SESSION_SECRET je generisan i upisan u fajl.")
    if "PUBLIC_BASE_URL" not in values:
        print("Upozorenje: PUBLIC_BASE_URL je ostao placeholder. Dodaj --domain pre javnog live-a.")
    if "DATABASE_URL" not in values:
        print("Upozorenje: DATABASE_URL je ostao placeholder. Dodaj --database-url za javni live.")
    print("Sledece: prebaci vrednosti u hosting env dashboard, pa pokreni run_remote_smoke.py.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
