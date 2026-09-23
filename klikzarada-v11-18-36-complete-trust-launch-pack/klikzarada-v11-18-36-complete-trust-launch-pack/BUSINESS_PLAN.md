# KlikZarada: poslovni plan i cenovnik za lansiranje

Status: predlog za odobrenje pre promene cena u aplikaciji.

## Osnovni model

KlikZarada prodaje proverene mikro-usluge, a ne placene klikove na oglase.
Oglasivac unapred dopunjuje budzet. Kada administrator odobri valjan dokaz
izvrsenja, nagrada se rezervise za korisnika. Tek nakon fraud provere i isteka
roka za prigovor, ona postaje raspoloziva za PayPal isplatu.

Ovaj model stiti sve strane:

- korisnik unapred vidi nagradu i kriterijum za odobrenje;
- oglasivac placa samo dokazano izvrsene poslove;
- platforma ima sredstva za moderaciju, refundacije, PayPal troskove i fraud zastitu.

## Sta je imala referentna skripta

Arhiva `-Buks_Mdland.zip` je analizirana samo kao poslovna referenca. Njen
kod, zastarele payment integracije i demo podaci se ne prenose u KlikZaradu.

Imala je sledece grupe:

- rucne zadatke sa nazivom, URL-om, opisom, rokom, brojem izvrsenja i cenom;
- testove proizvoda i sajta sa instrukcijama i dokazom;
- placeni surf i mini-surf sa tajmerima od 5 do 60 sekundi;
- e-mail kampanje, tekstualne i baner pozicije;
- VIP, istaknute i prioritetne pozicije;
- konkurse, referral i jednostavnu moderaciju;
- pakete za veci budzet i doplate za vidljivost.

Istorijska logika naplate bila je uglavnom "cena po prikazu" u rubljama, sa
veoma malim minimumima, oko 10% provizije na zadatke i dodatnim placanjem za
VIP/bold pozicije. To nije cenovnik koji treba kopirati: ne pokriva savremene
payment troskove, rucnu proveru, refundacije ni zastitu od botova.

## Kategorije koje KlikZarada prihvata

| Tip | Sta korisnik radi | Dokaz | Nagrada korisniku | Cena oglasivacu |
| --- | --- | --- | ---: | ---: |
| Kratka anketa | Odgovori na pitanja od 2-4 minuta | Kompletirana anketa u sistemu | 50 RSD | 70 RSD |
| UX provera | Prodje scenarij na sajtu/aplikaciji i opise problem | Kontrolna pitanja ili screenshot bez licnih podataka | 70 RSD | 100 RSD |
| Validacija podataka | Proveri javni podatak, kategoriju ili duplikat | Strukturisan odgovor i izvor | 90 RSD | 130 RSD |
| Kvalitativni feedback | Daje konkretan utisak o proizvodu ili landing strani | Odgovor minimalne kvalitativne duzine | 120 RSD | 175 RSD |
| Lokalna provera | Potvrdi javnu informaciju ili dostupnost usluge | Fotografija ili strukturisan izvestaj, samo kad je dozvoljeno | 250 RSD | 360 RSD |
| Unos i klasifikacija | Oznacava, poredi ili razvrstava podatke | Rezultat prolazi uzorak kvaliteta | 60 RSD | 85 RSD |

### Zabranjene kampanje

Ne nuditi i ne naplacivati:

- klikove na Google/AdSense/AdMob oglase ili bilo koju mrezu oglasa;
- lazne lajkove, pratioce, komentare, ocene, recenzije ili preglede;
- gledanje oglasa radi nagrade, automatsko osvezavanje ili podsticanje klikova;
- politicki uticaj, kockanje, odrasli sadrzaj, obmane i prikupljanje tudjih licnih podataka;
- zadatke koji traze prijavu u tudji nalog, sumnjiv softver ili placanje korisnika.

Oglasivac moze traziti stvaran UX obilazak svoje stranice i odgovor na
pitanja. Ne moze platiti klik, follow, pregled ili recenziju kao metriku.

## Pravila objave kampanje

Svaka kampanja mora sadrzati:

1. naziv i kategoriju;
2. URL sa `https://` gde je potreban;
3. jasne korake koje korisnik izvrsava;
4. tacno definisan dokaz i kriterijum odobrenja;
5. nagradu po izvrsenju, broj mesta i ukupan budzet;
6. publiku samo kroz dozvoljene parametre, na primer jezik, grad ili interesovanje;
7. kontakt kategoriju za spor i rok za odgovor.

Pre objave ide automatska provera URL-a i teksta, zatim moderatorski pregled
za nove oglasivace, rizicne kategorije i zadatke sa dokazima. Kampanja se ne
objavljuje dok budzet nije rezervisan.

## Cenovnik pri lansiranju

Pocetna faza traje dok nema vise od 250 verifikovanih aktivnih korisnika.
"Aktivan" znaci da je korisnik u poslednjih 30 dana zavrsio makar jedan
odobren zadatak. Broj registracija sam po sebi nije razlog za povecanje cene.

### Kampanje

- minimalna nagrada korisniku: 50 RSD;
- minimalno 20 mesta po kampanji;
- minimalni budzet kampanje: 1.500 RSD;
- standardni posao bez rucnog dokaza: 35% naknade preko fonda za nagrade;
- posao sa rucnim dokazom ili uzorkom kvaliteta: 45% naknade preko fonda;
- nema mesecne pretplate u pocetnoj fazi;
- cena i nagrada se prikazuju odvojeno pre placanja.

Primer: 20 UX provera x 70 RSD pravi fond nagrada od 1.400 RSD. Standardna
naknada od 35% je 490 RSD. Oglasivac pre placanja vidi ukupan iznos od
1.890 RSD i sta svaka strana dobija.

Platformska naknada pokriva obradu placanja, PayPal payout trosak, moderaciju,
fraud analizu, podrsku i rezervu za refundacije. Ne dodavati skrivene troskove
nakon placanja.

### Banner zakup na pocetku

| Pozicija | Cena za 7 dana | Pravilo |
| --- | ---: | --- |
| Donji banner na pocetnoj | 1.200 RSD | najvise 3 istovremeno |
| Sponzorisani blok na pocetnoj | 1.800 RSD | najvise 4 istovremeno |
| Gornji premium banner | 2.500 RSD | najvise 2 istovremeno |
| Dashboard sponzor | 2.200 RSD | samo oznacen kao sponzorisano |

Svaki banner mora imati oznaku "Sponzorisano", bezbedan URL i odobrenje
administratora. Ako nema stvarnog saobracaja, banner se ne prodaje kao garancija
klikova ili pregleda.

## Rast cena bez naglog poskupljenja

Pregled radi admin jednom u 90 dana. Nove cene vaze samo za nove kampanje i
nove zakupa, nikada retroaktivno.

| Faza | Uslov dve uzastopne sedmice | Kampanje | Banneri |
| --- | --- | --- | --- |
| Lansiranje | 0-250 aktivnih | 35% / 45% | pocetni cenovnik |
| Stabilizacija | 251-1.000 aktivnih i 70% kampanja popunjeno u roku | 32% / 42% za veci fond | plus 15% |
| Rast | 1.001-5.000 aktivnih i fraud odbijanje ispod 5% | 30% / 40%; ponuda paketa | jos plus 15% |
| Skala | preko 5.000 aktivnih, 90% taskova ima rok popune ispod 7 dana | individualna ponuda za velike klijente | cena po prikazanoj publici |

Povecanje se ne odobrava ako padne kvalitet, raste broj sporova ili se zadaci
ne popunjavaju. Nagrada korisnika se ne smanjuje da bi se zadrzala marza.

## Refundacije i poverenje

- pre prvog prihvacenog zadatka: oglasivac moze obustaviti kampanju i dobija nazad neiskorisceni fond;
- posle prihvacenog zadatka: rezervisana nagrada ostaje za radnika dok se dokaz ne pregleda;
- odbijen dokaz: novac se vraca u budzet oglasivaca uz obrazlozenje;
- zadatak koji admin povuce zbog pravila: refundira se neiskorisceni fond;
- svaki spor, refundacija i admin odluka ostavlja audit zapis.

## Operativni prioriteti pre javnog lansiranja

1. Uvesti eksplicitne tipove zadataka iz tabele i njihov obrazac dokaza.
2. U adminu dodati cenovne verzije sa datumom stupanja na snagu, bez rucnog menjanja koda.
3. Prikazati oglasivacu racunicu: fond nagrada, naknada, raspolozivi budzet i refundabilni deo.
4. Uvesti metrics: aktivni verifikovani korisnici, stopa popune, odbijeni dokazi, fraud stopa, medijana vremena do popune i sporovi.
5. Objaviti pravila kampanja, privatnosti, refundacija i poreski/knjigovodstveni proces uz strucnu pravnu proveru.

## Odluka za implementaciju

Predlog je da se prvo implementira faza Lansiranje sa sest dozvoljenih tipova
zadataka, minimalnim budzetom od 1.500 RSD i jasnim troskovnikom. Tek nakon
30 dana stvarnih podataka administracija potvrdjuje prelazak na sledecu fazu.
