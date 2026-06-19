# Backend V45

Glavne nove rute:

- `/app` — nova korisnička aplikacija
- `/u` — kratka putanja za korisničku aplikaciju
- `POST /v45/seed-consumer-database` — učitava pilot bazu sa gradovima, GPS lokacijama, slikama, cenama i količinama
- `GET /v45/consumer-readiness` — meri spremnost baze za korisničko testiranje

Ako pretraga po gradovima vraća 0, prvo klikni **Učitaj pilot bazu** na `/app`.
