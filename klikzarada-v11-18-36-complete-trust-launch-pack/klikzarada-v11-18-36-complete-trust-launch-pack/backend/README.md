# KlikZarada V11 Real Launch Pack

V11 je veliki produkcioni update preko V10 Automation OS verzije.

## Novo u V11

### Real Launch / Admin Daily Desk
- glavni V11 dashboard: `/admin/v11`
- Admin Daily Desk: `/admin/daily-desk-v11`
- jedna strana za pending dokaze, isplate, fraud signale i dnevne note

### Security hardening
- email verification token model
- password reset tok
- login attempt log
- admin 2FA demo kod
- user device sessions
- rute:
  - `/reset-lozinke`
  - `/verify-email/{token}`
  - `/admin/security-v11`

### Payout sistem
- korisnik dodaje payout method
- admin verifikuje/odbija payout method
- payout holds
- payout export zapis
- rute:
  - `/korisnik/payout-profile-v11`
  - `/admin/payouts-v11`

### Budget / campaign ops
- advertiser budget alerts
- campaign status logs
- ruta: `/admin/budget-v11`

### Anti-fraud
- fraud signals
- risk score
- forbidden task rules
- ruta: `/admin/fraud-v11`

### Legal / compliance
- legal pages
- user consent model
- forbidden task rules
- javna ruta: `/legal/{slug}`
- admin ruta: `/admin/legal-v11`

### Marketing / sales pages
- landing pages:
  - `/lp/za-korisnike`
  - `/lp/za-oglasivace`
  - `/lp/za-agencije`
  - `/lp/testiranje-sajtova`
  - `/lp/ankete-i-istrazivanja`
  - `/lp/cenovnik-v11`
- admin ruta: `/admin/marketing-v11`

### Deploy / production
- `.env.example`
- `Dockerfile`
- `render.yaml`
- production config checks
- deploy targets
- backup run records
- route: `/admin/deploy-v11`

### Smoke test / backup scripts
- `scripts/smoke_test_v11.py`
- `scripts/backup_v11.py`
- `scripts/restore_v11.py`
- admin smoke test: `/admin/smoke-v11`
- API:
  - `/api/v1/v11/health`
  - `/api/v1/v11/smoke`

## Pokretanje

```powershell
cd $env:USERPROFILE\Downloads
Expand-Archive -Path .\klikzarada-v11-real-launch-pack.zip -DestinationPath .\klikzarada-v11-work -Force
cd .\klikzarada-v11-work\klikzarada-v11-real-launch-pack\backend

python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Otvori:

```text
http://127.0.0.1:8000
```

## Demo nalozi

```text
Admin:
admin@klikzarada.rs
Admin123!

Oglašivač:
oglasivac@demo.rs
Demo123!

Korisnik:
korisnik@demo.rs
Demo123!
```

## Test V11 rute

```text
/admin/v11
/admin/daily-desk-v11
/admin/security-v11
/admin/payouts-v11
/admin/budget-v11
/admin/fraud-v11
/admin/legal-v11
/admin/marketing-v11
/admin/deploy-v11
/admin/smoke-v11

/korisnik/payout-profile-v11
/reset-lozinke
/lp/za-korisnike
/lp/za-oglasivace
/legal/uslovi-koriscenja

/api/v1/v11/health
/api/v1/v11/smoke
```

## Lokalni smoke test

```powershell
python scripts\smoke_test_v11.py
```

## Backup

```powershell
python scripts\backup_v11.py
```

## Restore

```powershell
python scripts\restore_v11.py backups\klikzarada_v11_backup_YYYYMMDD_HHMMSS.db
```

## Napomena

V11 još uvek koristi ručne/demo tokove za email, payment i legal proveru. Pre javne produkcije:
- promeniti `KLIKZARADA_SECRET_KEY`
- prebaciti bazu na PostgreSQL
- podesiti HTTPS i domen
- povezati pravi email provider
- proveriti pravni/porezni model
- uraditi realan backup/restore test


# V11.1 UI, Ads & Pricing

## Šta je sređeno

- svetliji dizajn, manje zamara oči
- kartice/prozorčići umesto beskonačnog listanja
- nova početna strana sa plaćenim banner slotovima
- plaćeno podizanje kampanje na prvo mesto
- admin cenovnik za monetizaciju

## Admin može da menja

- cenu velikog banner slota
- cenu srednjeg banner slota
- cenu gledanja reklame koju plaća oglašivač
- nagradu korisniku za gledanje reklame
- cenu top pozicije
- cenu featured isticanja
- cenu highlighted isticanja
- proviziju platforme za nove kampanje

## Rute

```text
/
/panel-v111
/admin/cene-v111
/admin/reklame-v111
/oglasivac/reklame-v111
/oglasivac/boost-v111
/reklama-v111/{banner_id}/view
```

## Pokretanje

```powershell
cd $env:USERPROFILE\Downloads
Expand-Archive -Path .\klikzarada-v11-1-ui-monetization-pricing.zip -DestinationPath .\klikzarada-v11-1-work -Force
cd .\klikzarada-v11-1-work\klikzarada-v11-1-ui-monetization-pricing\backend

python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```


# V11.2 Professional Homepage Design

Ovaj update implementira izabrani profesionalni dizajn početne strane.

## Novo

- nova premium svetla početna strana
- hero sekcija kao u odobrenom mockupu
- dashboard preview desno u hero sekciji
- sponzorski banneri na početnoj
- sekcija "Kampanja na prvom mestu"
- istaknuti zadaci u lepim karticama
- sekcije "Za korisnike" i "Za oglašivače"
- metrički/testimonial strip
- premium footer CTA
- zadržane V11.1 funkcije:
  - `/admin/cene-v111`
  - `/admin/reklame-v111`
  - `/oglasivac/reklame-v111`
  - `/oglasivac/boost-v111`

## Pokretanje

```powershell
cd $env:USERPROFILE\Downloads
Expand-Archive -Path .\klikzarada-v11-2-pro-design.zip -DestinationPath .\klikzarada-v11-2-work -Force
cd .\klikzarada-v11-2-work\klikzarada-v11-2-pro-design\backend

python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```


# V11.3 Wide Professional Design

Ovaj update širi dizajn preko ekrana i dodatno sređuje početnu stranu.

## Šta je promenjeno

- stranica više nije uska i sabijena u sredini
- maksimalna širina povećana na veliki desktop layout
- hero sekcija je veća, prostranija i profesionalnija
- dashboard preview je veći i čitljiviji
- sponzorski banneri su širi i jači vizuelno
- sekcija "Kampanja na prvom mestu" je bolje raspoređena
- task kartice su veće i preglednije
- sekcije "Za korisnike" i "Za oglašivače" su prostranije
- admin/app paneli su širi i manje zbijeni

## Pokretanje

```powershell
cd $env:USERPROFILE\Downloads
Expand-Archive -Path .\klikzarada-v11-3-wide-pro-design.zip -DestinationPath .\klikzarada-v11-3-work -Force
cd .\klikzarada-v11-3-work\klikzarada-v11-3-wide-pro-design\backend

python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```


# V11.4 Pro UI Clean

Ovaj update popravlja problem koji se video u snimku:
- header više nije ogroman
- header se više ne lepi preko sadržaja
- početna je složena kao profesionalan landing page
- sekcije su čiste i pravilno raspoređene
- širina je velika, ali kontrolisana i bez haosa
- admin/app paneli su i dalje funkcionalni

Pokretanje:

```powershell
cd $env:USERPROFILE\Downloads
Expand-Archive -Path .\klikzarada-v11-4-pro-ui-clean.zip -DestinationPath .\klikzarada-v11-4-work -Force
cd .\klikzarada-v11-4-work\klikzarada-v11-4-pro-ui-clean\backend

python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```


# V11.4.1 Banner Slots & Clickable Buttons

Dodato:
- 3 dodatna banner mesta u dnu početne strane
- klikabilna dugmad u sponzorskim banerima
- klikabilno dugme za "Isplati sredstva"
- sređen footer blok

Pokretanje:

```powershell
cd $env:USERPROFILE\Downloads
Expand-Archive -Path .\klikzarada-v11-4-1-banners-buttons.zip -DestinationPath .\klikzarada-v11-4-1-work -Force
cd .\klikzarada-v11-4-1-work\klikzarada-v11-4-1-banners-buttons\backend

python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```


# V11.4.2 Pro Final Polish

Dodato:
- hero sekcija dodatno doterana bliže izabranoj referenci
- admin može da menja banner:
  - naslov
  - tekst
  - link
  - cenu bannera
  - cenu gledanja reklame
  - nagradu korisniku
  - broj dana
- admin može da menja banner slotove
- admin može ručno da doda banner oglašivaču
- hover efekti i profesionalne mikro-animacije za kartice i dugmad

Rute:
- `/admin/reklame-v111`
- `/admin/cene-v111`
- `/oglasivac/reklame-v111`
- `/oglasivac/boost-v111`


# V11.5 Full Platform UI

Ovaj update usklađuje ceo dizajn platforme sa profesionalnom početnom stranom.

## Urađeno

- novi profesionalni `app_base.html`
- kompletan korisnički panel u istom svetlom SaaS stilu
- kompletan oglašivački panel u istom stilu
- kompletan admin panel u istom stilu
- novi topbar za sve panele
- nova sidebar navigacija po ulogama
- kartice, tabele, forme i dugmad usklađeni sa početnom
- admin paneli više ne izgledaju kao stari V3/V4 sistem
- manje listanja i bolja podela po funkcijama
- responsivno za manje ekrane

## Pokretanje

```powershell
cd $env:USERPROFILE\Downloads
Expand-Archive -Path .\klikzarada-v11-5-platform-ui.zip -DestinationPath .\klikzarada-v11-5-work -Force
cd .\klikzarada-v11-5-work\klikzarada-v11-5-platform-ui\backend

python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Test

- `/`
- `/admin/v11`
- `/admin/reklame-v111`
- `/admin/cene-v111`
- `/oglasivac/panel`
- `/oglasivac/reklame-v111`
- `/korisnik/panel`
- `/panel-v111`

# V11.6 Serbian Professional Platform UI

- paneli su usklađeni sa početnom
- admin komande su na srpskom koliko god je moguće
- dodata automatska zamena čestih engleskih termina
- tabele, forme i akcije su preglednije
- sidebar je grupisan po funkcijama

Pokretanje:
```powershell
cd $env:USERPROFILE\Downloads
Expand-Archive -Path .\klikzarada-v11-6-serbian-pro-ui.zip -DestinationPath .\klikzarada-v11-6-work -Force
cd .\klikzarada-v11-6-work\klikzarada-v11-6-serbian-pro-ui\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

# V11.7 Unified Professional Platform

Ovaj update menja ključne template-e, ne samo CSS.

Urađeno:
- `/zadaci` više nije tamna stara lista, već profesionalne svetle kartice kao početna
- `/za-oglasivace` potpuno novi profesionalni template
- `/za-korisnike` novi profesionalni template
- `/cenovnik` novi profesionalni template
- `/reklame` nova stranica i svi dugmići vode na realne rute
- `/kontakt` i `/blog` realne stranice
- header, font, dugmad i raspored su ujednačeni sa početnom
- admin panel ostaje u srpskom stilu iz V11.6

Pokretanje:
```powershell
cd $env:USERPROFILE\Downloads
Expand-Archive -Path .\klikzarada-v11-7-unified-professional.zip -DestinationPath .\klikzarada-v11-7-work -Force
cd .\klikzarada-v11-7-work\klikzarada-v11-7-unified-professional\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

# V11.7.1 Admin Fixed

Popravljeno:
- `/admin/v11` više ne pada sa Internal Server Error
- ubačen nov bezbedan admin dashboard template
- admin dashboard je u istom profesionalnom svetlom stilu
- sve komande na dashboardu vode na realne stranice

Testirano:
- admin login
- `/admin/v11`
- `/admin/reklame-v111`
- `/admin/cene-v111`

# V11.8 Full Design Consistency Audit

Ovaj paket sređuje platformu kao celinu.

## Dodato

- `/admin/mapa-platforme` — mapa svih glavnih stranica, grupisano po funkciji
- `/api/v1/v11/design-map` — API lista stranica
- finalni CSS sloj koji sprečava vraćanje starih tamnih kartica i starih tabela
- javne, admin, oglašivačke i korisničke stranice imaju isti svetli profesionalni stil
- dugmad i tabele su dodatno ujednačeni
- skripta za proveru:
  - `scripts/design_audit_v118.py`

## Pokretanje audita

```powershell
python scripts\design_audit_v118.py
```

## Pokretanje aplikacije

```powershell
cd $env:USERPROFILE\Downloads
Expand-Archive -Path .\klikzarada-v11-8-design-audit.zip -DestinationPath .\klikzarada-v11-8-work -Force
cd .\klikzarada-v11-8-work\klikzarada-v11-8-design-audit\backend

python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

# V11.9 Structured Professional Platform

Ovaj update rešava preglednost:

- nova `/admin/mapa-platforme` kao jedna centralna stranica
- svaka funkcija iz mape ima svoju stranicu: `/admin/funkcija/{slug}`
- nova `/zadaci` stranica sa kategorijama, pretragom i istaknutim zadacima
- dodato 12 kategorija zadataka
- nova stranica za svaku kategoriju: `/zadaci-kategorija/{slug}`
- novi admin `/admin/kampanje` bez ogromnih dugmića i nepreglednog listanja
- novi admin `/admin/reklame-v111` kao kartice, ne ogromne tabele
- sve važne rute testirane skriptom `scripts/design_audit_v119.py`

Pokretanje:
```powershell
cd $env:USERPROFILE\Downloads
Expand-Archive -Path .\klikzarada-v11-9-structured-platform.zip -DestinationPath .\klikzarada-v11-9-work -Force
cd .\klikzarada-v11-9-work\klikzarada-v11-9-structured-platform\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Audit:
```powershell
python scripts\design_audit_v119.py
```

# V11.10 Final Layout Consistency

Popravljeno po screenshotovima:
- `/admin/kampanje` je prebačen iz tabele u pregledne kartice
- akcije kampanja su kompaktne
- nema više ogromnog presecanja po širini
- `/admin/reklame-v111` ima sekcije koje popunjavaju širinu normalno
- prazna stanja su široka i profesionalna, ne mala kartica u uglu
- banner slotovi, top pozicija i log gledanja su razdvojeni u jasne sekcije
- mapa platforme je još preglednija

Audit:
```powershell
python scripts\design_audit_v1110.py
```

# V11.11 Perfect UI Pass

Popravljeno:
- `/admin/dokazi` potpuno nova profesionalna stranica
- `/korisnik/dokazi` nova stranica
- `/oglasivac/dokazi` nova stranica
- `/admin/finansije` dobija obojene finansijske kartice
- `/admin/isplate` dobija isti kartični sistem
- dodat kolor sistem: plava, zelena, ljubičasta, narandžasta, crvena
- dodata audit skripta `scripts/design_audit_v1111.py`

Audit:
```powershell
python scripts\design_audit_v1111.py
```

# V11.12 Admin Clean Full Width

Admin deo je sada bez levog sidebar-a.

Urađeno:
- nema više levog “Admin centar” spiska
- Admin centar je gore u meniju
- dodat `/admin-centar` kao centralna stranica sa dugmadima/karticama
- admin stranice su full-width
- admin komande su u horizontalnom button meniju
- kartice koriste celu širinu ekrana
- manje horizontalnog povlačenja
- audit: `scripts/admin_clean_audit_v1112.py`

Pokretanje audita:
```powershell
python scripts\admin_clean_audit_v1112.py
```

# V11.13 Admin Automation & Control

Dodato:
- admin podešava procenat platforme i procenat korisniku za gledanje reklame
- automatski izračun nagrade korisniku iz cene gledanja
- nove admin stranice:
  - `/admin/cene-v111`
  - `/admin/budget-v11`
  - `/admin/fraud-v11`
  - `/admin/workflows-v10`
  - `/admin/deploy-v11`
- automatska kontrola vremena na zadatku `/zadaci/{id}`
- korisnik ne može da pošalje dokaz dok tajmer ne istekne
- ako korisnik promeni tab/izađe, tajmer se pauzira
- admin quick auto-boost za kampanju
- audit: `scripts/admin_automation_audit_v1113.py`

# V11.14 Auto Approval & Budget Engine

Urađeno osim automatske isplate:
- automatsko skidanje budžeta za top poziciju
- automatsko aktiviranje top pozicije za kampanju
- auto engine logovi
- notification queue za email/SMS, bez pravog slanja
- task view session tabela
- API start/tick za kontrolu tajmera
- automatsko odobravanje sigurnih dokaza
- anti-fraud signali
- workflow pregled automatizacije
- audit `scripts/auto_engine_audit_v1114.py`

# V11.15 Smart Automation & User Motivation

Dodato:
- automatska rezervacija zadataka
- automatsko vraćanje isteklih rezervacija
- automatsko zatvaranje popunjenih kampanja
- automatsko pauziranje kampanja bez budžeta
- quality score korisnika
- risk score korisnika
- statusi korisnika: Nov, Pouzdan, Proveren, Premium tester, VIP korisnik, Pod kontrolom, Rizičan
- bedževi
- dnevne nagrade
- streak sistem
- dnevne misije
- leaderboard
- automatski predlozi oglašivaču
- dnevni admin izveštaj
- smart admin panel `/admin/smart-v115`
- motivacioni korisnički panel `/korisnik/motivacija-v115`
- oglašivački saveti `/oglasivac/saveti-v115`
- audit `scripts/smart_automation_audit_v1115.py`


## V11.15.1 UI polish
- sređen korisnički panel prema traženom rasporedu
- dugme za isplatu pomereno i pregledno postavljeno
- motivacija stranica dobila lepši layout
- ruta /korisnik/motivacija-v115 više ne baca 403 za pogrešan tip korisnika, već radi bez ružne greške

# V11.16 Premium Platform UI

Finalna tura za ujednačen dizajn:
- početna stranica dobila premium layout
- korisnički panel ostaje u istom premium stilu
- oglašivački panel kompletno prepakovan
- admin dashboard kompletno prepakovan
- novi app shell i navigacija
- isti font, dugmad, kartice, širine, boje i raspored
- audit: `scripts/premium_ui_audit_v1116.py`

# V11.16.1 User Wallet / Payout / Badges Fix

Ispravljeno:
- dugme za isplatu na početnoj kartici pomereno ispod balansa
- /korisnik/wallet je posebna stranica za novčanik
- /korisnik/isplate je posebna stranica za zahteve za isplatu
- /korisnik/bedzevi je posebna stranica za bedževe
- /korisnik/referral je posebna stranica za referral
- motivacija prikazuje i zaključane bedževe
- audit: scripts/user_pages_fix_audit_v1161.py

# V11.17 Admin Analytics & Separate CRM Databases

Dodato:
- automatsko merenje poseta platformi
- broj ukupnih i dnevnih poseta
- jedinstveni posetioci preko visitor cookie ID
- najposećenije stranice
- posete po ulozi: guest, korisnik, oglasivac, admin
- broj registrovanih korisnika
- broj registrovanih oglašivača
- posebna CRM baza korisnika: `UserDirectoryV117`
- posebna CRM baza oglašivača: `AdvertiserDirectoryV117`
- CSV export za korisnike i oglašivače
- admin stranice:
  - `/admin/analitika-v117`
  - `/admin/korisnici-baza-v117`
  - `/admin/oglasivaci-baza-v117`
- audit: `scripts/admin_analytics_audit_v117.py`

# V11.17.1 Home Banners Fix

Ispravljena početna:
- smanjeni veliki prozori i kartice
- vraćen pregledan hero
- dodata desna hero banner pozicija
- dodata tri top banner slota
- dodat veliki horizontalni banner između sekcija
- dodata četiri mini banner mesta pri dnu
- početna ostaje premium, ali bez prevelikih prozora
- audit: `scripts/home_banners_audit_v1171.py`


# V11.17.2 Admin Nav Clean

- uklonjene duple admin navigacione trake
- admin dugmići složeni u 2 pregledna reda
- bez horizontalnog skrola u admin meniju
- zadržan isti premium dizajn
- fokus na preglednost za /admin/reklame-v111 i ostale admin stranice

# V11.18.1 Production Polish Final

Finalno upakovano:
- početna po odobrenom preview stilu
- hero podeljen u dve simetrične polovine
- uklonjeni dodatni veliki prozori za korisnike/oglašivače sa početne
- banneri profesionalno raspoređeni
- kampanja na prvom mestu kompaktna i podeljena
- admin dugmad grupisana bojama i aktivno dugme jasno vidljivo
- korisnik i oglašivač dobijaju ujednačen stil i brze linkove
- novčanik, isplate, bedževi i referral su odvojeni

# V11.18.2 Approved Home

Početna je napravljena prema odobrenoj slici:
- isti raspored kao target
- top horizontalni banner iznad svega podeljen na 2 dela
- hero levo tekst, desno dashboard panel
- sponzorski banneri + kampanja na prvom mestu
- 5 istaknutih zadataka
- statistički strip
- CTA sekcija
- dodatna donja 3 reklamna bannera
- footer kao u target slici


# V11.18.3 Professional Home Polish

- sređene boje, slova i kartice
- profesionalniji top banneri i sponzorski blokovi
- doterani task cardovi
- footer proširen i sređen da izgleda punije i profesionalnije
- ukupna početna dodatno usklađena po approved izgledu


# V11.18.4 Next Polish Update

- sponsor banneri sada imaju ilustracije / SVG vizuale
- top split banneri su dodatno profesionalno doterani
- footer je luksuzniji i vizuelno jači
- korisnički i oglašivački panel su dodatno usklađeni sa početnom
- cache bust CSS podignut na ?v=1184


# V11.18.5 Final Premium Pack

Završni polish:
- bolji mobilni prikaz početne, admina, korisnika i oglašivača
- još ujednačeniji admin / korisnik / oglašivač panel
- aktivni linkovi, hover efekti i sidebar sređeni
- brzi linkovi u korisničkom i oglašivačkom panelu dobijaju ikonice
- bolji kontrast, padding i kartice
- production-ready CSS cache bust ?v=1185


# V11.18.6 Readable Home Fix

- popravljena čitljivost svih tekstova i bannera
- smanjeni top banneri da hero ne beži ispod ekrana
- popravljeno dugme Naruči kampanju da ne izlazi iz kartice
- svi banner tekstovi imaju jak kontrast
- footer i donji banneri punom širinom i profesionalnije


# V11.18.7 Readable Text Colors

Fix samo za vidljivost slova:
- svi tekstovi na obojenim bannerima prebačeni u belu boju
- sekundarni tekst na bannerima dobija bolji kontrast
- hero/dashboard/task kartice dobijaju tamnija slova
- dugmad imaju belu boju slova
- paneli, forme i tabele imaju čitljiv tekst
- CSS cache bust ?v=1187


# V11.18.8 Task Banner Polish

Implementiran prihvaćeni izgled:
- istaknuti zadaci uredni, čitljivi i bez preklapanja labela
- cena poravnata gore desno
- Lako/Srednje labeli su pill badge
- top 2 premium bannera simetrična i profesionalna
- donji reklamni banneri dodatno doterani
- CSS cache bust ?v=1188


# V11.18.9 Full Premium Home

Cela početna je prebačena u odobreni premium stil:
- top 2 banneri
- navigacija ostaje čista
- hero + dashboard kao odobrena slika
- realnije SVG ikonice za dashboard
- sponzorski banneri
- kampanja na prvom mestu
- istaknuti zadaci
- statistički strip
- CTA
- 3 donja banera
- footer
- CSS cache bust ?v=1189


# V11.18.11 Footer Banners Polish

Finalni polish:
- 3 donja banera povećana po visini i vizuelno doterana
- footer širi, niži, bolje poravnat i profesionalniji
- CTA strip smanjen po visini
- hover/focus efekti za linkove i dugmad
- CSS cache bust ?v=11811
