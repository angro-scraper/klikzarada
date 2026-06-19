from __future__ import annotations

import argparse
import json
import socket
import ssl
import sys
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


def normalize_base_url(value: str) -> str:
    cleaned = value.strip().rstrip("/")
    if not cleaned:
        raise ValueError("Domen/base URL je prazan.")
    if not cleaned.startswith(("http://", "https://")):
        cleaned = "https://" + cleaned
    return cleaned


def hostname_from_url(base_url: str) -> str:
    parsed = urlparse(base_url)
    if not parsed.hostname:
        raise ValueError(f"Ne mogu da procitam hostname iz: {base_url}")
    return parsed.hostname


def check_dns(hostname: str) -> dict:
    try:
        rows = socket.getaddrinfo(hostname, 443, type=socket.SOCK_STREAM)
        addresses = sorted({row[4][0] for row in rows})
        return {"ok": bool(addresses), "addresses": addresses, "error": None}
    except socket.gaierror as exc:
        return {"ok": False, "addresses": [], "error": str(exc)}


def check_tls(hostname: str, timeout: int) -> dict:
    context = ssl.create_default_context()
    try:
        with socket.create_connection((hostname, 443), timeout=timeout) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as wrapped:
                cert = wrapped.getpeercert()
        not_after = cert.get("notAfter")
        return {"ok": True, "issuer": cert.get("issuer"), "not_after": not_after, "error": None}
    except Exception as exc:
        return {"ok": False, "issuer": None, "not_after": None, "error": str(exc)}


def fetch_json_or_text(url: str, timeout: int) -> dict:
    req = Request(url, headers={"User-Agent": "sacuvaj-hranu-domain-check/1.0"})
    try:
        with urlopen(req, timeout=timeout) as response:
            text = response.read().decode("utf-8", errors="replace")
            data = None
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                pass
            return {"ok": 200 <= response.status < 400, "status": response.status, "bytes": len(text), "json": data, "error": None}
    except HTTPError as exc:
        text = exc.read().decode("utf-8", errors="replace")
        return {"ok": False, "status": exc.code, "bytes": len(text), "json": None, "error": text[:300]}
    except URLError as exc:
        return {"ok": False, "status": 0, "bytes": 0, "json": None, "error": str(exc.reason)}


def print_check(label: str, ok: bool, detail: str) -> None:
    status = "OK" if ok else "FAIL"
    print(f"[{status}] {label}: {detail}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Provera da li je domen spreman za Sacuvaj Hranu live.")
    parser.add_argument("domain", help="Domen ili base URL, npr. sacuvajhranu.rs ili https://sacuvajhranu.rs")
    parser.add_argument("--expected-ip", help="IP adresa na koju domen treba da pokazuje.")
    parser.add_argument("--timeout", type=int, default=15)
    parser.add_argument("--strict", action="store_true", help="Zahteva da production env audit na domenu bude OK.")
    args = parser.parse_args()

    base_url = normalize_base_url(args.domain)
    hostname = hostname_from_url(base_url)
    result = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "base_url": base_url,
        "hostname": hostname,
        "checks": {},
    }

    dns = check_dns(hostname)
    if args.expected_ip:
        dns["expected_ip"] = args.expected_ip
        dns["matches_expected_ip"] = args.expected_ip in dns["addresses"]
    result["checks"]["dns"] = dns
    dns_ok = dns["ok"] and (not args.expected_ip or dns["matches_expected_ip"])
    dns_detail = ", ".join(dns["addresses"]) if dns["addresses"] else dns["error"] or "nema adresa"
    if args.expected_ip:
        dns_detail += f", expected={args.expected_ip}"
    print_check("DNS", dns_ok, dns_detail)

    tls = check_tls(hostname, args.timeout)
    result["checks"]["tls"] = tls
    print_check("HTTPS sertifikat", tls["ok"], tls["not_after"] or tls["error"] or "nema detalja")

    paths = {
        "healthz": "/healthz",
        "home": "/pocetna",
        "offers": "/ponude",
        "audit": "/pilot-live/production-env-audit",
        "go_no_go": "/pilot-live/go-no-go",
    }
    for key, path in paths.items():
        url = base_url + path
        check = fetch_json_or_text(url, args.timeout)
        result["checks"][key] = check
        detail = f"HTTP {check['status']}, bytes={check['bytes']}"
        data = check.get("json")
        if isinstance(data, dict):
            if "ok" in data:
                detail += f", ok={data.get('ok')}"
            if "decision" in data:
                detail += f", decision={data.get('decision')}"
            if "public_decision" in data:
                detail += f", public={data.get('public_decision')}"
            if "score" in data:
                detail += f", score={data.get('score')}"
        elif check["error"]:
            detail += f", error={check['error']}"
        print_check(path, check["ok"], detail)

    required = ["dns", "tls", "healthz", "home", "offers", "go_no_go"]
    failed = [key for key in required if not result["checks"].get(key, {}).get("ok")]
    if args.expected_ip and not dns.get("matches_expected_ip"):
        failed.append("dns_expected_ip")
    audit_json = result["checks"].get("audit", {}).get("json")
    if args.strict and (not isinstance(audit_json, dict) or not audit_json.get("ok")):
        failed.append("production_env_audit")

    print(json.dumps(result, ensure_ascii=False, indent=2))
    if failed:
        print("DOMAIN READY FAILED: " + ", ".join(failed))
        return 1
    print("DOMAIN READY PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
