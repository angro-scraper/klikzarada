# KlikZarada Project Instructions

## Jezik
Sve izmene, UI tekstovi, komentari za korisnika i admin tekstovi treba da budu na srpskom latinicom.

## Najvažnije pravilo
Početna stranica je zaključana i ne sme se menjati bez izričitog zahteva.
Ne menjati dizajn početne, home.html, promo banner red, hero sekcije, footer i vizuelni stil početne osim ako korisnik direktno kaže da se početna menja.

## Trenutna stabilna baza
KlikZarada V11.18.36 Complete Trust Launch Pack.

## Pokretanje projekta

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Lokalni URL:
http://127.0.0.1:8000

## Audit

Najnoviji kompletni audit:

```powershell
cd backend
python scripts\complete_trust_launch_pack_audit_v11836.py
```

## Pravila za dalji razvoj

1. Ne dirati početnu stranicu.
2. Raditi funkcionalne update-e kao nove verzije.
3. Svaki update treba da ima:
   - novu verziju u FastAPI title/version
   - novi audit script
   - proveru Python syntax
   - proveru startup
   - jasan report šta je promenjeno
4. Ne brisati postojeće rute bez potrebe.
5. Ako postoji stari endpoint, bolje ga ojačati kompatibilno nego ga ukloniti.
6. Ne kvariti postojeći workflow:
   - korisnik
   - oglašivač
   - admin
   - kampanje
   - dokazi
   - isplate
   - budžeti
   - finance
   - ops
   - trust/KYC

## Kratka istorija verzija

- V11.18.30: Zaključana i sređena početna promo/banner sekcija. Početnu ne dirati dalje.
- V11.18.31: Task proof workflow.
- V11.18.32: Payout workflow.
- V11.18.33: Advertiser budget engine.
- V11.18.34: Finance reconciliation.
- V11.18.35: Ops Command Center.
- V11.18.36: Complete Trust Launch Pack: KYC, payout lock, fraud/risk, disputes, daily report, launch checklist, advertiser performance.
