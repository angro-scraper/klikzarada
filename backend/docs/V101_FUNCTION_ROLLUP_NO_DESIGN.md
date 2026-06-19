# V101 Functional Rollup — bez dizajna

Ovaj update zaključava pravilo: V71 dizajn se ne dira.

## Sabirane funkcije

- Finansije i provizije
- QR preuzimanje
- Partner operacije
- Pilot/live checklist
- Pravne stranice/status
- Marketing šabloni
- Analitika
- Notifikacije/outbox
- Integracije
- Bezbednosne provere
- Podrška/CRM
- Mapa na početnoj strani

## Mapa na početnoj

Mapa se ubacuje samo na `/pocetna` kroz ograničeni middleware. Ne menja globalni dizajn.

## Live napomena

Pre pravog live-a moraju se podesiti:

- produkcioni `.env`
- domen i HTTPS
- admin token
- backup
- monitoring
- email/SMS provider
- pravni pregled tekstova
