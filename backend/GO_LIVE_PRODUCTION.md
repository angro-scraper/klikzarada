# Sačuvaj Hranu — go-live kratki plan

## 1. Obavezno pre javnog linka
- Učitaj pilot podatke kroz `/pilot-live/setup`.
- Proveri da javne ponude imaju sliku, cenu, količinu i GPS lokaciju.
- Za prvi zatvoreni pilot koristi `PAYMENT_PROVIDER=pay_on_pickup`.
- Promeni `ADMIN_PIN` i `ADMIN_SESSION_SECRET`.
- Uključi `ADMIN_GUARD_ENABLED=true`.
- U produkciji koristi HTTPS, jer GPS i kamera rade pouzdano samo preko HTTPS-a.
- Za javni live koristi PostgreSQL, ne lokalni SQLite.

## 2. Preporučen live test
1. Otvori `/pilot-live/setup`.
2. Uključi GPS ili klikni na mapu.
3. Otvori `/ponude`.
4. Rezerviši proizvod.
5. Otvori `/reservation?code=...`.
6. Partner potvrđuje kod kroz `/partner/preuzimanje`.
7. Proveri `/pilot-live/daily-report`.
8. Proveri `/finance/summary` ili finansijsku konzolu.

## 3. Minimalni zatvoreni pilot
- 5–10 stvarnih prodavaca.
- 50–100 stvarnih ponuda sa slikom.
- 1 grad ili 2 zone u Beogradu.
- Ručna finansijska kontrola uplata preko `/finance`.
- Podrška preko `/support-admin`.

## 4. Šta ostaje za produkcioni nivo
- Pravi SMS provider.
- Pravi payment gateway webhook ili bankarski izvod import.
- Hosting sa domenom i HTTPS-om.
- Backup baze na eksterni storage.
- Pravna provera uslova, privatnosti i pravila za hranu.

Detaljan runbook: `docs/LIVE_DEPLOY_RUNBOOK_SR.md`.
