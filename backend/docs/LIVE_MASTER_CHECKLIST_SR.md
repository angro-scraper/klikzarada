# Sačuvaj Hranu - master checklist za live

## Zatvoreni pilot može kada
- `/go-live` prikazuje `GO za zatvoreni pilot`.
- `/pilot-live/go-no-go` nema blokatore za zatvoreni pilot.
- `/pilot-live/backup` je pokrenut pre test dana.
- Kupac tok radi: `/ponude`, rezervacija, `/reservation?code=KOD`, `/moje-rezervacije`.
- Partner tok radi: `/partner/live?store_id=ID&pin=PIN`, potvrda preuzimanja, dodavanje ponude.
- Support radi: `/podrska` kreira ticket, `/support-admin` ga prikazuje.
- Finance radi: `/finance/live-closeout` i `/finance/live-closeout.csv`.

## Javni live može tek kada
- Domen je dodat na hosting i DNS pokazuje na aplikaciju.
- HTTPS sertifikat je aktivan za domen.
- `/pilot-live/production-env-audit` ima `ok: true`.
- `DATABASE_URL` je stvarni PostgreSQL ili MySQL/MariaDB.
- `.\prepare_production_db.ps1 ... -Create -RequireProductionDb` prolazi bez greške.
- `/pilot-live/database-status` prikazuje kompletnu šemu baze.
- `PUBLIC_BASE_URL` je stvarni HTTPS domen.
- `ALLOWED_ORIGINS` sadrži samo stvarni HTTPS domen.
- `ADMIN_GUARD_ENABLED=true`.
- `ADMIN_PIN` nije podrazumevan i ima najmanje 8 karaktera.
- `ADMIN_SESSION_SECRET` je jak random secret od 48+ karaktera.
- `ADMIN_COOKIE_SECURE=true`.
- Pravni tekstovi su provereni.
- Remote backup je aktivan.

## Komande pre deploy-a
```powershell
.\.venv\Scripts\python.exe run_live_verify.py
.\generate_production_env.ps1 -Domain https://tvoj-domen.rs -DatabaseUrl "mysql+pymysql://USER:PASSWORD@HOST:3306/DBNAME?charset=utf8mb4" -Force
.\check_mysql_schema.ps1
.\prepare_production_db.ps1 -DatabaseUrl "mysql+pymysql://USER:PASSWORD@HOST:3306/DBNAME?charset=utf8mb4" -Create -RequireProductionDb
.\run_launch_monitor.ps1 -BaseUrl http://127.0.0.1:8000
.\build_live_release.ps1
.\check_live_release.ps1
.\check_public_html_package.ps1
.\print_live_upload_plan.ps1
.\check_external_backend_ready.ps1
.\run_production_audit.ps1
.\run_production_audit.ps1 -Strict
```

## Komande posle deploy-a
```powershell
.\check_domain_ready.ps1 -Domain https://tvoj-domen.rs -ExpectedIp 37.48.77.143 -Strict
.\run_remote_smoke.ps1 -BaseUrl https://tvoj-domen.rs -AdminPin TVOJ_ADMIN_PIN -Strict
.\run_launch_monitor.ps1 -BaseUrl https://tvoj-domen.rs -StrictPublicLive
```

## Prvi live dan
- Svakih 30 minuta: `/go-live`.
- Svakih 30 minuta: `/support-admin`.
- Na kraju dana: `/finance`, zatim CSV izvoz `/finance/live-closeout.csv`.
- Posle dana: `/pilot-live/backup`.
