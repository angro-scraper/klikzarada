# Codex Handoff — KlikZarada V11.18.36

Ovo je kompletan projekat spreman za nastavak u Codex-u.

## Glavno pravilo
Početna stranica je zaključana. Ne menjati početnu bez eksplicitnog zahteva.

## Start komanda

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Glavni audit

```powershell
python scripts\complete_trust_launch_pack_audit_v11836.py
```

## Važni login podaci iz seed-a

Admin:
- admin@klikzarada.rs
- Admin123!

Oglašivač:
- oglasivac@demo.rs
- Demo123!

Korisnik:
- korisnik@demo.rs
- Demo123!

## Najnoviji moduli

### Trust/KYC
- /admin/trust-v11836
- /korisnik/kyc-v11836
- /korisnik/isplate/zahtev-v11836

### Dispute
- /korisnik/dokazi/{submission_id}/zalba-v11836
- /admin/disputes-v11836

### Daily report
- /admin/daily-v11836
- /admin/daily-v11836/email

### Launch
- /admin/launch-v11836

### Oglašivač performance
- /oglasivac/performance-v11836

### Health
- /api/v1/v11/trust-launch-health

## Sledeći mogući koraci u Codex-u

1. Pravi SMTP slanje email queue-a.
2. UI forma za KYC u korisničkom panelu ako nije dovoljno vidljiva.
3. Bolji admin filteri za Trust/KYC panel.
4. Export dispute i KYC CSV.
5. Role-based sidebar linkovi za nove panele.
6. Backup/restore modul.
7. Produkcioni deployment checklist za Render/VPS.
