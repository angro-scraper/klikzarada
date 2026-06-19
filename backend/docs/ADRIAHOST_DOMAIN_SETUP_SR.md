# Sačuvaj Hranu - domen na AdriaHost

## Podaci za domen
- Domen: `sacuvaj-hranu.rs`
- Status: domen kupljen kod AdriaHost-a 19.06.2026.
- SSL status: Let's Encrypt uspešno zatražen u DirectAdmin panelu za `sacuvaj-hranu.rs` i `www.sacuvaj-hranu.rs` 19.06.2026.
- Server IP: `37.48.77.143`
- Privremeni panel host: `budo370.adriahost.com`
- Primarni nameserver: `ns739.adriahost.com`
- Sekundarni nameserver: `ns740.adriahost.com`

## Preporučeno usmeravanje domena
Domen je sada u AdriaHost nalogu, pa bi nameserveri trebalo da budu podešeni automatski:

```text
ns739.adriahost.com
ns740.adriahost.com
```

Posle kupovine i aktivacije obično treba 2-4 časa za propagaciju, nekada do 24 časa.

Kada NS delegacija proradi, AdriaHost DNS zona treba da vodi domen na hosting paket.

## Alternativno ručno DNS podešavanje
Ako ne koristiš AdriaHost nameservere nego DNS ostaje kod drugog provajdera, u DNS zoni postavi:

| Tip | Naziv | Vrednost |
| --- | --- | --- |
| A | `@` ili prazno | `37.48.77.143` |
| A | `www` | `37.48.77.143` |

Ako panel ne dozvoljava `A` za `www`, koristi:

| Tip | Naziv | Vrednost |
| --- | --- | --- |
| CNAME | `www` | `sacuvaj-hranu.rs.` |

## SSL
Kada DNS proradi, u panelu uključi SSL/Let's Encrypt za:
- `sacuvaj-hranu.rs`
- `www.sacuvaj-hranu.rs`

SSL se obično izdaje 30-60 minuta posle pune DNS propagacije.
U panelu je izdavanje već prošlo uspešno; spoljašnja provera još zavisi od DNS propagacije.

## Baza na AdriaHost-u
Ako Basic 4.0 nudi MySQL/MariaDB bazu, `DATABASE_URL` format je:

```text
mysql+pymysql://USER:PASSWORD@HOST:3306/DBNAME?charset=utf8mb4
```

Pre live deploy-a proveri šemu:

```powershell
.\prepare_production_db.ps1 -DatabaseUrl "mysql+pymysql://USER:PASSWORD@HOST:3306/DBNAME?charset=utf8mb4" -Create -RequireProductionDb
```

## Provera sa naše strane
```powershell
Resolve-DnsName sacuvaj-hranu.rs -Type NS
.\check_domain_ready.ps1 -Domain https://sacuvaj-hranu.rs -ExpectedIp 37.48.77.143
```

Kada aplikacija bude deploy-ovana i produkcioni env podešen:

```powershell
.\check_domain_ready.ps1 -Domain https://sacuvaj-hranu.rs -ExpectedIp 37.48.77.143 -Strict
.\run_remote_smoke.ps1 -BaseUrl https://sacuvaj-hranu.rs -AdminPin TVOJ_ADMIN_PIN -Strict
```

## Važna napomena za FastAPI
Ako Basic 4.0 paket nema opciju za Python aplikaciju / Passenger / Application Manager, ovaj hosting može da posluži za DNS, domen i eventualno statičnu stranicu, ali ne može direktno da pokrene FastAPI aplikaciju.

U tom slučaju najčistije rešenje je:
1. aplikaciju deploy-ovati na Render/Railway/VPS,
2. u DNS-u domen `sacuvaj-hranu.rs` usmeriti na taj servis,
3. u produkcionom env-u staviti `PUBLIC_BASE_URL=https://sacuvaj-hranu.rs`.
