# Sačuvaj Hranu - backend deploy na Render

Ovo je rezervni i preporučeni put ako AdriaHost Basic paket nema Python Application Manager / Passenger / terminal za FastAPI.

## Šta ostaje na AdriaHost-u
- domen `sacuvaj-hranu.rs`
- SSL i email
- privremeni `public_html` landing dok backend ne bude spreman

## Šta ide na Render
- FastAPI aplikacija
- produkciona baza preko `DATABASE_URL`
- admin zaštita i live monitoring

## Deploy koraci
1. Napravi novi Render Web Service iz repozitorijuma.
2. Izaberi Docker deploy.
3. Root direktorijum treba da bude `backend`.
4. Dockerfile koristi `requirements-production.txt`, bez Playwright browser paketa, da prvi live deploy bude brži.
5. Health check path:

```text
/healthz
```

6. Obavezne env vrednosti:

```text
APP_ENV=production
PRODUCTION_MODE=true
PUBLIC_BASE_URL=https://sacuvaj-hranu.rs
ALLOWED_ORIGINS=https://sacuvaj-hranu.rs,https://www.sacuvaj-hranu.rs
ADMIN_GUARD_ENABLED=true
ADMIN_COOKIE_SECURE=true
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/DBNAME
ADMIN_PIN=novi-jaki-pin
ADMIN_SESSION_SECRET=duga-jaka-tajna
PAYMENT_PROVIDER=pay_on_pickup
SMS_DRY_RUN=true
```

7. Pre prvog javnog puštanja pokreni lokalno:

```powershell
.\run_live_verify.ps1
.\check_mysql_schema.ps1
.\build_live_release.ps1
.\check_live_release.ps1
.\check_public_html_package.ps1
.\check_external_backend_ready.ps1
```

8. Kada Render URL proradi, proveri:

```powershell
.\run_remote_smoke.ps1 -BaseUrl https://RENDER-URL
```

9. Tek kada je stabilno, poveži domen:
- ili CNAME `www` ka Render hostu,
- ili Render custom domain instrukcije za apex domen,
- ili ostavi AdriaHost kao statički landing i koristi poddomen `app.sacuvaj-hranu.rs` za aplikaciju.

## Najbezbednija varijanta za početak
Prvo pusti `https://sacuvaj-hranu.rs` kao statički landing na AdriaHost-u, a aplikaciju testiraj na Render URL-u. Kada prođu partneri, rezervacije, admin i finansije, domen se prebaci na aplikaciju.
