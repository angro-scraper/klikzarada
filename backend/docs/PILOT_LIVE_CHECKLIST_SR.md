# Sačuvaj Hranu - zatvoreni pilot checklist

## Pre pilot dana
- Pokrenuti `/pilot-live/setup`.
- Pokrenuti `/pilot-live/backup`.
- Otvoriti `/go-live` i proveriti Go/No-Go odluku.
- Proveriti `/pilot-live/go-no-go`.
- Proveriti `/pilot-live/readiness`.
- Promeniti `ADMIN_PIN` i `ADMIN_SESSION_SECRET` u `.env`.
- Za pravi pilot uključiti `ADMIN_GUARD_ENABLED=true`.
- Otvoriti `/ponude` i napraviti probnu rezervaciju.
- Otvoriti QR kartu preko `/reservation?code=KOD`.
- Otvoriti `/moje-rezervacije` i proveriti istoriju po telefonu kupca.
- Proveriti `/reservations/customer?phone=TELEFON`.
- Testirati otkazivanje rezervacije iz kupac panela.
- Partner treba da potvrdi preuzimanje preko `/partner/preuzimanje`.
- Partner treba da koristi dnevni ekran `/partner/live?store_id=ID&pin=PIN`.
- Proveriti `/pilot-live/partner-ops-status`.
- Proveriti `/pilot-live/partner-ops?store_id=ID&pin=PIN`.
- Proveriti javne trust strane: `/podrska`, `/uslovi-koriscenja`, `/privatnost`, `/bezbednost-hrane`.
- Poslati probni support ticket preko `/podrska`.
- Proveriti `/pilot-live/daily-report`.
- Proveriti `/pilot-live/legal-status`.
- Proveriti `/pilot-live/customer-flow-status`.
- Proveriti `/pilot-live/finance-closeout-status`.
- Proveriti `/pilot-live/monitoring-status`.
- Proveriti `/pilot-live/production-env-audit`.
- Otvoriti `/finance` i proveriti dnevni finance closeout.
- Izvesti CSV preko `/finance/live-closeout.csv`.
- Finalno: `/go-live` mora pokazati GO za zatvoreni pilot.

## Model za prvi pilot
- Plaćanje pri preuzimanju.
- Kupac vidi svoje rezervacije po telefonu i otvara digitalnu kartu.
- Partner PIN za potvrdu preuzimanja.
- Partner live ekran za smenu, dodavanje ponude i pregled provizije.
- Provizija ide kao `commission_due`.
- Finance closeout označava kada je obračun provizije poslat partneru.
- Online kartice/IPS ostaju isključeni dok se ne izabere payment provider.
- Support prijave idu u `/support-admin`.

## Pre javnog live-a
- PostgreSQL baza.
- Domen i HTTPS.
- Secure admin cookie.
- Admin guard uključen.
- Remote backup.
- Pravni tekstovi provereni.
- Javni support i bezbednost hrane provereni.
- SMS/email provider podešen.
- `ALLOWED_ORIGINS` podešen na stvarni HTTPS domen.
- `run_production_audit.ps1 -Strict` prolazi bez upozorenja.
