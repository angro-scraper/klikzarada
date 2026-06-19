# Sačuvaj Hranu — V59 Payments + Commission Hardening

V59 dodaje poseban modul za obračun provizije kod plaćanja pri preuzimanju.

## Novo

- Nova admin strana: `/commission-admin`
- Alias: `/v59`
- API:
  - `GET /commission/summary`
  - `GET /commission/sellers`
  - `GET /commission/sellers/{store_id}/items`
  - `POST /commission/sellers/{store_id}/invoice`
  - `PATCH /commission/invoices/{invoice_reference}/mark-paid`
  - `GET /commission/export.csv`
- Novi statusi provizije:
  - `commission_due` — prodavac duguje proviziju
  - `invoice_sent` — obračun je poslat prodavcu
  - `commission_paid` — provizija je naplaćena
- `/finance` sada ima link ka provizijama i filtere za nove statuse.
- `/flow` sada vodi i ka novom commission modulu.

## Model novca

- Online/PayPal: platforma prima uplatu i zadržava 25% provizije.
- Plaćanje pri preuzimanju: prodavac naplaćuje kupcu i duguje platformi 25% kroz nedeljni/mesečni obračun.

## Pokretanje

```powershell
cd C:\Users\49162\Downloads
Expand-Archive .\food-saver-serbia-v59-payments-commission-hardening.zip -DestinationPath .\food-saver-serbia-v59-payments-commission-hardening -Force
cd "C:\Users\49162\Downloads\food-saver-serbia-v59-payments-commission-hardening\v59_work\backend"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python -m uvicorn app.main:app --reload
```

Otvori:

- `/flow` za kreiranje demo rezervacije
- `/checkout` za plaćanje pri preuzimanju
- `/seller` za potvrdu preuzimanja
- `/commission-admin` za obračun i naplatu provizije
- `/finance` za širi finansijski pregled
