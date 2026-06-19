
# Food Saver Serbia — V68 Finance Reports Command Center

## Added endpoints

- `GET /api/admin/finance/dashboard-data`
- `GET /api/admin/finance/reports/aging`
- `GET /api/admin/finance/reports/monthly-summary`
- `GET /api/admin/finance/reports/seller-statement?seller_id=...`
- `GET /api/admin/finance/monthly-close/preview`
- `POST /api/admin/finance/monthly-close/run`
- `POST /api/admin/finance/invoices/bulk-mark-overdue`
- `GET /api/admin/finance/reconciliation/check`
- `GET /api/admin/finance/export/invoices.csv`
- `GET /api/admin/finance/export/ledger.csv`
- `GET /api/admin/finance/export/payments.csv`
- `GET /api/admin/finance/reports/seller-statement.csv?seller_id=...`
- `GET /admin/finance-reports-console`
- `GET /admin/finance-console/invoice/{invoice_id}/print`

## Install

```powershell
Expand-Archive -Path "$env:USERPROFILE\Downloads\v68-finance-reports-command-center-update-pack.zip" -DestinationPath ".\v68_reports" -Force
Copy-Item ".\v68_reports\apply_v68_finance_reports_command_center.py" "." -Force
python ".\apply_v68_finance_reports_command_center.py"
.\run_v68_verify_finance_reports.ps1
```

## Open

```text
http://127.0.0.1:8000/admin/finance-reports-console
```

## Notes

V68 does not replace V67. It adds a reports command center focused on finance reporting, aging, monthly close, seller statements and exports.
