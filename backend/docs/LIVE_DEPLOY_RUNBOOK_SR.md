# Sačuvaj Hranu - live deploy runbook

## 1. Pre deploy-a
- Pokreni lokalno `/pilot-live/backup`.
- Proveri `/pilot-live/readiness`.
- Proveri `/pilot-live/public-live-check`.
- Proveri `/pilot-live/pwa-status`.
- Proveri `/pilot-live/legal-status`.
- Proveri `/pilot-live/partner-ops-status`.
- Proveri `/pilot-live/customer-flow-status`.
- Proveri `/pilot-live/finance-closeout-status`.
- Proveri `/pilot-live/monitoring-status`.
- Proveri `/pilot-live/launch-monitor-status`.
- Proveri `/pilot-live/database-status`.
- Proveri `/pilot-live/production-env-audit`.
- Proveri `/pilot-live/go-no-go`.
- Proveri `/healthz`.
- Generiši produkcioni env fajl: `.\generate_production_env.ps1 -Domain https://tvoj-domen.rs -DatabaseUrl "postgresql+psycopg://USER:PASSWORD@HOST:5432/DBNAME" -Force`.
- Pokreni lokalno `.\run_production_audit.ps1`.

## 2. Obavezne produkcione vrednosti
- `DATABASE_URL` mora biti PostgreSQL ili MySQL/MariaDB.
- `PUBLIC_BASE_URL` mora biti HTTPS domen.
- `ADMIN_GUARD_ENABLED=true`.
- `ADMIN_PIN` promenjen.
- `ADMIN_SESSION_SECRET` dugačak random secret.
- `ADMIN_COOKIE_SECURE=true`.
- `ALLOWED_ORIGINS` mora biti stvarni HTTPS domen, bez wildcard-a.
- `ADMIN_PIN` ne sme biti podrazumevan i mora imati najmanje 8 karaktera.
- `PAYMENT_PROVIDER=pay_on_pickup` za prvi zatvoreni pilot.

## 2.2 Produkciona baza
Pre prvog deploy-a na produkcionu bazu pokreni jednu od opcija.

AdriaHost/MySQL:

```powershell
.\prepare_production_db.ps1 -DatabaseUrl "mysql+pymysql://USER:PASSWORD@HOST:3306/DBNAME?charset=utf8mb4" -Create -RequireProductionDb
```

PostgreSQL:

```powershell
.\prepare_production_db.ps1 -DatabaseUrl "postgresql+psycopg://USER:PASSWORD@HOST:5432/DBNAME" -Create -RequireProductionDb
```

Ako želiš da odmah upišeš pilot ponude u novu bazu:

```powershell
.\prepare_production_db.ps1 -DatabaseUrl "mysql+pymysql://USER:PASSWORD@HOST:3306/DBNAME?charset=utf8mb4" -Create -SeedPilot -RequireProductionDb
```

Ako želiš da prebaciš lokalne pilot podatke u novu produkcionu bazu:

```powershell
.\migrate_live_data.ps1 -Command export -Output .\data\live_data_export.json
.\migrate_live_data.ps1 -Command validate -Input .\data\live_data_export.json
.\migrate_live_data.ps1 -Command import -Input .\data\live_data_export.json -DatabaseUrl "mysql+pymysql://USER:PASSWORD@HOST:3306/DBNAME?charset=utf8mb4" -DryRun
.\migrate_live_data.ps1 -Command import -Input .\data\live_data_export.json -DatabaseUrl "mysql+pymysql://USER:PASSWORD@HOST:3306/DBNAME?charset=utf8mb4" -ReplaceExisting
```

## 2.1 Domen i DNS
1. Kupi ili izaberi domen, npr. `sacuvajhranu.rs`.
2. Na hostingu/deploy platformi dodaj custom domain.
3. Kod registrara/DNS provajdera postavi AdriaHost nameservere:
   - `ns739.adriahost.com`
   - `ns740.adriahost.com`
4. Ako ne koristiš AdriaHost nameservere, ručno postavi DNS zapise:
   - `A @ -> 37.48.77.143`
   - `A www -> 37.48.77.143`
5. Sačekaj DNS propagaciju, obično 2-4 časa, nekada do 24 časa.
6. Proveri domen komandom:

```powershell
.\check_domain_ready.ps1 -Domain https://tvoj-domen.rs -ExpectedIp 37.48.77.143
```

Kada su produkcioni env i HTTPS spremni:

```powershell
.\check_domain_ready.ps1 -Domain https://tvoj-domen.rs -Strict
```

## 3. Deploy varijante

### Render
1. Napravi PostgreSQL bazu.
2. Napravi Web Service iz ovog backend foldera.
3. Koristi `render.yaml` ili Docker deploy.
4. Popuni secret env vrednosti u dashboardu.
5. Health check path: `/healthz`.

### Docker ručno
```powershell
docker build -t sacuvaj-hranu .
docker run --env-file .env.production -p 8000:8000 sacuvaj-hranu
```

### AdriaHost / DirectAdmin
Ako panel ima Python Application Manager ili Passenger:

```powershell
.\build_adriahost_package.ps1
```

Detalji su u `docs/ADRIAHOST_DEPLOY_SR.md`.

Za finalni upload paket sa manifestom:

```powershell
.\build_live_release.ps1
.\check_live_release.ps1
```

## 4. Posle deploy-a
- Proveri DNS i HTTPS: `.\check_domain_ready.ps1 -Domain https://tvoj-domen.rs -Strict`.
- Pokreni remote smoke test: `.\run_remote_smoke.ps1 -BaseUrl https://tvoj-domen.rs -AdminPin TVOJ_ADMIN_PIN -Strict`.
- Otvori `/healthz`.
- Otvori `/go-live` i proveri Go/No-Go odluku.
- Otvori `/pocetna`.
- Otvori `/ponude`.
- Otvori `/podrska`, `/uslovi-koriscenja`, `/privatnost`, `/bezbednost-hrane`.
- Otvori partner smenu `/partner/live?store_id=ID&pin=PIN`.
- Napravi test rezervaciju.
- Otvori QR kartu `/reservation?code=KOD`.
- Otvori `/moje-rezervacije` i proveri da se rezervacija vidi po telefonu.
- Partner potvrđuje preko `/partner/preuzimanje`.
- Partner potvrđuje isti kod preko `/partner/live`.
- Pošalji test support prijavu i proveri je u `/support-admin`.
- Proveri `/pilot-live/daily-report`.
- Otvori `/finance`, proveri dnevni closeout i preuzmi `/finance/live-closeout.csv`.

## 5. Još pre javnog marketinga
- Pravni tekstovi moraju biti provereni.
- SMS/email provider mora biti izabran.
- Remote backup mora biti aktivan.
- Payment provider/webhook se dodaje tek posle zatvorenog pilot testa.

## 6. Monitoring tokom prvog dana
- Na svakih 30 minuta otvori `/go-live`.
- Na svakih 30 minuta pokreni `.\run_launch_monitor.ps1 -BaseUrl https://sacuvaj-hranu.rs`.
- Proveri `/pilot-live/monitoring-status`.
- Proveri `/pilot-live/launch-monitor-status`.
- Proveri `/support-admin` i zatvori hitne prijave.
- Proveri `/finance` i dnevni closeout.
- Posle svake veće promene pokreni `/pilot-live/backup`.

## 7. Rollback
- Ako rezervacije ne rade: sakrij promociju i zadrži `/ponude` samo za ručno testiranje.
- Ako partner potvrda ne radi: koristi `/partner/preuzimanje` kao rezervni ekran.
- Ako finance closeout ne radi: izvezi `/finance/live-closeout.csv` i vodi ručni obračun do popravke.
- Ako javni domen padne: proveri hosting health check `/healthz`, env promenljive i poslednji deploy log.
