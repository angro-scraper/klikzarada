# V59 — Payments + Commission Hardening

Ovaj modul razdvaja dva toka novca:

## 1. Online / PayPal tok

Kupac plaća platformi. Platforma zadržava 25% provizije, a prodavcu se vodi neto iznos za isplatu.

Statusi:

- `payment_status = paid`
- `seller_payout_status = pending`
- posle isplate prodavcu: `seller_payout_status = paid`

## 2. Plaćanje pri preuzimanju

Kupac plaća prodavcu direktno. Platforma nije primila novac, pa prodavac duguje platformi 25% provizije.

Statusi:

- `payment_status = pay_on_pickup`
- `seller_payout_status = commission_due`
- kada se napravi obračun: `seller_payout_status = invoice_sent`
- kada prodavac plati proviziju: `seller_payout_status = commission_paid`

## Admin strana

Otvori `/commission-admin`.

Na toj strani možeš:

1. videti otvorenu proviziju po partneru,
2. kreirati obračun za sve otvorene stavke jednog partnera,
3. označiti obračun kao naplaćen,
4. izvesti CSV za knjigovodstvo.

## API

- `GET /commission/summary`
- `GET /commission/sellers`
- `GET /commission/sellers/{store_id}/items?include_paid=true`
- `POST /commission/sellers/{store_id}/invoice`
- `PATCH /commission/invoices/{invoice_reference}/mark-paid`
- `GET /commission/export.csv`
