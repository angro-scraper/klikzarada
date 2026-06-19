# PayPal setup za Sačuvaj Hranu

1. Otvori ili koristi PayPal Business nalog.
2. U `.env` stavi:

```env
PAYMENT_PROVIDER=paypal
PAYPAL_MODE=live
PAYPAL_BUSINESS_EMAIL=tvoj-paypal-business-email@example.com
PAYPAL_CURRENCY=EUR
PAYPAL_RSD_TO_EUR_RATE=117.0
PUBLIC_BASE_URL=http://127.0.0.1:8000
```

3. Restartuj server.
4. Rezerviši proizvod i otvori `/checkout?code=KOD`.
5. Klikni `Nastavi na PayPal`.

## Važno

- Ako su cene u aplikaciji u RSD, PayPal iznos se u ovom MVP-u računa u EUR preko `PAYPAL_RSD_TO_EUR_RATE`.
- Ako nemaš `PAYPAL_BUSINESS_EMAIL`, kupac može da izabere `Plaćanje pri preuzimanju`.
- Za automatsko potvrđivanje plaćanja u produkciji dodaje se PayPal API/webhook/IPN verifikacija.
