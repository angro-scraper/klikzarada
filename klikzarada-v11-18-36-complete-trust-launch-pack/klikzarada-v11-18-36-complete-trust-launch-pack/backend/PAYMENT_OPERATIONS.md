# Uplate i isplate: operativni postupak

Ovo je kontrolisan, **ručni bankarski tok**, a ne direktna integracija sa Raiffeisen bankom. Interni saldo oglašivača nije bankovni račun korisnika. Nijedna CSV datoteka iz ovog izdanja nije format za automatski uvoz naloga u banku.

## Uplata oglašivača

1. Oglašivač otvara zahtev za uplatu sa iznosom i jedinstvenom referencom.
2. Firma proverava prijem novca na svom poslovnom računu u zvaničnom bankarskom izvodu. Ime uplatioca, poziv na broj/referenca i tačan RSD iznos moraju da odgovaraju zahtevu. Ne potvrđivati na osnovu slike uplatnice ili tvrdnje korisnika.
3. Admin u `/admin/payments-v8` za bankarski zahtev upisuje referencu bankarske transakcije i iznos sa izvoda. Aplikacija dozvoljava jednu potvrdu po zahtevu i jednu po bankarskoj referenci. Tek tada se dopunjava oglašivački budžet.
4. Stare direktne admin dopune budžeta su isključene. Kartice potvrđuje samo konfigurisan i proverljiv procesor; generički webhook ne sme se uključiti kao zamena za ugovorenu, potpisanu integraciju.

## Isplata korisnika

1. Zahtev rezerviše raspoloživi saldo. Admin proverava identitet, pravo na nagradu, signal rizika i potvrđeni bankovni račun korisnika.
2. CSV iz `/admin/payouts-v11/export` je **spisak za proveru**, ne bankarski nalog. U njemu su samo podobni zahtevi za bankarski transfer.
3. Firma naloge izvršava u banci po ugovorenoj proceduri. Status `paid` se postavlja tek kada banka potvrdi izvršenje; admin unosi jedinstvenu bankarsku referencu. Aplikacija ne šalje novac sama.
4. Odbijen zahtev vraća rezervisani iznos korisniku. PayPal zahtevi ostaju na odvojenom, postojećem PayPal toku dok se ne dogovori migracija korisnika.

## Pre produkcione upotrebe

- Od banke pribaviti ponudu/ugovor za internet prihvat uplata, specifikaciju webhook potpisa i izvoz izvoda, te odvojenu specifikaciju za masovne isplate ako je dostupna. Ne unositi ključeve u repozitorijum.
- Sa knjigovođom i pravnikom potvrditi izdavanje računa/faktura, poreski tretman nagrada, prag isplate, identifikaciju primalaca, rokove čuvanja i način knjiženja agregiranih isplata. Ovaj kod to ne rešava sam.
- Potvrditi koji načini plaćanja i modeli nagrada su dozvoljeni za Android/iOS i uskladiti store deklaracije sa stvarnim funkcijama aplikacije.
- Testirati stvaran izvod i jednu kontrolisanu uplatu/isplatu u staging okruženju pre aktiviranja toka za korisnike. Dok to nije urađeno, ne tvrditi da je bankarski sistem automatski ili spreman za javni rad.

Regresiona provera: `python scripts/payment_controls_audit_v11875.py` iz direktorijuma `backend`.
