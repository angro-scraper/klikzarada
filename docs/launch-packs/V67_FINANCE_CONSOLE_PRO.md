
# Food Saver Serbia — V67 Finance Console Pro

## Šta dodaje

- uredan pregled svih računa
- KPI kartice: broj računa, fakturisano, plaćeno, dug, ledger saldo
- filtere po statusu, seller ID, dugu i pretrazi
- detaljan panel za svaki račun
- pregled stavki računa
- pregled uplata
- lifecycle status: issued, sent, due, paid, voided, disputed
- akcije po računu: issue, send, pay due, overdue, dispute, void
- print/PDF prikaz za pojedinačni račun
- seller balance tabelu
- audit log
- full demo flow

## Instalacija

Iz backend foldera:

```powershell
python ".\apply_v67_finance_console_pro.py"
.\run_v67_verify_finance_console_pro.ps1
.\run_backend.ps1
```

Otvori:

```text
http://127.0.0.1:8000/admin/finance-console
```

Print stranica za pojedinačni račun:

```text
http://127.0.0.1:8000/admin/finance-console/invoice/1/print
```

## Napomena

Ako koristiš V66 admin guard i uključen je `ADMIN_GUARD_ENABLED=true`, otvori admin console sa:

```text
http://127.0.0.1:8000/admin/finance-console?admin_token=TVOJ_TOKEN
```
