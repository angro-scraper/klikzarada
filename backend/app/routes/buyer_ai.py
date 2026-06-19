from __future__ import annotations

import json
import os
import re
import unicodedata
from pathlib import Path
from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from .products import product_to_public, VISIBLE_STATUSES, SUPPORTED_CITIES, BELGRADE_DISTRICTS, SUPPORTED_CATEGORIES
from ..services.admin_auth import require_admin_session


DATA_DIR = Path(__file__).resolve().parents[2] / "data"
KNOWLEDGE_PATH = DATA_DIR / "ai_knowledge.json"

EXPANDED_FAQS: list[dict[str, Any]] = [{'question': 'Kako radi rezervacija?',
  'answer': 'Izaberi ponudu, klikni Rezerviši, upiši ime, telefon i količinu. Dobićeš kod rezervacije. Sačuvaj kod i '
            'pokaži ga prodavcu pri preuzimanju u navedenom terminu.',
  'keywords': ['rezervacija', 'rezervisanje', 'kod', 'preuzimanje', 'preuzmem', 'kako radi']},
 {'question': 'Šta znači pred istek roka?',
  'answer': 'Pred istek znači da je prodavac potvrdio rok ili kraći rok trajanja. Ako rok nije potvrđen, ponuda se '
            'prikazuje kao akcijska cena ili potvrđena ponuda prodavca, a ne kao pred istek.',
  'keywords': ['pred istek', 'rok', 'istice', 'ističe', 'upotrebljivo', 'najbolje upotrebiti', 'kraci rok']},
 {'question': 'Da li se plaća preko aplikacije?',
  'answer': 'Da. U ovoj verziji rezervacija može da se plati online kroz aplikaciju. Za MVP je uključena demo naplata, bez stvarnog unosa kartice. Aplikacija služi '
            'za pronalaženje, rezervaciju i online plaćanje ponude. Kupac dobija digitalnu kartu i kod rezervacije koji '
            'pokazuje prodavcu Kupac dobija digitalnu kartu i kod za preuzimanje.',
  'keywords': ['placanje', 'plaćanje', 'platim', 'kartica', 'gotovina', 'online placanje', 'plaćam', 'pay', 'naplata']},
 {'question': 'Kako da nađem ponude blizu mene?',
  'answer': 'Klikni Koristi moju lokaciju, izaberi radius, na primer 3 ili 5 km, i sortiraj po Najbliže meni. Možeš i '
            "da napišeš AI-ju: 'pecivo u krugu 5 km'.",
  'keywords': ['blizu', 'u blizini', 'lokacija', 'gps', 'najbliže', 'najblize', 'mapa', 'radius']},
 {'question': 'Mogu li da otkažem rezervaciju?',
  'answer': 'Da. Ako ponudu još nisi preuzeo/la, pošalji prodavcu informaciju što pre ili koristi opciju otkazivanja '
            'kada je dostupna. Otkazivanje na vreme pomaže da hrana ne propadne i da neko drugi može da je rezerviše.',
  'keywords': ['otkazivanje', 'otkazem', 'otkažem', 'rezervacija', 'odustajem', 'ne mogu da dodjem']},
 {'question': 'Šta ako zakasnim na preuzimanje?',
  'answer': 'Ako kasniš, najbolje je da kontaktiraš prodavca. Prodavac nije dužan da čuva ponudu posle navedenog '
            'termina, posebno kod sveže hrane i dnevnih viškova.',
  'keywords': ['kasnim', 'zakasnim', 'preuzimanje', 'termin', 'vreme preuzimanja', 'ne stizem']},
 {'question': 'Da li neko drugi može da preuzme moju rezervaciju?',
  'answer': 'Može, ako ima tvoj kod rezervacije i ime na koje je rezervacija napravljena. Sačuvaj kod i pošalji ga '
            'osobi koja preuzima.',
  'keywords': ['neko drugi', 'druga osoba', 'preuzme', 'kod', 'umesto mene']},
 {'question': 'Šta znači kod rezervacije?',
  'answer': 'Kod rezervacije je kratka potvrda da si rezervisao/la ponudu. Pokaži ga prodavcu pri preuzimanju da bi '
            'znao koju rezervaciju izdaje.',
  'keywords': ['kod rezervacije', 'kod', 'potvrda', 'broj rezervacije', 'preuzimanje']},
 {'question': 'Da li je količina garantovana?',
  'answer': 'Količina je rezervisana kada dobiješ kod, ali kod sveže hrane može doći do izuzetaka. Ako se to desi, '
            'prodavac treba da te obavesti ili ponudi zamenu, povraćaj ili drugo rešenje.',
  'keywords': ['kolicina', 'količina', 'garantovano', 'dostupno', 'rezervisano', 'nema proizvoda']},
 {'question': 'Šta ako prodavac nema proizvod kada dođem?',
  'answer': 'Sačuvaj kod rezervacije i obrati se prodavcu. U MVP verziji prodavac rešava situaciju direktno sa kupcem, '
            'a kasnije ćemo dodati prijavu problema kroz aplikaciju.',
  'keywords': ['nema proizvod', 'nema ponude', 'problem', 'dosao sam', 'došla sam', 'zalba', 'žalba']},
 {'question': 'Da li mogu da rezervišem više komada?',
  'answer': 'Možeš da rezervišeš dostupnu količinu koju aplikacija prikazuje. Rezerviši samo ono što sigurno '
            'preuzimaš, jer cilj aplikacije je da se hrana stvarno spasi od bacanja.',
  'keywords': ['vise komada', 'više komada', 'kolicina', 'količina', 'koliko mogu', 'komada']},
 {'question': 'Zašto ne vidim sve proizvode na mapi?',
  'answer': 'Na mapi se prikazuju samo ponude prodavaca koji imaju unetu GPS lokaciju. Ako prodavac nema lokaciju, '
            'ponuda se može videti u listi, ali ne mora imati marker na mapi.',
  'keywords': ['mapa', 'marker', 'ne vidim', 'gps', 'lokacija prodavca', 'koordinate']},
 {'question': 'Zašto GPS ne radi?',
  'answer': 'GPS radi najpouzdanije na localhost/127.0.0.1 tokom testa ili na HTTPS adresi kada aplikacija bude '
            'online. Ako browser blokira lokaciju, možeš ručno uneti lokaciju ili koristiti mapu.',
  'keywords': ['gps ne radi', 'lokacija ne radi', 'dozvola', 'browser', 'https', 'lokacija blokirana']},
 {'question': 'Kako AI pretraga funkcioniše?',
  'answer': "Napiši prirodno šta tražiš, na primer 'pecivo do 200 din u krugu 5 km'. AI će pokušati da podesi filtere "
            'za cenu, kategoriju, lokaciju, rok i popust.',
  'keywords': ['ai pretraga', 'kako trazim', 'kako tražim', 'filteri', 'prirodno', 'pretraga']},
 {'question': 'Šta da ukucam u AI pretragu?',
  'answer': "Možeš pisati jednostavno: 'hleb blizu mene', 'pekara do 200 din', 'najveći popusti', 'rok danas', 'pecivo "
            "u Beogradu' ili 'ponude u krugu 5 km'.",
  'keywords': ['primer', 'sta da ukucam', 'šta da ukucam', 'komanda', 'pretraga', 'ai']},
 {'question': 'Nema rezultata. Šta da radim?',
  'answer': 'Probaj da povećaš radius, ukloniš maksimalnu cenu, izabereš sve kategorije ili pretražiš šire, na primer '
            "'pekara Beograd' umesto konkretnog proizvoda.",
  'keywords': ['nema rezultata', 'nista nema', 'ništa nema', 'prazno', 'ne nalazi', 'proširi']},
 {'question': 'Šta znači akcijska ponuda?',
  'answer': 'Akcijska ponuda znači da je artikal na sniženju ili je pronađen iz javnog izvora/prodavca, ali ne mora '
            'biti pred istekom roka. Za rok je potrebna potvrda prodavca.',
  'keywords': ['akcijska ponuda', 'akcija', 'snizenje', 'sniženje', 'public discount', 'popust']},
 {'question': 'Ko potvrđuje rok trajanja?',
  'answer': 'Rok trajanja potvrđuje prodavac. AI može da pomogne u unosu i prepoznavanju, ali ne sme sam da garantuje '
            'da je proizvod pred istekom roka.',
  'keywords': ['ko potvrdjuje', 'ko potvrđuje', 'rok trajanja', 'prodavac', 'garancija', 'ai']},
 {'question': 'Da li je hrana bezbedna?',
  'answer': 'Aplikacija pomaže da pronađeš ponude, ali bezbednost hrane i tačnost deklaracije potvrđuje prodavac. '
            'Kupuj samo hranu koja je pravilno čuvana i prati oznake roka.',
  'keywords': ['bezbedna', 'sigurna', 'trovanje', 'deklaracija', 'cuvala', 'čuvana', 'hrana']},
 {'question': 'Razlika između upotrebljivo do i najbolje upotrebiti do?',
  'answer': "'Upotrebljivo do' je stroža oznaka i vezuje se za bezbednost hrane. 'Najbolje upotrebiti do' se više "
            'odnosi na kvalitet. Uvek poštuj oznaku na proizvodu i informacije prodavca.',
  'keywords': ['upotrebljivo do', 'najbolje upotrebiti', 'razlika', 'rok', 'deklaracija', 'best before', 'use by']},
 {'question': 'Da li mogu da kupim proizvod posle isteka roka?',
  'answer': 'Aplikacija treba automatski da sakrije istekle ponude. Ako vidiš spornu ponudu, nemoj je rezervisati i '
            'prijavi je prodavcu ili adminu.',
  'keywords': ['posle isteka', 'istekao rok', 'isteklo', 'da li smem', 'rok prosao', 'rok prošao']},
 {'question': 'Da li se vidi adresa prodavca?',
  'answer': 'Da, kod ponude se prikazuje prodavac i lokacija ako je uneta. Za preuzimanje koristi adresu i vreme '
            'navedeno u ponudi.',
  'keywords': ['adresa', 'gde je', 'lokacija', 'prodavac', 'preuzimanje', 'mapa']},
 {'question': 'Da li mogu da pozovem prodavca?',
  'answer': 'Ako je prodavac uneo telefon, možeš ga koristiti za dogovor oko preuzimanja. Uvek navedi kod rezervacije '
            'da bi prodavac lakše pronašao tvoju porudžbinu.',
  'keywords': ['telefon', 'pozovem', 'kontakt', 'prodavac', 'broj telefona']},
 {'question': 'Da li aplikacija ima dostavu?',
  'answer': 'Trenutno je fokus na rezervaciji i ličnom preuzimanju kod prodavca. Dostava može biti dodata kasnije kao '
            'posebna funkcija.',
  'keywords': ['dostava', 'donosi', 'kurir', 'isporuka', 'glovo', 'wolt']},
 {'question': 'Šta znači korpa iznenađenja?',
  'answer': 'Korpa iznenađenja je ponuda u kojoj prodavac daje paket hrane po sniženoj ceni, ali tačan sadržaj može '
            'zavisiti od viška hrane tog dana.',
  'keywords': ['korpa iznenadjenja', 'korpa iznenađenja', 'paket', 'surprise bag', 'sta je u korpi']},
 {'question': 'Da li mogu da znam tačan sadržaj korpe?',
  'answer': 'Ako je prodavac opisao sadržaj, videćeš ga u ponudi. Kod korpe iznenađenja sadržaj može varirati, ali '
            'cena, količina i vreme preuzimanja treba da budu jasni.',
  'keywords': ['sadrzaj', 'sadržaj', 'sta dobijam', 'šta dobijam', 'korpa', 'paket']},
 {'question': 'Kako se računaju popusti?',
  'answer': 'Popust se računa iz stare i snižene cene kada su obe cene dostupne. Ako stara cena nije poznata, '
            'prikazaće se samo trenutna/snižena cena.',
  'keywords': ['popust', 'procenat', 'stara cena', 'nova cena', 'snizena cena', 'snižena cena']},
 {'question': 'Da li je cena konačna?',
  'answer': 'Cena prikazana u ponudi je cena koju je uneo prodavac ili pronašao sistem. U MVP verziji prodavac '
            'potvrđuje konačnu cenu Kupac dobija digitalnu kartu i kod za preuzimanje.',
  'keywords': ['cena', 'konačna cena', 'konacna cena', 'koliko kosta', 'koliko košta', 'din']},
 {'question': 'Šta znači dostupna količina?',
  'answer': 'Dostupna količina je količina koja ostaje posle postojećih rezervacija. Ako je proizvod rasprodat, više '
            'se ne bi trebalo prikazivati za rezervaciju.',
  'keywords': ['dostupna kolicina', 'dostupna količina', 'rasprodato', 'sold out', 'koliko ima']},
 {'question': 'Kako da proverim svoju rezervaciju?',
  'answer': 'Na korisničkoj strani možeš uneti kod rezervacije u proveru rezervacije. Sistem će prikazati status: '
            'čeka, potvrđeno, preuzeto ili otkazano.',
  'keywords': ['provera rezervacije', 'proverim', 'status rezervacije', 'kod', 'potvrdjeno', 'potvrđeno']},
 {'question': 'Šta znače statusi rezervacije?',
  'answer': "'Čeka' znači da je poslata, 'potvrđeno' znači da je prodavac prihvatio, 'preuzeto' znači da je hrana "
            "preuzeta, a 'otkazano' znači da rezervacija više ne važi.",
  'keywords': ['status rezervacije', 'ceka', 'čeka', 'potvrdjeno', 'preuzeto', 'otkazano']},
 {'question': 'Da li moram da napravim nalog?',
  'answer': 'U MVP verziji kupac može da rezerviše bez pravljenja naloga, koristeći ime i telefon. Kasnije možemo '
            'dodati naloge, favorite i istoriju rezervacija.',
  'keywords': ['nalog', 'registracija', 'login', 'prijava', 'bez naloga']},
 {'question': 'Šta radite sa mojim telefonom?',
  'answer': 'Telefon se koristi da prodavac može da prepozna ili potvrdi rezervaciju. Ne treba unositi tuđi broj i ne '
            'treba deliti kod rezervacije javno.',
  'keywords': ['telefon', 'privatnost', 'podaci', 'broj telefona', 'gdpr', 'licni podaci']},
 {'question': 'Da li mogu da prijavim problem?',
  'answer': 'U ovoj verziji problem možeš prijaviti prodavcu ili adminu. Kasnije ćemo dodati dugme za prijavu ponude, '
            'pogrešne cene, loše slike ili nepreuzete rezervacije.',
  'keywords': ['prijava problema', 'problem', 'zalba', 'žalba', 'pogresna cena', 'pogrešna cena', 'lose']},
 {'question': 'Zašto neke ponude nemaju sliku?',
  'answer': 'Cilj je da svaka realna ponuda ima sliku, posebno za pekarske proizvode. Ako slika nedostaje, ponuda je '
            'verovatno test, stari unos ili kandidat iz crawlera.',
  'keywords': ['nema sliku', 'slika', 'fotografija', 'proizvod bez slike']},
 {'question': 'Kako da nađem samo pekare?',
  'answer': "U pretragu napiši 'pekara', 'hleb', 'pecivo' ili izaberi kategoriju pekara. Možeš dodati cenu i lokaciju, "
            "na primer 'pekara do 200 din u Beogradu'.",
  'keywords': ['pekara', 'pekare', 'hleb', 'pecivo', 'kifle', 'burek']},
 {'question': 'Kako da nađem najveće popuste?',
  'answer': "Napiši 'najveći popusti' ili izaberi sortiranje po popustu. Možeš dodati kategoriju, na primer 'najveći "
            "popusti pekara'.",
  'keywords': ['najveci popusti', 'najveći popusti', 'popust', 'snizenje', 'sniženje', 'akcija']},
 {'question': 'Kako da nađem hranu za danas?',
  'answer': "Napiši 'rok danas', 'preuzimanje danas' ili 'ponude danas'. AI će pokušati da prikaže aktuelne ponude i "
            'bliže rokove.',
  'keywords': ['danas', 'rok danas', 'preuzimanje danas', 'ponude danas', 'dnevna ponuda']},
 {'question': 'Da li mogu da filtriram po gradu?',
  'answer': "Da. Napiši grad u pretragu, na primer 'pekara Beograd' ili koristi filter za grad kada je dostupan.",
  'keywords': ['grad', 'beograd', 'novi sad', 'nis', 'niš', 'filter po gradu']},
 {'question': 'Da li ponude važe ceo dan?',
  'answer': 'Ne uvek. Svaka ponuda ima svoje vreme preuzimanja. Sveža hrana, peciva i dnevni viškovi često važe samo '
            'nekoliko sati.',
  'keywords': ['vazi ceo dan', 'važi ceo dan', 'vreme', 'preuzimanje', 'do kada', 'termin']},
 {'question': 'Kako prodavac dodaje ponude?',
  'answer': 'Prodavac u svom panelu može da doda ponudu ručno, slikom/kamerom ili brzim AI unosom jednom rečenicom. '
            'Kupci vide samo ponude koje su objavljene i aktivne.',
  'keywords': ['prodavac dodaje', 'dodavanje ponude', 'kamera', 'ai unos', 'seller']},
 {'question': 'Da li su prodavci provereni?',
  'answer': 'U bazi razlikujemo lead prodavce, nepotvrđene i potvrđene prodavce. Najsigurnije su ponude koje je '
            'prodavac sam potvrdio ili uneo kroz svoj panel.',
  'keywords': ['provereni prodavci', 'verified', 'potvrdjen', 'potvrđen', 'prodavac']},
 {'question': 'Šta znači preporuka AI-ja?',
  'answer': 'AI preporuka znači da je sistem pronašao ponude koje odgovaraju tvojoj poruci i dostupnim filterima. To '
            'nije garancija kvaliteta hrane, nego pomoć u pretrazi.',
  'keywords': ['ai preporuka', 'preporucuje', 'preporučuje', 'garancija', 'kvalitet']},
 {'question': 'Mogu li da sačuvam omiljene ponude?',
  'answer': 'Trenutno nema favorita, ali to je dobra sledeća funkcija. Za sada možeš sačuvati link ponude ili kod '
            'rezervacije kada rezervišeš.',
  'keywords': ['favoriti', 'omiljeno', 'sacuvam', 'sačuvam', 'link']},
 {'question': 'Da li aplikacija radi na telefonu?',
  'answer': 'Da. Aplikacija je zamišljena kao PWA, pa može da se koristi kroz browser i instalira kao aplikacija kada '
            'browser to podržava.',
  'keywords': ['telefon', 'mobilni', 'pwa', 'instalacija', 'aplikacija']},
 {'question': 'Gde se plaća rezervisana hrana?',
  'answer': 'Plaćanje ide online kroz aplikaciju. U MVP verziji je to demo plaćanje bez unosa stvarne kartice. '
            'Ponesi kod rezervacije i digitalnu kartu; prodavac može da proveri da li je rezervacija plaćena.',
  'keywords': ['gde placam',
               'gde plaćam',
               'placam kod prodavca',
               'plaćam kod prodavca',
               'preuzimanje',
               'gotovina',
               'kartica kod prodavca']},
 {'question': 'Da li aplikacija prima kartice?',
  'answer': 'Ne. U ovoj verziji aplikacija ne prima kartice i ne čuva podatke o kartici. Ako prodavac prima kartice u '
            'svom objektu, plaćanje se obavlja direktno kod njega.',
  'keywords': ['kartica', 'karticom', 'visa', 'mastercard', 'podaci kartice', 'online kartica', 'placanje karticom']},
 {'question': 'Da li je rezervacija besplatna?',
  'answer': 'Da. Rezervacija kroz aplikaciju je samo potvrda da želiš da preuzmeš ponudu. Proizvod plaćaš prodavcu pri '
            'preuzimanju. Rezerviši samo ono što stvarno planiraš da preuzmeš.',
  'keywords': ['besplatna rezervacija',
               'da li se placa rezervacija',
               'rezervacija kosta',
               'rezervacija košta',
               'free']},
 {'question': 'Da li aplikacija uzima proviziju od kupca?',
  'answer': 'Kupcu se prikazuje cena za plaćanje. Platforma zadržava 25% od plaćenog iznosa kao proviziju, a prodavcu ide neto iznos. Aplikacija služi za pronalaženje, rezervaciju i plaćanje '
            'ponuda.',
  'keywords': ['provizija', 'naknada', 'trosak aplikacije', 'trošak aplikacije', 'fee']},
 {'question': 'Da li dobijam fiskalni račun?',
  'answer': 'Račun izdaje prodavac u skladu sa svojim obavezama i načinom prodaje. Aplikacija ne izdaje fiskalni račun '
            'jer ne naplaćuje proizvod u ovoj verziji.',
  'keywords': ['fiskalni racun', 'fiskalni račun', 'racun', 'račun', 'invoice', 'potvrda placanja']},
 {'question': 'Da li postoji povraćaj novca kroz aplikaciju?',
  'answer': 'Ne, jer aplikacija ne prima uplatu. Ako si platio/la direktno prodavcu i postoji problem, rešava se sa '
            'prodavcem. Kasnije možemo dodati prijavu problema i evidenciju reklamacija.',
  'keywords': ['povracaj novca', 'povraćaj', 'refundacija', 'refund', 'vracanje para', 'vraćanje para']},
 {'question': 'Mogu li da platim gotovinom?',
  'answer': 'To zavisi od prodavca. Pošto aplikacija ne naplaćuje ponudu, način plaćanja dogovaraš ili obavljaš '
            'direktno u objektu prodavca Kupac dobija digitalnu kartu i kod za preuzimanje.',
  'keywords': ['gotovina', 'kes', 'keš', 'cash', 'platim gotovinom']},
 {'question': 'Mogu li da platim karticom u objektu?',
  'answer': 'Ako prodavac prima kartice u svom objektu, možeš platiti tamo. Aplikacija samo čuva rezervaciju i kod; ne '
            'obrađuje kartično plaćanje.',
  'keywords': ['karticom u objektu', 'pos terminal', 'platim karticom', 'kartica kod prodavca']},
 {'question': 'Da li moram da platim unapred?',
  'answer': 'Ne. U ovoj verziji možeš da platiš online odmah posle rezervacije. Rezervišeš ponudu u aplikaciji, platiš online i dođeš da '
            'je preuzmeš.',
  'keywords': ['unapred', 'avans', 'pre payment', 'prepaid', 'moram da platim']},
 {'question': 'Šta ako rezervišem, a ne dođem?',
  'answer': 'Ako znaš da nećeš doći, otkaži ili kontaktiraj prodavca što pre. Neodlazak bez otkazivanja može značiti '
            'da hrana propadne i da drugi kupac ostane bez ponude.',
  'keywords': ['ne dodjem', 'ne dođem', 'no show', 'nisam dosao', 'nisam došla', 'ne mogu da preuzmem']},
 {'question': 'Mogu li da promenim količinu rezervacije?',
  'answer': 'Ako još nije preuzeta, najbolje je da napraviš novu rezervaciju sa tačnom količinom ili kontaktiraš '
            'prodavca. U ovoj verziji promena količine kroz aplikaciju može biti ograničena.',
  'keywords': ['promena kolicine',
               'promenim količinu',
               'promenim rezervaciju',
               'izmeni rezervaciju',
               'smanjim',
               'povecam']},
 {'question': 'Izgubio sam kod rezervacije. Šta sad?',
  'answer': 'Proveri da li si ga kopirao/la ili sačuvao/la. Ako ga nemaš, kontaktiraj prodavca i reci ime i telefon '
            'koje si uneo/la. Kod je najbrži način da prodavac pronađe rezervaciju.',
  'keywords': ['izgubio kod', 'zaboravio kod', 'nemam kod', 'kod rezervacije', 'izgubljen kod']},
 {'question': 'Uneo sam pogrešan telefon. Šta da radim?',
  'answer': 'Ako si već napravio/la rezervaciju, kontaktiraj prodavca i navedi kod rezervacije. Za sledeću rezervaciju '
            'unesi ispravan broj, jer prodavac može koristiti telefon za potvrdu.',
  'keywords': ['pogresan telefon', 'pogrešan telefon', 'broj telefona', 'telefon', 'ispravim broj']},
 {'question': 'Da li prodavac mora da potvrdi rezervaciju?',
  'answer': 'Rezervacija može biti u statusu čeka ili potvrđeno. Ako je čeka, prodavac je još nije obradio. Ako je '
            'potvrđeno, spremna je za preuzimanje u navedenom terminu.',
  'keywords': ['mora da potvrdi', 'potvrda prodavca', 'ceka', 'čeka', 'potvrdjeno', 'potvrđeno']},
 {'question': 'Kada mogu da preuzmem ponudu?',
  'answer': 'Preuzimanje se obavlja u terminu navedenom na ponudi, na primer danas 18–21h. Kod sveže hrane je važno '
            'doći u tom periodu jer ponuda možda ne važi kasnije.',
  'keywords': ['kada preuzimam', 'vreme preuzimanja', 'termin', 'preuzimanje', 'do kada']},
 {'question': 'Da li mogu da preuzmem ranije?',
  'answer': 'Možda, ali to zavisi od prodavca. Ako želiš ranije preuzimanje, kontaktiraj prodavca i navedi kod '
            'rezervacije.',
  'keywords': ['ranije', 'pre termina', 'preuzmem ranije', 'dodjem ranije']},
 {'question': 'Da li mogu da preuzmem kasnije?',
  'answer': 'Kasnije preuzimanje nije garantovano. Sveža hrana i ponude kraćeg roka obično važe samo u navedenom '
            'terminu. Kontaktiraj prodavca ako kasniš.',
  'keywords': ['kasnije', 'posle termina', 'preuzmem kasnije', 'kasnim', 'zakasnim']},
 {'question': 'Šta znači potvrđena ponuda prodavca?',
  'answer': 'To znači da je ponudu uneo ili potvrdio prodavac. Takva ponuda je pouzdanija od kandidata iz javnog '
            'izvora, ali oznaka pred istek se koristi samo ako je rok posebno potvrđen.',
  'keywords': ['potvrdjena ponuda', 'potvrđena ponuda', 'seller verified', 'prodavac potvrdio']},
 {'question': 'Šta znači kandidat iz crawlera?',
  'answer': 'Kandidat iz crawlera je proizvod pronađen automatskim pretraživanjem javnih izvora. Takav unos treba '
            'pregledati, dopuniti slikom/cenom ako fali i ne označavati kao pred istek bez potvrde prodavca.',
  'keywords': ['crawler', 'kandidat', 'automatski pronadjeno', 'automatski pronađeno', 'javni izvor']},
 {'question': 'Zašto neka ponuda nije pred istek roka?',
  'answer': 'Zato što za oznaku pred istek mora postojati potvrda prodavca i konkretan rok. Ako toga nema, ponuda može '
            'biti obična akcija ili snižena cena.',
  'keywords': ['nije pred istek', 'zasto nije rok', 'zašto nije rok', 'akcija', 'rok nije potvrđen']},
 {'question': 'Da li AI garantuje tačnost cena?',
  'answer': 'Ne. AI pomaže u pretrazi i unosu, ali cenu potvrđuje prodavac. Ako primetiš grešku, proveri kod prodavca '
            'ili prijavi problem adminu.',
  'keywords': ['ai garantuje', 'tacnost cene', 'tačnost cene', 'pogresna cena', 'pogrešna cena']},
 {'question': 'Da li AI garantuje rok trajanja?',
  'answer': 'Ne. AI ne garantuje rok trajanja. Rok potvrđuje prodavac, a kupac treba da proveri deklaraciju i stanje '
            'proizvoda Kupac dobija digitalnu kartu i kod za preuzimanje.',
  'keywords': ['ai garantuje rok', 'garancija roka', 'rok trajanja', 'deklaracija', 'sigurnost']},
 {'question': 'Kako da znam da je slika realna?',
  'answer': 'Najbolje su slike koje prodavac slika direktno kroz seller panel kamerom. Slike iz crawlera ili starih '
            'izvora treba proveriti i ne treba ih koristiti kao dokaz roka.',
  'keywords': ['slika realna', 'fotografija', 'kamera', 'slika proizvoda', 'stvarna slika']},
 {'question': 'Šta ako proizvod izgleda drugačije nego na slici?',
  'answer': 'Kod hrane slika može biti ilustrativna ili zavisiti od dnevne ponude. Pre preuzimanja proveri proizvod '
            'kod prodavca, posebno ako je korpa iznenađenja.',
  'keywords': ['drugacije nego na slici', 'drugačije', 'slika', 'izgled proizvoda', 'nije kao slika']},
 {'question': 'Da li aplikacija proverava alergene?',
  'answer': 'Ne garantujemo alergene kroz AI. Ako imaš alergiju, obavezno pitaj prodavca i proveri deklaraciju. Ne '
            'rezerviši proizvod ako nisi siguran/na u sastav.',
  'keywords': ['alergeni', 'alergija', 'gluten', 'laktoza', 'orasasti', 'sastav', 'deklaracija']},
 {'question': 'Da li mogu da tražim bez glutena?',
  'answer': 'Možeš ukucati “bez glutena”, ali AI ne sme da garantuje sastav. Proveri sa prodavcem i deklaracijom pre '
            'kupovine.',
  'keywords': ['bez glutena', 'gluten free', 'gluten', 'celijakija']},
 {'question': 'Da li mogu da tražim vegetarijansko ili posno?',
  'answer': 'Možeš pretražiti “vegetarijansko”, “posno” ili slične pojmove, ali sastav potvrđuje prodavac. Kod korpi '
            'iznenađenja obavezno pitaj šta ulazi u paket.',
  'keywords': ['vegetarijansko', 'posno', 'vegan', 'sastav', 'bez mesa']},
 {'question': 'Da li mogu da tražim burek, kifle ili hleb?',
  'answer': 'Da. Napiši naziv proizvoda, na primer “burek blizu mene”, “kifle do 150 din” ili “hleb danas”. AI će '
            'pokušati da pronađe najbliže odgovarajuće ponude.',
  'keywords': ['burek', 'kifle', 'hleb', 'pecivo', 'kroasan', 'pekara']},
 {'question': 'Kako da tražim ponude ispod određene cene?',
  'answer': 'Napiši cenu prirodno, na primer “pecivo do 200 din”, “hleb ispod 100 din” ili “najjeftinije u blizini”. '
            'AI će podesiti filter maksimalne cene.',
  'keywords': ['do 200 din', 'ispod', 'jeftino', 'cena', 'maksimalna cena', 'najjeftinije']},
 {'question': 'Kako da tražim samo velike popuste?',
  'answer': 'Napiši “najveći popusti”, “preko 30%” ili “minimum 50% popusta”. AI će sortirati ili filtrirati ponude po '
            'popustu kada podaci postoje.',
  'keywords': ['veliki popust', 'najveci popusti', 'najveći popusti', 'preko 30', '50%', 'minimum popust']},
 {'question': 'Kako da tražim ponude u određenom kraju Beograda?',
  'answer': 'Možeš napisati kraj ili opštinu, na primer “Novi Beograd”, “Vračar”, “Zemun” ili “Banovo brdo”. Ako '
            'prodavac ima lokaciju, najbolje radi pretraga preko mape i radiusa.',
  'keywords': ['novi beograd', 'vracar', 'vračar', 'zemun', 'banovo brdo', 'opstina', 'opština', 'kraj']},
 {'question': 'Da li mapa pokazuje tačnu adresu?',
  'answer': 'Mapa prikazuje lokaciju prodavca ako su koordinate unete. Kod test podataka lokacija može biti približna, '
            'a za preuzimanje uvek proveri adresu na kartici ponude.',
  'keywords': ['tacna adresa', 'tačna adresa', 'mapa', 'koordinate', 'adresa prodavca']},
 {'question': 'Zašto aplikacija traži moju lokaciju?',
  'answer': 'Lokacija se koristi da bi se prikazale najbliže ponude i udaljenost do prodavca. Možeš odbiti GPS i ručno '
            'pretraživati po gradu ili mapi.',
  'keywords': ['zasto lokacija', 'zašto lokacija', 'moja lokacija', 'gps dozvola', 'privatnost lokacije']},
 {'question': 'Da li mogu da koristim aplikaciju bez GPS-a?',
  'answer': 'Da. Možeš pretraživati po gradu, kategoriji, ceni i tekstu. GPS je koristan samo za najbliže ponude i '
            'radius.',
  'keywords': ['bez gps', 'bez lokacije', 'ne zelim lokaciju', 'ne želim lokaciju', 'manualno']},
 {'question': 'Da li aplikacija radi ako nema interneta?',
  'answer': 'Aplikacija može imati osnovni PWA prikaz, ali za sveže ponude, rezervacije, mapu i AI pretragu potreban '
            'je internet.',
  'keywords': ['offline', 'bez interneta', 'internet', 'pwa', 'ne radi mreza']},
 {'question': 'Kako se čuvaju moji podaci?',
  'answer': 'U MVP verziji čuvaju se samo podaci potrebni za rezervaciju, kao ime, telefon i kod rezervacije. Ne '
            'ne čuvaju se podaci o karticama; MVP koristi demo plaćanje, a produkcija će koristiti ovlašćenog payment providera.',
  'keywords': ['podaci', 'privatnost', 'gdpr', 'telefon', 'ime', 'kartica', 'licni podaci']},
 {'question': 'Da li čuvate podatke o kartici?',
  'answer': 'Da. Aplikacija ima online payment flow u MVP/demo režimu i ne traži podatke o kartici. U produkciji plaćanje će ići preko ovlašćenog payment providera kod '
            'prodavca.',
  'keywords': ['podaci kartice', 'kartica', 'cuvate karticu', 'čuvate karticu', 'sigurnost placanja']},
 {'question': 'Da li prodavac vidi moj telefon?',
  'answer': 'Da, telefon je deo rezervacije da bi prodavac mogao da potvrdi ili pronađe rezervaciju. Unesi samo broj '
            'koji želiš da koristiš za tu rezervaciju.',
  'keywords': ['prodavac vidi telefon', 'telefon', 'privatnost', 'moj broj', 'kontakt']},
 {'question': 'Da li mogu da naručim dostavu preko aplikacije?',
  'answer': 'Ne u ovoj verziji. Aplikacija je fokusirana na rezervaciju i lično preuzimanje kod prodavca. Dostava bi '
            'bila posebna buduća funkcija.',
  'keywords': ['narucim dostavu', 'naručim dostavu', 'dostava', 'kurir', 'donosenje']},
 {'question': 'Da li mogu da rezervišem za sutra?',
  'answer': 'Možeš ako ponuda ima rok i termin preuzimanja za sutra. Kod dnevnih viškova i pekarskih proizvoda ponude '
            'su najčešće za isti dan.',
  'keywords': ['za sutra', 'rezervisem sutra', 'rezervišem sutra', 'sutra', 'preuzimanje sutra']},
 {'question': 'Zašto je ponuda nestala?',
  'answer': 'Ponuda može nestati ako je rasprodata, istekla, sakrivena, otkazana ili ako je prodavac uklonio ponudu. '
            'Sveža hrana često ima kratko vreme dostupnosti.',
  'keywords': ['ponuda nestala', 'nema ponude', 'rasprodato', 'isteklo', 'sakrivena', 'uklonjena']},
 {'question': 'Da li mogu da podelim ponudu prijatelju?',
  'answer': 'Možeš podeliti link ponude. Ako deliš rezervaciju, ne deli kod javno jer osoba sa kodom može pokušati da '
            'preuzme rezervaciju.',
  'keywords': ['podelim', 'share', 'prijatelj', 'link ponude', 'kod javno']},
 {'question': 'Šta znači “rasprodato”?',
  'answer': 'Rasprodato znači da više nema dostupne količine za rezervaciju. Proveri kasnije ili proširi pretragu na '
            'slične ponude u blizini.',
  'keywords': ['rasprodato', 'sold out', 'nema kolicine', 'nema količine', 'dostupno']},
 {'question': 'Kako AI bira preporuke?',
  'answer': 'AI gleda tvoju poruku, filtere, cenu, kategoriju, rok, popust i lokaciju ako je dostupna. Preporuka je '
            'pomoć u pretrazi, ne garancija kvaliteta ili bezbednosti hrane.',
  'keywords': ['kako ai bira', 'preporuke', 'algoritam', 'ai preporuka', 'sortiranje']},
 {'question': 'Zašto AI nije razumeo moje pitanje?',
  'answer': 'Probaj kraće i konkretnije: proizvod + cena + lokacija, na primer “kifle do 150 din u blizini” ili “hleb '
            'danas Beograd”.',
  'keywords': ['nije razumeo', 'ai ne razume', 'pogresno', 'pogrešno', 'pretraga ne radi']},
 {'question': 'Kako da prijavim pogrešnu cenu?',
  'answer': 'U ovoj verziji prijavi problem prodavcu ili adminu. Sačuvaj naziv ponude, prodavca i, ako imaš, kod '
            'rezervacije da bi se greška lakše našla.',
  'keywords': ['pogresna cena', 'pogrešna cena', 'prijavim cenu', 'greska cena', 'greška cena']},
 {'question': 'Kako da prijavim neispravnu ili spornu hranu?',
  'answer': 'Nemoj preuzimati hranu ako deluje neispravno. Obrati se prodavcu i prijavi adminu. Kod hrane sa rokom '
            'uvek proveri deklaraciju, izgled, miris i uslove čuvanja.',
  'keywords': ['neispravna hrana', 'sporna hrana', 'pokvareno', 'loš miris', 'los miris', 'prijava hrane']},
 {'question': 'Da li mogu da ocenim prodavca?',
  'answer': 'Ocenjivanje prodavaca nije uključeno u ovu verziju, ali je dobra buduća funkcija. Za sada problem možeš '
            'prijaviti prodavcu ili adminu.',
  'keywords': ['ocena prodavca', 'review', 'recenzija', 'rating', 'ocenim']},
 {'question': 'Da li mogu da dobijam obaveštenja?',
  'answer': 'Obaveštenja nisu još završena. Za sada proveravaj aplikaciju ručno ili sačuvaj link. Kasnije možemo '
            'dodati push notifikacije za omiljene pekare i ponude blizu tebe.',
  'keywords': ['obavestenja', 'obaveštenja', 'notifikacije', 'push', 'sms', 'email']},
 {'question': 'Da li aplikacija šalje SMS?',
  'answer': 'Ne u ovoj verziji. Telefon se koristi za rezervaciju i kontakt prodavca, ali aplikacija ne šalje '
            'automatski SMS potvrde.',
  'keywords': ['sms', 'poruka', 'potvrda sms', 'telefon poruka']},
 {'question': 'Da li mogu da koristim aplikaciju iz drugog grada?',
  'answer': 'Možeš, ali početni fokus je Beograd i pekare. Kako se baza bude širila, dodaćemo druge gradove i '
            'kategorije hrane.',
  'keywords': ['drugi grad', 'novi sad', 'nis', 'niš', 'kragujevac', 'subotica', 'srbija']},
 {'question': 'Zašto je baza mala?',
  'answer': 'Baza raste postepeno. Najkvalitetnije ponude dolaze direktno od prodavaca jer imaju tačnu cenu, sliku, '
            'količinu, rok i termin preuzimanja.',
  'keywords': ['mala baza', 'nema mnogo ponuda', 'baza', 'ponude', 'prodavci']},
 {'question': 'Kako prodavac može da se uključi?',
  'answer': 'Prodavac dobija svoj PIN i seller panel. Tu može brzo da slika proizvod, unese cenu, količinu, rok i '
            'vreme preuzimanja, pa objavi ponudu.',
  'keywords': ['prodavac se ukljuci', 'prodavac se uključi', 'seller panel', 'pin', 'dodavanje prodavca']},
 {'question': 'Da li prodavac može da postavi dnevni višak hrane?',
  'answer': 'Da. Prodavac može objaviti dnevni višak, korpu iznenađenja ili konkretan proizvod. Bitno je da navede '
            'količinu, cenu i vreme preuzimanja.',
  'keywords': ['dnevni visak', 'dnevni višak', 'višak hrane', 'korpa', 'prodavac objavi']},
 {'question': 'Da li ponuda mora imati sliku?',
  'answer': 'Za profesionalnu bazu cilj je da svaka realna ponuda ima sliku. Slika povećava poverenje kupca, posebno '
            'za pekarske proizvode i korpe iznenađenja.',
  'keywords': ['mora slika', 'slika obavezna', 'fotografija', 'bez slike', 'proizvod sa slikom']},
 {'question': 'Šta je najbolje da prodavac slika?',
  'answer': 'Najbolje je da slika stvarni proizvod ili grupu proizvoda koja se prodaje tog dana, uz jasnu cenu i '
            'količinu u opisu. Ne treba koristiti generičke slike ako proizvod izgleda drugačije.',
  'keywords': ['prodavac slika', 'sta slikati', 'šta slikati', 'kamera', 'fotografija proizvoda']},
 {'question': 'Da li mogu da rezervišem bez slike proizvoda?',
  'answer': 'Možeš ako je ponuda aktivna, ali preporuka je da prednost daš ponudama sa jasnom slikom, cenom, količinom '
            'i vremenom preuzimanja.',
  'keywords': ['bez slike rezervisem', 'bez slike', 'ponuda bez slike', 'rezervacija bez slike']}]

DEFAULT_KNOWLEDGE: dict[str, Any] = {
    "assistant_name": "Sačuvaj Hranu AI",
    "tone": "prijateljski, kratak, praktičan i siguran; govori srpski latinicom; jasno objašnjava online plaćanje kroz aplikaciju, demo režim, loyalty popust i 25% proviziju platforme; ne obećava rok trajanja bez potvrde prodavca",
    "business_rules": ['Nikada ne tvrdi da je artikal pred istekom roka ako status nije near_expiry ili ako rok nije potvrđen.',
 'Za public_discount reci da je to akcijska/snižena cena iz javnog izvora ili ponuda bez potvrđenog kraćeg roka.',
 'Kod rezervacije je dokaz za preuzimanje. Kupac treba da sačuva kod i dođe u terminu preuzimanja.',
 'Ako nema rezultata, predloži širi radius, uklanjanje roka ili prikaz svih pekarskih ponuda.',
 'Ne daje medicinske ili pravne garancije bezbednosti hrane. Rok i uslove prodaje potvrđuje prodavac.',
 'Aplikacija podržava online payment flow. U MVP verziji plaćanje je demo bez stvarne kartice; u produkciji ide preko payment providera. '
 'Kupac dobija digitalnu kartu i kod za preuzimanje.',
 'Nikada ne traži broj kartice direktno u chatu ili formi. U produkciji karticu sme obrađivati samo ovlašćeni payment provider.',
 'Ako korisnik pita za plaćanje, objasni da posle rezervacije plaća online kroz aplikaciju, dobija digitalnu kartu, a platforma zadržava 25% od plaćenog iznosa.',
 'Odgovaraj kao korisnički asistent: prvo daj direktan odgovor, zatim jedan praktičan sledeći korak.',
 'Kada korisnik pita za bezbednost, rok ili alergene, budi oprezan i uputi ga da proveri deklaraciju i prodavca.',
 'Kada korisnik traži ponude, pokušaj da pretvoriš poruku u filtere: kategorija, cena, grad, radius, rok i popust.'],
    "faqs": EXPANDED_FAQS,
    "quick_replies": ['Šta ima blizu mene?',
 'Pekara do 200 din',
 'Kako radi rezervacija?',
 'Kako se plaća online?',
 'Šta znači pred istek?',
 'Najveći popusti',
 'Rok danas',
 'Da li je hrana bezbedna?',
 'Zašto GPS ne radi?',
 'Kako da otkažem?'],
}

def load_knowledge() -> dict[str, Any]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not KNOWLEDGE_PATH.exists():
        KNOWLEDGE_PATH.write_text(json.dumps(DEFAULT_KNOWLEDGE, ensure_ascii=False, indent=2), encoding="utf-8")
        return DEFAULT_KNOWLEDGE.copy()
    try:
        data = json.loads(KNOWLEDGE_PATH.read_text(encoding="utf-8"))
        merged = DEFAULT_KNOWLEDGE.copy()
        merged.update(data if isinstance(data, dict) else {})
        if not isinstance(merged.get("faqs"), list):
            merged["faqs"] = DEFAULT_KNOWLEDGE["faqs"]
        if not isinstance(merged.get("business_rules"), list):
            merged["business_rules"] = DEFAULT_KNOWLEDGE["business_rules"]
        return merged
    except Exception:
        return DEFAULT_KNOWLEDGE.copy()


def save_knowledge(data: dict[str, Any]) -> dict[str, Any]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    cleaned = {
        "assistant_name": str(data.get("assistant_name") or "Sačuvaj Hranu AI")[:80],
        "tone": str(data.get("tone") or DEFAULT_KNOWLEDGE["tone"])[:800],
        "business_rules": [str(x).strip()[:700] for x in data.get("business_rules", []) if str(x).strip()][:30],
        "faqs": [],
        "quick_replies": [str(x).strip()[:60] for x in data.get("quick_replies", []) if str(x).strip()][:10],
    }
    for item in data.get("faqs", []):
        if not isinstance(item, dict):
            continue
        q = str(item.get("question") or "").strip()[:300]
        a = str(item.get("answer") or "").strip()[:1200]
        keywords = item.get("keywords") or []
        if isinstance(keywords, str):
            keywords = [x.strip() for x in keywords.split(",")]
        keywords = [str(x).strip()[:60] for x in keywords if str(x).strip()][:12]
        if q and a:
            cleaned["faqs"].append({"question": q, "answer": a, "keywords": keywords})
    if not cleaned["business_rules"]:
        cleaned["business_rules"] = DEFAULT_KNOWLEDGE["business_rules"]
    if not cleaned["quick_replies"]:
        cleaned["quick_replies"] = DEFAULT_KNOWLEDGE["quick_replies"]
    KNOWLEDGE_PATH.write_text(json.dumps(cleaned, ensure_ascii=False, indent=2), encoding="utf-8")
    return cleaned


def match_custom_faq(message: str, knowledge: dict[str, Any]) -> dict[str, Any] | None:
    text = normalize(message)
    best: tuple[int, dict[str, Any]] | None = None
    for faq in knowledge.get("faqs", []):
        score = 0
        q = normalize(str(faq.get("question", "")))
        if q and (q in text or text in q):
            score += 8
        for kw in faq.get("keywords", []):
            nkw = normalize(str(kw))
            if not nkw:
                continue
            if nkw in text:
                score += 4 if " " in nkw else 2
        # simple token overlap with the question
        q_tokens = set(re.findall(r"[a-z0-9]{4,}", q))
        t_tokens = set(re.findall(r"[a-z0-9]{4,}", text))
        score += len(q_tokens & t_tokens)
        if score >= 3 and (best is None or score > best[0]):
            best = (score, faq)
    return best[1] if best else None

router = APIRouter(prefix="/buyer-ai", tags=["buyer-ai"])


class BuyerAIRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1200)
    lat: float | None = Field(default=None, ge=-90, le=90)
    lng: float | None = Field(default=None, ge=-180, le=180)
    radius_km: float | None = Field(default=None, ge=0.1, le=500)
    city: str | None = None
    limit: int = Field(default=8, ge=1, le=20)


class BuyerAIResponse(BaseModel):
    reply: str
    intent: str
    filters: dict[str, Any]
    products: list[dict[str, Any]] = []
    quick_replies: list[str] = []
    tips: list[str] = []


class KnowledgeFAQ(BaseModel):
    question: str
    answer: str
    keywords: list[str] = []


class BuyerAIKnowledge(BaseModel):
    assistant_name: str = "Sačuvaj Hranu AI"
    tone: str = ""
    business_rules: list[str] = []
    faqs: list[KnowledgeFAQ] = []
    quick_replies: list[str] = []


CATEGORY_KEYWORDS = {
    "pekara": ["hleb", "hljeb", "kifla", "kifle", "pecivo", "peciva", "burek", "pita", "kroasan", "kroasani", "baget", "projara", "pogač", "pogac", "sendvič", "sendvic", "đevrek", "djevrek", "lepinja", "somun", "lisnato", "pekara", "pekarski", "pogačica", "pogacica"],
    "restoran": ["restoran", "ručak", "rucak", "večera", "vecera", "obrok", "meni", "porcija", "gotovo", "kuvano", "jelo", "jela", "dnevni meni", "kuhinja"],
    "market": ["market", "prodavnica", "supermarket", "minimarket", "namirnice", "katalog", "akcija", "artikli"],
    "mlečni proizvodi": ["mleko", "mlijeko", "jogurt", "sir", "kajmak", "pavlaka", "kiselo mleko", "mlečni", "mlecni", "namaz"],
    "voće i povrće": ["voće", "voce", "povrće", "povrce", "jabuka", "banana", "paradajz", "krastavac", "salata", "krompir", "luk", "šargarepa", "sargarepa", "piljara"],
    "mesara": ["mesara", "meso", "piletina", "svinjsko", "junetina", "ćevapi", "cevapi", "kobasica", "šunka", "sunka", "pršuta", "prsuta"],
    "ribarnica": ["riba", "ribarnica", "losos", "pastrmka", "oslić", "oslic", "tuna", "morski plodovi"],
    "poslastice": ["kolač", "kolac", "torta", "slatko", "mafini", "mafin", "čokolada", "cokolada", "krofna", "krofne", "poslastičarnica", "poslasticarnica", "palačinke", "palacinke"],
    "gotova jela": ["gotova jela", "kuvana jela", "ručak", "rucak", "porcija", "pasulj", "sarma", "gulaš", "gulas", "pasta", "rižoto", "rizoto"],
    "zdrava hrana": ["zdrava hrana", "integralno", "bez glutena", "vegan", "vegetarijansko", "proteinsko", "bio", "organsko"],
    "delikates": ["delikates", "salama", "sir", "namaz", "masline", "pršuta", "prsuta", "kulen"],
    "pića": ["piće", "pice", "sok", "voda", "limunada", "kafa", "čaj", "caj", "napitak"],
    "smrznuta hrana": ["smrznuto", "zamrznuto", "sladoled", "smrznuta hrana", "frozen"],
    "sendviči": ["sendvič", "sendvic", "tost", "tortilja", "wrap", "panini"],
    "salate": ["salata", "salate", "obrok salata", "cezar", "caesar"],
    "kafa i doručak": ["kafa", "doručak", "dorucak", "espresso", "kapućino", "kapucino", "jutarnje"],
    "korpa iznenađenja": ["korpa", "korpa iznenađenja", "korpa iznenadjenja", "surprise", "paket", "misteriozna"],
}

STOP_WORDS = {
    "sta", "šta", "ima", "imate", "trazim", "tražim", "nadji", "nađi", "mi", "molim", "treba", "zelim", "želim",
    "nesto", "nešto", "najbolje", "ponude", "ponuda", "hrana", "hrane", "u", "na", "za", "od", "do", "oko", "blizu",
    "mene", "mogu", "moze", "može", "daj", "prikazi", "prikaži", "pokazi", "pokaži", "jeftino", "jeftine",
}


def strip_accents(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def normalize(text: str) -> str:
    return strip_accents(text.lower()).replace("đ", "dj")


def parse_money(text: str) -> float | None:
    normalized = normalize(text).replace(".", "")
    patterns = [
        r"(?:do|ispod|max|maksimum|najvise|najvise do)\s*(\d{2,5})(?:\s*(?:din|rsd|dindzi))?",
        r"(\d{2,5})\s*(?:din|rsd)\s*(?:ili manje|najvise|max|maks)",
    ]
    for pattern in patterns:
        match = re.search(pattern, normalized)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                return None
    return None


def parse_filters(message: str, lat: float | None = None, lng: float | None = None, radius_km: float | None = None, city: str | None = None) -> dict[str, Any]:
    raw = message.strip()
    text = normalize(raw)
    filters: dict[str, Any] = {
        "q": "",
        "category": "",
        "status": "",
        "min_discount": None,
        "max_price": parse_money(raw),
        "expiring_days": None,
        "sort": "updated",
        "radius_km": radius_km,
        "city": city or "",
        "district": "",
        "has_image": None,
    }

    for category, words in CATEGORY_KEYWORDS.items():
        if any(normalize(w) in text for w in words):
            filters["category"] = category
            break

    if any(phrase in text for phrase in ["pred istek", "istice", "istice rok", "kraci rok", "kraceg roka", "rok danas", "rok sutra"]):
        filters["status"] = "near_expiry"
        filters["sort"] = "expiry_asc"
    elif any(phrase in text for phrase in ["akcija", "akcijs", "snizen", "popust"]):
        filters["sort"] = "discount_desc"

    if "danas" in text:
        filters["expiring_days"] = 0
        if "rok" in text or "ist" in text:
            filters["status"] = filters["status"] or "near_expiry"
            filters["sort"] = "expiry_asc"
    elif "sutra" in text:
        filters["expiring_days"] = 1
    else:
        days_match = re.search(r"(?:u\s*)?(\d{1,2})\s*dana", text)
        if days_match and ("rok" in text or "ist" in text):
            filters["expiring_days"] = int(days_match.group(1))

    discount_match = re.search(r"(?:bar|min|minimum|preko|vise od|više od)?\s*(\d{1,2})\s*%", text)
    if discount_match:
        filters["min_discount"] = float(discount_match.group(1))
        filters["sort"] = "discount_desc"
    elif "veliki popust" in text or "najveci popust" in text or "najveći popust" in raw.lower():
        filters["min_discount"] = 30
        filters["sort"] = "discount_desc"

    radius_match = re.search(r"(\d{1,3})\s*km", text)
    if radius_match:
        filters["radius_km"] = float(radius_match.group(1))
        filters["sort"] = "distance_asc"
    elif any(word in text for word in ["blizu", "najblize", "najbliže", "u blizini", "oko mene"]):
        filters["radius_km"] = filters["radius_km"] or 5
        filters["sort"] = "distance_asc"

    if any(word in text for word in ["najjeftin", "jeftino", "najmanja cena", "najniža cena", "najniza cena"]):
        filters["sort"] = "price_asc"

    city_map = {
        "beograd": "Beograd", "bg": "Beograd", "novi sad": "Novi Sad", "ns": "Novi Sad",
        "nis": "Niš", "niš": "Niš", "kragujevac": "Kragujevac", "subotica": "Subotica",
        "zrenjanin": "Zrenjanin", "pancevo": "Pančevo", "pančevo": "Pančevo", "cacak": "Čačak", "čacak": "Čačak",
        "kraljevo": "Kraljevo", "novi pazar": "Novi Pazar", "smederevo": "Smederevo", "leskovac": "Leskovac",
        "valjevo": "Valjevo", "krusevac": "Kruševac", "kruševac": "Kruševac", "vranje": "Vranje",
        "sabac": "Šabac", "šabac": "Šabac", "sombor": "Sombor", "kikinda": "Kikinda", "uzice": "Užice", "užice": "Užice",
        "pozarevac": "Požarevac", "požarevac": "Požarevac", "pirot": "Pirot", "zajecar": "Zaječar", "zaječar": "Zaječar",
        "jagodina": "Jagodina", "loznica": "Loznica", "prokuplje": "Prokuplje", "sremska mitrovica": "Sremska Mitrovica",
        "ruma": "Ruma", "indjija": "Inđija", "inđija": "Inđija", "stara pazova": "Stara Pazova",
        "zemun": "Beograd", "vracar": "Beograd", "vračar": "Beograd", "novi beograd": "Beograd", "banovo brdo": "Beograd",
        "dorcol": "Beograd", "dorćol": "Beograd", "zvezdara": "Beograd", "palilula": "Beograd", "vozdovac": "Beograd", "voždovac": "Beograd",
        "cukarica": "Beograd", "čukarica": "Beograd", "rakovica": "Beograd", "mirijevo": "Beograd", "karaburma": "Beograd",
    }
    for key, value in city_map.items():
        if key in text:
            filters["city"] = value
            break

    # Opštine/naselja: ostavljamo grad Beograd, ali dodatno filtriramo po adresi/nazivu lokacije.
    for district in BELGRADE_DISTRICTS:
        nd = normalize(district)
        if nd and nd in text:
            filters["city"] = "Beograd"
            filters["district"] = district
            break

    if any(x in text for x in ["sa slikom", "samo sa slikom", "fotografijom", "slika obavezna", "imaju sliku"]):
        filters["has_image"] = True

    # Build a gentle keyword query only from likely product words, not from command words.
    tokens = [t for t in re.findall(r"[a-zA-ZčćžšđČĆŽŠĐ0-9]+", raw.lower()) if len(t) > 2]
    normalized_stop = {normalize(w) for w in STOP_WORDS}
    generic_category_words = {"pekara", "pekare", "restoran", "restorani", "market", "prodavnica", "prodavnice", "mesara", "ribarnica", "poslastice", "hrana"}
    product_tokens = []
    for token in tokens:
        nt = normalize(token)
        if nt in normalized_stop or nt.isdigit() or nt in {"din", "rsd", "kom", "km", "rok", "dana", "danas", "sutra"}:
            continue
        if any(nt in normalize(w) or normalize(w) in nt for words in CATEGORY_KEYWORDS.values() for w in words):
            if nt not in generic_category_words:
                product_tokens.append(token)
    if product_tokens:
        filters["q"] = " ".join(product_tokens[:3])

    if lat is not None and lng is not None:
        filters["lat"] = lat
        filters["lng"] = lng
    return filters


def detect_intent(message: str) -> str:
    text = normalize(message)
    if any(x in text for x in ["kako", "sta znaci", "šta znači", "objasni", "rok", "rezervis"]):
        if any(x in text for x in ["rezervis", "kod", "preuzim"]):
            return "help_reservation"
        if "rok" in text or "istek" in text or "upotreb" in text:
            return "help_expiry"
    return "search"


def query_products(db: Session, filters: dict[str, Any], limit: int) -> list[dict[str, Any]]:
    query = db.query(models.Product).outerjoin(models.Store).filter(models.Product.status.in_(VISIBLE_STATUSES))
    if filters.get("city"):
        query = query.filter(models.Store.city.ilike(f"%{filters['city']}%"))
    if filters.get("district"):
        needle = f"%{filters['district']}%"
        query = query.filter(or_(models.Store.city.ilike(needle), models.Store.address.ilike(needle), models.Store.name.ilike(needle)))
    if filters.get("category"):
        query = query.filter(models.Product.category.ilike(f"%{filters['category']}%"))
    if filters.get("status"):
        query = query.filter(models.Product.status == filters["status"])
    if filters.get("q"):
        needle = f"%{filters['q']}%"
        query = query.filter(or_(models.Product.name.ilike(needle), models.Store.name.ilike(needle)))
    if filters.get("min_discount") is not None:
        query = query.filter(models.Product.discount_percent.is_not(None), models.Product.discount_percent >= float(filters["min_discount"]))
    if filters.get("max_price") is not None:
        query = query.filter(models.Product.discounted_price.is_not(None), models.Product.discounted_price <= float(filters["max_price"]))
    if filters.get("expiring_days") is not None:
        end_date = date.today() + timedelta(days=max(int(filters["expiring_days"]), 0))
        query = query.filter(models.Product.expiry_date.is_not(None), models.Product.expiry_date <= end_date)
    if filters.get("has_image") is True:
        query = query.filter(models.Product.image_url.is_not(None), models.Product.image_url != "")

    sort = filters.get("sort") or "updated"
    if sort == "discount_desc":
        query = query.order_by(models.Product.discount_percent.desc().nullslast(), models.Product.updated_at.desc())
    elif sort == "price_asc":
        query = query.order_by(models.Product.discounted_price.asc().nullslast(), models.Product.updated_at.desc())
    elif sort == "expiry_asc":
        query = query.order_by(models.Product.expiry_date.asc().nullslast(), models.Product.updated_at.desc())
    else:
        query = query.order_by(models.Product.updated_at.desc())

    products = [product_to_public(db, p, lat=filters.get("lat"), lng=filters.get("lng")) for p in query.limit(120).all()]
    radius = filters.get("radius_km")
    if filters.get("lat") is not None and filters.get("lng") is not None and radius:
        products = [p for p in products if p.get("distance_km") is not None and p["distance_km"] <= float(radius)]
        if sort == "distance_asc":
            products.sort(key=lambda p: p["distance_km"] if p.get("distance_km") is not None else 10**9)
    # Hide sold out products.
    products = [p for p in products if p.get("available_quantity") is None or p.get("available_quantity", 0) > 0]
    return products[:limit]


def build_reply(intent: str, message: str, filters: dict[str, Any], products: list[dict[str, Any]], knowledge: dict[str, Any] | None = None) -> tuple[str, list[str], list[str]]:
    knowledge = knowledge or load_knowledge()
    quick_defaults = knowledge.get("quick_replies") or DEFAULT_KNOWLEDGE["quick_replies"]
    if intent == "help_reservation":
        return (
            "Rezervacija je jednostavna: izaberi ponudu, klikni Rezerviši, upiši ime i telefon, zatim plati online kroz aplikaciju. Dobićeš digitalnu kartu i kod koji pokazuješ prodavcu pri preuzimanju.",
            ["Prikaži najbliže ponude", "Pokaži pekarske proizvode", "Šta je pred istek roka?"],
            ["U MVP verziji plaćanje je demo/sandbox i ne unosi se stvarna kartica. Produkcija treba payment providera."],
        )
    if intent == "help_expiry":
        return (
            "U aplikaciji razlikujemo običnu akcijsku cenu i artikle pred istekom roka. Oznaka ‘Pred istek’ treba da se koristi samo kada prodavac potvrdi rok. Ako rok nije potvrđen, ponuda se tretira kao akcijska ili potvrđena ponuda prodavca.",
            ["Pokaži samo pred istek", "Pokaži rok danas", "Najveći popusti"],
            ["Za hranu sa oznakom ‘upotrebljivo do’ treba biti posebno oprezan; aplikacija ne sme sama da tvrdi rok bez potvrde prodavca."],
        )

    if products:
        names = ", ".join(p["name"] for p in products[:3])
        parts = [f"Našao sam {len(products)} relevantnih ponuda. Prve koje bih pogledao: {names}."]
        if filters.get("radius_km"):
            parts.append(f"Uključio sam blizinu do {filters['radius_km']} km.")
        if filters.get("max_price"):
            parts.append(f"Filtrirao sam do {int(filters['max_price'])} RSD.")
        if filters.get("category"):
            parts.append(f"Kategorija: {filters['category']}.")
        if filters.get("district"):
            parts.append(f"Lokacija/naselje: {filters['district']}.")
        if filters.get("has_image"):
            parts.append("Prikazujem samo ponude sa slikom.")
        return (
            " ".join(parts),
            ["Najbliže meni", "Najveći popust", "Pekara do 200 din", "Rok danas"],
            ["Klikni na karticu ili mapu za detalje, pa rezerviši samo količinu koju sigurno preuzimaš."],
        )
    return (
        "Nisam našao ponude koje tačno odgovaraju tome. Mogu da proširim pretragu: ukloniću rok, povećati radius ili prikazati sve pekarske ponude.",
        ["Pokaži sve ponude", "Pekara Beograd", "Najveći popusti", "U blizini 10 km"],
        ["Ako baza još nema mnogo realnih proizvoda, dodaj test ponude kroz seller/admin panel da bi korisnički AI imao šta da preporuči."],
    )


@router.get("/knowledge", response_model=BuyerAIKnowledge, dependencies=[Depends(require_admin_session)])
def get_buyer_ai_knowledge():
    return load_knowledge()


@router.post("/knowledge", response_model=BuyerAIKnowledge, dependencies=[Depends(require_admin_session)])
def update_buyer_ai_knowledge(payload: BuyerAIKnowledge):
    return save_knowledge(payload.model_dump())


@router.post("/knowledge/reset", response_model=BuyerAIKnowledge, dependencies=[Depends(require_admin_session)])
def reset_buyer_ai_knowledge():
    if KNOWLEDGE_PATH.exists():
        KNOWLEDGE_PATH.unlink()
    return load_knowledge()


@router.post("/knowledge/seed-expanded", response_model=BuyerAIKnowledge, dependencies=[Depends(require_admin_session)])
def seed_expanded_buyer_ai_knowledge():
    current = load_knowledge()
    existing_questions = {normalize(str(item.get("question", ""))) for item in current.get("faqs", []) if isinstance(item, dict)}
    merged_faqs = list(current.get("faqs", []))
    for faq in EXPANDED_FAQS:
        key = normalize(str(faq.get("question", "")))
        if key and key not in existing_questions:
            merged_faqs.append(faq)
            existing_questions.add(key)
    current["faqs"] = merged_faqs

    rules = list(current.get("business_rules") or [])
    for rule in DEFAULT_KNOWLEDGE["business_rules"]:
        if rule not in rules:
            rules.append(rule)
    current["business_rules"] = rules

    quick = list(current.get("quick_replies") or [])
    for item in DEFAULT_KNOWLEDGE["quick_replies"]:
        if item not in quick:
            quick.append(item)
    current["quick_replies"] = quick[:10]
    return save_knowledge(current)


@router.post("/chat", response_model=BuyerAIResponse)
def buyer_ai_chat(payload: BuyerAIRequest, db: Session = Depends(get_db)):
    knowledge = load_knowledge()
    filters = parse_filters(payload.message, lat=payload.lat, lng=payload.lng, radius_km=payload.radius_km, city=payload.city)
    faq = match_custom_faq(payload.message, knowledge)
    if faq:
        return BuyerAIResponse(
            reply=str(faq.get("answer") or ""),
            intent="knowledge",
            filters=filters,
            products=[],
            quick_replies=knowledge.get("quick_replies") or DEFAULT_KNOWLEDGE["quick_replies"],
            tips=["Odgovor je uzet iz AI trening baze. Možeš ga promeniti u AI trening panelu."],
        )
    intent = detect_intent(payload.message)
    products = [] if intent.startswith("help_") else query_products(db, filters, payload.limit)
    reply, quick_replies, tips = build_reply(intent, payload.message, filters, products, knowledge)
    return BuyerAIResponse(reply=reply, intent=intent, filters=filters, products=products, quick_replies=quick_replies, tips=tips)


@router.post("/parse", response_model=BuyerAIResponse)
def buyer_ai_parse(payload: BuyerAIRequest, db: Session = Depends(get_db)):
    knowledge = load_knowledge()
    filters = parse_filters(payload.message, lat=payload.lat, lng=payload.lng, radius_km=payload.radius_km, city=payload.city)
    products = query_products(db, filters, payload.limit)
    reply, quick_replies, tips = build_reply("search", payload.message, filters, products, knowledge)
    return BuyerAIResponse(reply=reply, intent="search", filters=filters, products=products, quick_replies=quick_replies, tips=tips)
