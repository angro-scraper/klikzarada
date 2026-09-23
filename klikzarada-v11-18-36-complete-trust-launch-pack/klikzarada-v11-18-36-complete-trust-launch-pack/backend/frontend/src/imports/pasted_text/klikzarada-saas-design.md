Nastavi postojeći KlikZarada Figma Make projekat i podigni ga na premium, kompletan SaaS dizajn.

VAŽNO:
Ovaj Figma Make projekat je dizajn/prototip. Ne sme da zameni postojeću produkcionu FastAPI aplikaciju niti da briše njene rute, modele, autentikaciju, finansije ili Render konfiguraciju.

Produkcioni kod ostaje u:
klikzarada-v11-18-36-complete-trust-launch-pack/klikzarada-v11-18-36-complete-trust-launch-pack/backend

Cilj ovog projekta:
- napraviti kompletan premium UI sistem
- prikazati sve postojeće i planirane funkcije
- koristiti realistične podatke i jasna prazna stanja
- pripremiti dizajn tako da se kasnije precizno prebaci u FastAPI/Jinja aplikaciju
- ne koristiti lokalne URL-ove, lažne API integracije, API ključeve ni bankovne podatke

VIZUELNI PRAVAC:
- Elegantni B2B/B2C SaaS proizvod.
- Pouzdano, čisto, moderno, finansijski ozbiljno.
- Tamna mornarsko-plava za strukturu i poverenje.
- Jasna plava za glavne akcije.
- Zelena samo za uspeh, zaradu i odobrenje.
- Ljubičasta samo za premium, tier i istaknute funkcije.
- Crvena samo za greške, rizik i odbijanje.
- Bez previše gradijenata, prevelikih kartica, duplih ikonica i razbacanih dugmića.
- Dosledne outline ikonice.
- Jasni naslovi, dosta praznog prostora i pregledna hijerarhija.
- Desktop, tablet i mobilni dizajn za svaku ključnu stranicu.

NAPRAVI KOMPLETAN DESIGN SYSTEM:
- Color tokens.
- Typography scale.
- Spacing i grid sistem.
- Buttons: primary, secondary, ghost, danger, icon-only.
- Inputs, select, textarea, upload, checkbox, radio, toggle.
- Cards, tables, filters, tabs, sidebar, topbar.
- Status bedževi: aktivno, na čekanju, odobreno, odbijeno, plaćeno, blokirano, greška, pauzirano.
- Empty, loading, success i error states.
- Confirmation modal za osetljive akcije.
- Mobile drawer navigacija.
- Fokus stanja, kontrast i pristupačnost.

JAVNI DEO:
1. Početna
- Hero sa CTA: „Pokreni zaradu” i „Kreiraj kampanju”.
- Jasna podela za korisnike i oglašivače.
- Kako radi platforma u 3 koraka.
- Kategorije zadataka.
- Zaštita od prevara, ručna provera dokaza, transparentne isplate.
- Sekcija za istaknute zadatke.
- Diskretan reklamni slot sa oznakom „Sponzorisano”.
- FAQ, kontakt, pravila, privatnost i premium footer.
- Ne prikazuj nerealne brojke ako nisu vezane za stvarne podatke.

2. Javni zadaci
- Pretraga.
- Filteri po kategoriji, nagradi, vremenu, nivou i statusu.
- Kartica zadatka: nagrada, vreme, nivo, dokaz, kategorija i detalji.
- Prazno stanje kada nema aktivnih zadataka.
- Jasan poziv za prijavu/registraciju za gosta.

3. Prijava i registracija
- Moderan auth ekran.
- Izbor uloge: „Korisnik” ili „Oglašivač”.
- Jasno objašnjenje koristi svake uloge.
- Sigurnosne poruke i recovery stanje.

KORISNIČKI PANEL - ZARADA CENTAR:
Napravi profesionalan dashboard koji objedinjuje sve postojeće funkcije.

Navigacija:
- Pregled
- Dostupni zadaci
- Pametne preporuke
- Moji dokazi
- Novčanik
- Isplate
- Dnevne nagrade i misije
- Bedževi
- Referral program
- Podaci za isplatu
- Profil
- Notifikacije i podrška

Dashboard:
- Ukupan balans.
- Zarađeno danas.
- Zadaci danas.
- Iznos do minimalne isplate.
- Primarno dugme „Isplati sredstva”.
- Dnevna nagrada sa statusom preuzeto/spremno.
- Streak i reputacioni tier: Explorer, Trusted, Pro, Elite.
- Jasno pokaži uslove za sledeći tier.
- Prioritetni zadaci koriste stvarne aktivne ili istaknute zadatke.
- Referral kartica: broj pozvanih korisnika, bonus pravilo i „Podeli link”.
- Bedževi i dnevne misije.
- Pregled dokaza po statusu.
- Istorija wallet transakcija.
- Jasni empty state-ovi kada nema zadataka, transakcija ili referral-a.

OGLAŠIVAČKI PANEL:
Navigacija:
- Pregled
- Nova kampanja
- Moje kampanje
- Dokazi korisnika
- Rezultati i analitika
- Banner reklame
- Premium pozicije
- Budžet
- Uplate
- Fakture
- Izveštaji
- Profil firme
- Podrška

Dashboard:
- Raspoloživi budžet.
- Rezervisan budžet.
- Aktivne kampanje.
- Rezultati kampanja.
- Dokazi na čekanju.
- Potrošnja po kampanji.
- Jasne akcije: „Kreiraj kampanju”, „Dopuni budžet”, „Pregledaj dokaze”.

Kreiranje kampanje:
- Korak 1: naziv, kategorija, opis i link.
- Korak 2: nagrada, broj izvršenja i budžet.
- Korak 3: ciljna publika i potreban dokaz.
- Korak 4: pregled i slanje na moderaciju.
- Jasni statusi draft, na moderaciji, aktivna, pauzirana, završena.

ADMIN - PREMIUM OPERATIONS HUB:
Admin mora izgledati kao operativni sistem, ne kao mreža nepovezanih dugmića.

Glavna struktura:
- Leva sidebar navigacija.
- Gornji status bar.
- Jedna jasna primarna akcija po ekranu.
- Dashboard sa stvarnim KPI podacima.
- Tabele sa pretragom, filterima, statusima i akcijama po redu.
- Brze akcije samo za najčešće operacije.

Grupe u adminu:
1. Dashboard
- Aktivne kampanje.
- Kampanje na čekanju.
- Dokazi na čekanju.
- Isplate na čekanju.
- Budžet oglašivača.
- Rizik i sistemska upozorenja.

2. Finansije
- Računi platforme.
- Uplate oglašivača.
- Budžeti.
- Isplate korisnicima.
- Payout batch-evi.
- Fakture.
- Naplata.
- Izveštaji.
- Podešavanja stvarnog računa za uplatu i isplatu, dostupna isključivo administratorima.

3. Kampanje i reklame
- Kampanje.
- Dokazi.
- Moderacija.
- Banner slotovi.
- Plaćene promocije.
- Cene.
- Anti-fraud signali.
- Podesi trajanje, cenu, oglašivača i preview za svaki banner slot.

4. Ljudi
- Korisnici.
- Oglašivači.
- CRM.
- Referral.
- Growth.
- KYC i podaci za isplatu.
- Tiketi i poruke.

5. Operacije
- Dnevni pregled.
- Queue za obaveštenja.
- Automatizacija.
- Anti-fraud.
- Moderacija uvoza.
- Logovi grešaka.
- Deploy i sistemski status.

6. Sistem i integracije
- API izvori zadataka.
- Status sinhronizacije.
- API ključevi.
- Feature flags.
- Security.
- Backup.
- Audit log.
- Podešavanja platforme.

UVOZ ZADATAKA:
Dizajniraj kompletan ekran za partner/API izvore:
- Lista izvora.
- Aktivno, pauzirano, greška.
- Poslednja sinhronizacija.
- Broj pronađenih, uvezenih i preskočenih zadataka.
- Pregled importovanog zadatka pre objave.
- Odobri, odbij, izmeni, obustavi.
- Jasna poruka kada endpoint vraća nevalidan JSON ili nije podržan feed.
- Ne prikazuj da je uvoz „uspešan” dok zadaci nisu stvarno moderirani.

BANNER SISTEM:
- Banneri ne smeju prekrivati sadržaj, dugmad ili footer.
- Svaki banner slot ima veličinu, preview, cenu, trajanje, status i vlasnika.
- Sponzorisani sadržaj mora biti jasno označen.
- Korisnički panel može imati jedan diskretan slot, ali zarada i zadaci moraju ostati fokus.

OBAVEZNE EKRANE:
- Design system
- Početna desktop i mobilna
- Javni zadaci
- Login i registracija
- Korisnički dashboard
- Novčanik
- Isplate
- Referral i bedževi
- Oglašivač dashboard
- Kreiranje kampanje
- Budžet i fakture
- Admin dashboard
- Admin finansije
- Admin moderacija dokaza
- Admin API uvoz zadataka
- Admin korisnici i oglašivači
- Admin banner slotovi
- Admin sistemska podešavanja

KVALITET:
- Nema horizontalnog skrolovanja na mobilnom.
- Tabele imaju responsive wrapper.
- Ne koristi duple ikonice.
- Ne pravi dugačke redove sitnih dugmadi.
- „Moj panel” i „Odjava” moraju biti pravilno poravnati.
- Footer je uredan na svim rezolucijama.
- Svaka funkcija ima jasno stanje kada nema podataka.
- Ne uvodi nerealne statistike, lažne finansijske podatke ili demo sadržaj bez oznake.

Na kraju napravi kratku listu:
- postojećih funkcija koje dizajn pokriva
- novih funkcija koje dizajn predlaže
- funkcija koje zahtevaju backend/API implementaciju pre produkcije