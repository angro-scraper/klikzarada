Redizajniraj i implementiraj kompletan SaaS web proizvod „KlikZarada”, srpsku platformu za mikro-zadatke koja povezuje korisnike koji rade proverljive zadatke i oglašivače koji plaćaju rezultate.

Radi direktno u povezanom GitHub repozitorijumu.

VAŽNO - AKTIVNI PROJEKAT I DEPLOY:
- Aktivna KlikZarada aplikacija je u:
  klikzarada-v11-18-36-complete-trust-launch-pack/klikzarada-v11-18-36-complete-trust-launch-pack/backend
- Render koristi baš taj folder kao rootDir.
- Ne menjaj korenski `backend/` projekat pod nazivom „Sačuvaj Hranu”. To je drugi, nepovezan projekat.
- Ne menjaj `render.yaml`, Dockerfile, modele baze, autentikaciju, finansijsku logiku ili API rute osim ako je to neophodno za konkretno funkcionalno poboljšanje.
- Ne ubacuj API ključeve, bankovne podatke, test kredencijale, lokalne URL-ove ili `127.0.0.1` u interfejs.
- Koristi relativne rute i postojeću logiku aplikacije.
- Radi na grani `main`, sa malim jasnim commitovima.

TEHNOLOGIJA:
- FastAPI
- Jinja HTML šabloni: `backend/app/templates`
- CSS: `backend/app/static/css/style.css`
- Statički resursi: `backend/app/static`
- Postojeći sistem već ima korisnike, oglašivače, zadatke, dokaze, novčanik, isplate, referral, bedževe, dnevne nagrade, misije, admin, finansije, bannere, moderaciju i API izvore zadataka.

CILJ DIZAJNA:
Napravi moderan, ozbiljan, premium i pregledan proizvodni interfejs. Platforma mora ulivati poverenje, biti jednostavna za korišćenje i izgledati kao pravi SaaS proizvod.

Ne kopiraj dizajn, grafiku, kod ili tekst sa starih „buks”, SEO-fast ili sličnih sajtova. Možeš koristiti samo opšte ideje:
- jasan korisnički dashboard
- referral program
- dnevne nagrade i streak
- prioritetni zadaci
- status, reputacija i bedževi
- transparentna zarada i isplate

BREND:
- Naziv: KlikZarada
- Jezik: srpski latinica
- Ton: profesionalan, pouzdan, transparentan, jasan
- Glavne boje:
  - tamna mornarsko-plava za poverenje i strukturu
  - plava za glavne akcije
  - zelena samo za zaradu, uspeh i odobrenje
  - ljubičasta samo za premium/tier elemente
  - crvena samo za rizik, grešku i odbijanje
- Koristi postojeći KlikZarada logo i brendirane ikonice gde postoje.
- Ne koristi duple ikonice.
- Ne koristi previše pill dugmića.
- Ne pravi kartice sa prevelikim zaobljenjem.
- Ne koristi prenaglašene gradijente.
- Izbegni nepregledan raspored sa puno dugmića u jednom redu.
- Svaka stranica mora imati jasnu hijerarhiju: naslov, opis, glavnu akciju, sadržaj i status.

DESIGN SYSTEM:
Napravi ili ujednači:
- paletu boja
- tipografiju
- spacing sistem
- širine sadržaja
- grid
- border radius
- senke
- primarna, sekundarna, ghost i danger dugmad
- inpute, select kontrole, textarea, upload
- kartice
- tabele
- filtere
- status bedževe
- empty state
- loading state
- success i error poruke
- modal potvrde
- responsive breakpoint-e
- fokus stanja i pristupačnost

STATUSI MORAJU BITI DOSLEDNI:
- aktivno
- na čekanju
- odobreno
- odbijeno
- blokirano
- plaćeno
- potrebno proveriti
- greška
- obustavljeno

JAVNE STRANICE:
1. Početna
- Jasna hero sekcija.
- Primarni CTA: „Pokreni zaradu”.
- Sekundarni CTA: „Kreiraj kampanju”.
- Jasno objasni kako radi za korisnike.
- Jasno objasni kako radi za oglašivače.
- Prikaži kategorije zadataka.
- Prikaži poverenje: proverljivi zadaci, zaštita od prevara, transparentne isplate, podrška.
- Reklamni/banner slot mora izgledati uredno, premium i ne sme prekriti sadržaj.
- Footer mora biti uredan i sadržati: platforma, informacije, podrška, pravila, privatnost, kontakt, društvene mreže.
- Ne prikazuj lažne statistike poput „20.000 korisnika” ako nisu stvarni podaci.

2. Javna lista zadataka
- Filteri: kategorija, nagrada, procenjeno vreme, status.
- Kartice ili tabela zadataka moraju prikazati: naziv, kategoriju, nagradu, vreme, potreban dokaz, nivo korisnika.
- Jasno prazno stanje ako nema aktivnih zadataka.
- Jasno stanje za gosta koji nije prijavljen.

3. Prijava i registracija
- Čist i siguran izgled.
- Jasan izbor: „Želim da zarađujem” ili „Želim da kreiram kampanju”.
- Bez nepotrebnih polja.
- Jasne poruke za grešku i uspeh.

KORISNIČKI PANEL - „ZARADA CENTAR”:
Napravi profesionalan korisnički dashboard.

Desktop:
- Leva sidebar navigacija.
- Glavni sadržaj u preglednim sekcijama.

Mobilni:
- Sidebar se pretvara u drawer ili donju navigaciju.
- Dugmad i tabele moraju biti upotrebljivi na telefonu.

Na vrhu korisničkog panela:
- Ukupan balans.
- Zarađeno danas.
- Zadaci danas.
- Iznos do minimalne isplate.
- Jasno primarno dugme: „Isplati sredstva”.

Dodaj pregledne sekcije:
- Dnevna nagrada sa realnim statusom i dugmetom za preuzimanje.
- Streak i reputacioni tier: Explorer, Trusted, Pro, Elite.
- Jasno pokaži šta korisniku treba za sledeći tier.
- Prioritetni zadaci koriste stvarne istaknute ili aktivne zadatke.
- Ne nazivaj nešto VIP ako korisnik nema stvarni VIP pristup.
- Referral program: broj pozvanih korisnika, objašnjenje bonusa, dugme „Podeli link”.
- Bedževi i misije.
- Moji dokazi: odobreno, na čekanju, odbijeno.
- Novčanik i istorija transakcija.
- Isplate i podaci za isplatu.
- Pametne preporuke zadataka.
- Uvek prikaži smisleno prazno stanje ako nema zadataka ili transakcija.

Referral link mora koristiti stvarni domen iz zahteva aplikacije, nikada `127.0.0.1`.

OGLAŠIVAČKI PANEL:
Napravi zaseban profesionalan panel za oglašivače.

Sekcije:
- Pregled budžeta.
- Aktivne kampanje.
- Potrošnja.
- Rezultati.
- Nova kampanja.
- Dokazi korisnika.
- Banner reklame.
- Premium pozicije.
- Fakture.
- Uplate.
- Izveštaji.
- Profil firme.

Kreiranje kampanje:
- Jasno višekoračno iskustvo.
- Definicija zadatka.
- Ciljna publika.
- Nagrada.
- Budžet.
- Trajanje.
- Potrebni dokaz.
- Pregled pre slanja.
- Jasno prikaži šta se dešava nakon slanja kampanje.

ADMIN - PROFESSIONAL OPERATIONS HUB:
Admin ne sme izgledati kao veliki skup razbacanih dugmadi.

Napravi:
- Sidebar navigaciju.
- Jasno grupisane oblasti.
- Preglednu početnu admin stranicu.
- Jednu primarnu akciju po stranici.
- Tabele sa filterima, pretragom, statusima i kontekstualnim akcijama.
- KPI kartice samo za stvarne podatke.

ADMIN GRUPE:
1. Dashboard
- Ukupni pregled.
- Aktivne kampanje.
- Kampanje na čekanju.
- Dokazi na čekanju.
- Isplate na čekanju.
- Rizici i sistemska upozorenja.

2. Finansije
- Računi platforme.
- Uplate oglašivača.
- Budžeti.
- Isplate korisnicima.
- Payout batch-evi.
- Fakture.
- Izveštaji.
- Podešavanja za realni bankovni račun i primaoca uplate.
- Ne prikazuj bankovni račun javno.
- Osjetljive podatke zaštiti admin pristupom.

3. Kampanje i reklame
- Kampanje.
- Dokazi.
- Moderacija.
- Banner slotovi.
- Plaćene promocije.
- Cene.
- Anti-fraud signal za kampanje.
- Uvoz i moderacija eksternih zadataka.

4. Ljudi
- Korisnici.
- Oglašivači.
- CRM.
- Referral.
- Growth.
- KYC/podaci za isplatu.
- Podrška i tiketi.

5. Operacije
- Dnevni pregled.
- Notification queue.
- Automatizacija.
- Anti-fraud.
- Moderacija uvoza.
- Logovi i greške.
- Deploy/status.

6. Sistem
- API izvori zadataka.
- API ključevi.
- Security.
- Feature flags.
- System settings.
- Integracije.
- Backup.
- Audit log.

ADMIN UVOZ ZADATAKA:
Postoji partner API/import sistem. Dizajniraj ga kao profesionalan tok:
- Lista izvora.
- Status izvora: aktivan, pauziran, greška.
- Poslednja sinhronizacija.
- Broj pronađenih zadataka.
- Broj novih zadataka.
- Broj preskočenih duplikata.
- Zadaci čekaju moderaciju pre objave.
- Pregled importovanog zadatka.
- Odobri, odbij, izmeni, obustavi.
- Jasne greške kada partner endpoint nije validan JSON ili nema podržan feed.
- Ne pokušavaj da scraperom preuzimaš sadržaj sa partnera bez dozvole i bez jasno podržanog API/feed formata.

BANNER I REKLAMNI SLOTOVI:
- Reklamni slotovi moraju imati smislen prostor i nikada ne smeju prekrivati tekst ili dugmad.
- Svaki slot treba imati admin podešavanje.
- Admin može videti status, trajanje, cenu, oglašivača i preview.
- Koristi oznaku „Sponzorisano” kada je sadržaj plaćen.
- Poseban slot može postojati u korisničkom panelu, ali ne sme usporiti ili narušiti osnovnu funkciju zarade.

RESPONSIVE ZAHTEVI:
- Desktop: od 1280px naviše.
- Tablet: 768px do 1279px.
- Mobilni: do 767px.
- Nema horizontalnog skrolovanja osim u tabelama, gde mora postojati jasan table wrapper.
- Zaglavlje, dugmad „Moj panel” i „Odjava” moraju ostati poravnati.
- Footer mora biti uredan na svim širinama.
- Ikonice moraju biti iste veličine i poravnate.
- Ne smeju postojati preklopljeni elementi.

IMPLEMENTACIJA:
- Koristi postojeće Jinja šablone u `backend/app/templates`.
- Koristi i ujednači postojeći `backend/app/static/css/style.css`.
- Ne dupliraj CSS bez potrebe.
- Ne briši postojeće funkcionalne rute.
- Ne uvodi lažne podatke ili demo tekst ako postoji realan podatak.
- Ako za neku funkciju još nema podataka, koristi jasno i kvalitetno prazno stanje.
- Ne menjaj DNS, Render konfiguraciju ili domenske zapise.
- Ne menjaj drugi korenski projekat „Sačuvaj Hranu”.

COMMITOVI:
Napravi male i jasne commitove:
1. `Unify KlikZarada design system and shared navigation`
2. `Redesign public KlikZarada pages`
3. `Improve user earning hub and referral experience`
4. `Improve advertiser campaign workspace`
5. `Rebuild admin as grouped operations hub`
6. `Polish responsive layouts and empty states`

PROVERE PRE SVAKOG COMMlTA:
- Python syntax proveri.
- Jinja template loading proveri.
- Proveri da CSS nema horizontalni overflow.
- Proveri desktop i mobilni raspored.
- Proveri da nema `127.0.0.1` URL-ova u korisničkim referral linkovima.
- Ne commituj `.db` fajlove, API ključeve, screenshot fajlove ili lokalne konfiguracije.

Krajnji rezultat treba da izgleda kao koherentna, moderna i pouzdana KlikZarada platforma, sa jasnim razlikama između korisnika, oglašivača i administratora.