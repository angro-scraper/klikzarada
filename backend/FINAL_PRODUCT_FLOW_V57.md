# V57 Final Product Flow — šta se testira

## Kupac
- `/app` prikazuje ponude.
- Modal za rezervaciju kreira kod.
- Checkout link vodi na `/checkout?code=...`.
- Digitalna karta vodi na `/reservation?code=...`.

## Prodavac
- `/seller` se koristi sa Store ID + PIN.
- Kod rezervacije se proverava ručno ili QR skenerom.
- Status se menja u `picked_up`.

## Plaćanje i provizija
- Online/demo plaćanje vodi kroz checkout.
- Plaćanje pri preuzimanju postavlja `payment_status=pay_on_pickup`.
- Kod plaćanja pri preuzimanju `seller_payout_status=commission_due`.
- Finance vidi proviziju za naplatu.

## Admin
- `/flow` pokazuje spremnost toka u procentima.
- `/command` ostaje glavni dashboard.
- `/finance` prati novac i proviziju.
