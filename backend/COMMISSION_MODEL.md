# V52 — Kako platforma uzima proviziju

Aplikacija podržava dva modela naplate:

## 1. Online plaćanje preko platforme

Provider: `paypal`, `ips_qr`, `demo`, kasnije kartični gateway.

Tok:

1. Kupac plaća kroz checkout.
2. Platforma evidentira `payment_status=paid`.
3. Sistem računa 25% platform fee.
4. Prodavcu se isplaćuje neto iznos: ukupno - loyalty popust - 25% provizija.
5. Finance panel stavlja rezervaciju u `seller_payout_status=pending` dok se prodavcu ne isplati.

Ovo je najbolji model za automatizaciju provizije.

## 2. Plaćanje pri preuzimanju

Provider: `pay_on_pickup`.

Tok:

1. Kupac rezerviše.
2. Kupac plaća direktno prodavcu pri preuzimanju.
3. Platforma nije primila novac.
4. Sistem ipak računa 25% proviziju i stavlja `seller_payout_status=commission_due`.
5. Prodavac periodično plaća platformi proviziju kroz mesečni/nedeljni obračun.

Ovo je korisno za prvi pilot kada nemamo payment provider ili srpski račun, ali zahteva ručni obračun u Finance panelu.

## Preporuka za pilot

Za najbrži start koristi:

```env
PAYMENT_PROVIDER=paypal
```

Ako PayPal nije podešen:

```env
PAYMENT_PROVIDER=pay_on_pickup
```

Tada aplikacija ne blokira rezervacije, ali provizija mora da se naplati od prodavca kroz periodični obračun.
