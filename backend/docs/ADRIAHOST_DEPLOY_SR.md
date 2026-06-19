# Sačuvaj Hranu - AdriaHost deploy paket

## Šta je spremno
Ovaj repo ima poseban ZIP builder za AdriaHost/DirectAdmin:

```powershell
.\build_adriahost_package.ps1
```

Paket se pravi u `dist/` i ne ubacuje:
- `.env`
- lokalnu SQLite bazu
- `.venv`
- logove
- backup fajlove
- QA screenshotove

## Privremeni public_html landing
Dok se FastAPI backend ne podigne, možeš zameniti DirectAdmin default stranicu brendiranom landing stranicom:

```powershell
.\build_static_landing_package.ps1
```

Za kompletan release paket sa manifestom i SHA256 proverom:

```powershell
.\build_live_release.ps1
.\check_live_release.ps1
.\check_public_html_package.ps1
.\print_live_upload_plan.ps1
```

ZIP sadrži:
- `index.html`
- `.htaccess`
- `robots.txt`
- `sitemap.xml`
- `site.webmanifest`

Uploaduj ga u `public_html` i raspakuj preko postojećeg default `index.html`.
Bitno: `index.html`, `.htaccess`, `robots.txt`, `sitemap.xml` i `site.webmanifest` moraju biti direktno u `public_html`, ne u dodatnom podfolderu.

Ako HTTPS još nije potpuno proradio, u `.htaccess` privremeno komentariši redirect blok.

## Ako panel ima Python Application Manager
1. Uploaduj ZIP u aplikacioni folder.
2. Raspakuj ZIP.
3. Instaliraj:

```bash
pip install -r requirements-adriahost.txt
```

4. Ako panel traži WSGI fajl, koristi:

```text
passenger_wsgi.py
```

5. Ako panel traži ASGI import, koristi:

```text
app_asgi:app
```

## Produkcione vrednosti
Pre starta aplikacije podesi env:

```text
PUBLIC_BASE_URL=https://sacuvaj-hranu.rs
ALLOWED_ORIGINS=https://sacuvaj-hranu.rs
ADMIN_GUARD_ENABLED=true
ADMIN_COOKIE_SECURE=true
DATABASE_URL=mysql+pymysql://USER:PASSWORD@HOST:3306/DBNAME?charset=utf8mb4
```

Generator env fajla:

```powershell
.\generate_production_env.ps1 -Domain https://sacuvaj-hranu.rs -DatabaseUrl "mysql+pymysql://USER:PASSWORD@HOST:3306/DBNAME?charset=utf8mb4" -Force
.\check_mysql_schema.ps1
.\prepare_production_db.ps1 -DatabaseUrl "mysql+pymysql://USER:PASSWORD@HOST:3306/DBNAME?charset=utf8mb4" -Create -RequireProductionDb
```

## Migracija lokalnih pilot podataka
Kada produkciona baza postoji:

```powershell
.\migrate_live_data.ps1 -Command export -Output .\data\live_data_export.json
.\migrate_live_data.ps1 -Command validate -Input .\data\live_data_export.json
.\migrate_live_data.ps1 -Command import -Input .\data\live_data_export.json -DatabaseUrl "mysql+pymysql://USER:PASSWORD@HOST:3306/DBNAME?charset=utf8mb4" -DryRun
.\migrate_live_data.ps1 -Command import -Input .\data\live_data_export.json -DatabaseUrl "mysql+pymysql://USER:PASSWORD@HOST:3306/DBNAME?charset=utf8mb4" -ReplaceExisting
```

## Ako Basic 4.0 nema Python aplikacije
Ako nema Python Application Manager / Passenger / terminal / pip, ovaj shared hosting ne može direktno da pokrene FastAPI.

Tada radi ovako:
1. domen i email ostaju na AdriaHost-u,
2. aplikacija ide na Render/Railway/VPS,
3. DNS za `sacuvaj-hranu.rs` se usmeri ka tom servisu,
4. proverava se:

```powershell
.\run_remote_smoke.ps1 -BaseUrl https://sacuvaj-hranu.rs -AdminPin TVOJ_ADMIN_PIN -Strict
```
