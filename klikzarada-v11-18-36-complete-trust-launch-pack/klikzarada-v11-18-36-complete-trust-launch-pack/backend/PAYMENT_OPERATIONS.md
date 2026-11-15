# Uplate i isplate: operativni postupak

Ovo je kontrolisan, **ručni bankarski tok**, a ne direktna integracija sa Raiffeisen bankom. Interni saldo oglašivača nije bankovni račun korisnika. Nijedna CSV datoteka iz ovog izdanja nije format za automatski uvoz naloga u banku.

## Računi firme se unose naknadno

Admin na `/admin/system-settings` može ostaviti oba bankarska toka prazna. Za svaki tok unosi par: dinarski račun firme od 18 cifara i tačan naziv primaoca/firme. Nije dozvoljen samo jedan od tih podataka. Dok par za uplate nedostaje, veb i mobilna aplikacija ne izdaju instrukcije za bankarsku uplatu i ne kreiraju zahtev. Dok par za isplate nedostaje, korisnik može da pripremi svoj račun, ali ne može zatražiti bankarsku isplatu. PayPal podaci i zahtevi ostaju odvojeni i nastavljaju da rade.

## Uplata oglašivača

1. Oglašivač otvara zahtev za uplatu sa iznosom i jedinstvenom referencom na vebu ili u mobilnoj aplikaciji. Referencu koristi pri nalogu za uplatu; sam zahtev nije potvrda da je novac primljen.
2. Firma proverava prijem novca na svom poslovnom računu u zvaničnom bankarskom izvodu. Ime uplatioca, poziv na broj/referenca i tačan RSD iznos moraju da odgovaraju zahtevu. Ne potvrđivati na osnovu slike uplatnice ili tvrdnje korisnika.
3. Admin u `/admin/payments-v8` za bankarski zahtev upisuje referencu bankarske transakcije i iznos sa izvoda. Aplikacija dozvoljava jednu potvrdu po zahtevu i jednu po bankarskoj referenci. Tek tada se dopunjava oglašivački budžet.
4. Stare direktne admin dopune budžeta su isključene. Kartice potvrđuje samo konfigurisan i proverljiv procesor; generički webhook ne sme se uključiti kao zamena za ugovorenu, potpisanu integraciju.

## Isplata korisnika

1. Korisnik unosi dinarski račun od 18 cifara, koji dobija status `pending`. Admin ga proverava u postojećem payout panelu i tek onda označava `verified`. Sajt i aplikacija prikazuju samo poslednje četiri cifre; PayPal adresa se ne briše.
2. Zahtev za bankarsku isplatu koristi isključivo poslednji potvrđeni račun iz baze, a ne račun iz teksta zahteva. Rezerviše raspoloživi saldo. Admin proverava identitet, pravo na nagradu i signal rizika.
3. CSV iz `/admin/payouts-v11/export` je **spisak za proveru**, ne bankarski nalog. U njemu su samo podobni zahtevi za bankarski transfer.
4. Firma naloge izvršava u banci po ugovorenoj proceduri. Status `paid` se postavlja tek kada banka potvrdi izvršenje; admin unosi jedinstvenu bankarsku referencu. Aplikacija ne šalje novac sama.
5. Odbijen zahtev vraća rezervisani iznos korisniku. PayPal zahtevi ostaju na odvojenom, postojećem PayPal toku dok se ne dogovori migracija korisnika.

## Pre produkcione upotrebe

- Od banke pribaviti ponudu/ugovor za internet prihvat uplata, specifikaciju webhook potpisa i izvoz izvoda, te odvojenu specifikaciju za masovne isplate ako je dostupna. Ne unositi ključeve u repozitorijum.
- Sa knjigovođom i pravnikom potvrditi izdavanje računa/faktura, poreski tretman nagrada, prag isplate, identifikaciju primalaca, rokove čuvanja i način knjiženja agregiranih isplata. Ovaj kod to ne rešava sam.
- Potvrditi koji načini plaćanja i modeli nagrada su dozvoljeni za Android/iOS i uskladiti store deklaracije sa stvarnim funkcijama aplikacije.
- Testirati stvaran izvod i jednu kontrolisanu uplatu/isplatu u staging okruženju pre aktiviranja toka za korisnike. Dok to nije urađeno, ne tvrditi da je bankarski sistem automatski ili spreman za javni rad.

Regresiona provera: `python scripts/payment_controls_audit_v11875.py` iz direktorijuma `backend`.
Za verziju 11.18.76: `python scripts/bank_setup_audit_v11876.py` iz direktorijuma `backend`.
