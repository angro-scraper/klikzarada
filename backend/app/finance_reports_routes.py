
from __future__ import annotations

import csv
import io
import os
from datetime import date, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from .database import get_db
from .models import Store, Product, Reservation
from .finance_models import (
    SellerCommissionLedger,
    SellerInvoice,
    SellerInvoiceLine,
    SellerInvoicePaymentRequest,
    SellerInvoicePayment,
    ProviderWebhookEvent,
    FinanceReconciliationException,
    FinanceAuditLog,
)

router = APIRouter(tags=['V68 Finance Reports Command Center'])


def _money(value: Any) -> float:
    try:
        return round(float(value or 0), 2)
    except Exception:
        return 0.0


def _iso(value: Any) -> str | None:
    if not value:
        return None
    if hasattr(value, 'isoformat'):
        return value.isoformat()
    return str(value)


def _month_bounds(year: int, month: int) -> tuple[date, date]:
    start = date(year, month, 1)
    if month == 12:
        end = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end = date(year, month + 1, 1) - timedelta(days=1)
    return start, end


def _parse_date(value: str | None, default: date | None = None) -> date:
    if not value:
        return default or date.today()
    return date.fromisoformat(value)


def _invoice_dict(inv: SellerInvoice) -> dict:
    return {
        'id': inv.id,
        'seller_id': inv.seller_id,
        'invoice_number': inv.invoice_number,
        'status': inv.status,
        'period_start': _iso(inv.period_start),
        'period_end': _iso(inv.period_end),
        'subtotal_amount': _money(inv.subtotal_amount),
        'adjustment_amount': _money(inv.adjustment_amount),
        'total_amount': _money(inv.total_amount),
        'amount_paid': _money(inv.amount_paid),
        'amount_due': _money(inv.amount_due),
        'currency': inv.currency or 'RSD',
        'issued_at': _iso(inv.issued_at),
        'sent_at': _iso(inv.sent_at),
        'due_date': _iso(inv.due_date),
        'paid_at': _iso(inv.paid_at),
        'voided_at': _iso(inv.voided_at),
        'dispute_reason': inv.dispute_reason,
        'created_at': _iso(inv.created_at),
        'updated_at': _iso(inv.updated_at),
    }


def _seller_name_map(db: Session) -> dict[int, str]:
    return {s.id: s.name for s in db.query(Store).all()}


def _aging_bucket(days_overdue: int) -> str:
    if days_overdue <= 0:
        return 'not_due'
    if days_overdue <= 7:
        return '1_7'
    if days_overdue <= 14:
        return '8_14'
    if days_overdue <= 30:
        return '15_30'
    return '31_plus'


def _csv_response(filename: str, rows: list[dict], fieldnames: list[str]) -> Response:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return Response(
        content=output.getvalue(),
        media_type='text/csv',
        headers={'Content-Disposition': f'attachment; filename={filename}'},
    )


@router.get('/api/admin/finance/dashboard-data')
def finance_dashboard_data(db: Session = Depends(get_db)):
    sellers = db.query(Store).all()
    invoices = db.query(SellerInvoice).order_by(SellerInvoice.created_at.desc()).all()
    ledger = db.query(SellerCommissionLedger).all()
    payments = db.query(SellerInvoicePayment).order_by(SellerInvoicePayment.created_at.desc()).limit(20).all()
    exceptions = db.query(FinanceReconciliationException).filter(FinanceReconciliationException.status != 'RESOLVED').all()
    seller_names = _seller_name_map(db)

    total_invoiced = sum(_money(i.total_amount) for i in invoices if i.status != 'VOID')
    total_paid = sum(_money(i.amount_paid) for i in invoices if i.status != 'VOID')
    total_due = sum(_money(i.amount_due) for i in invoices if i.status not in ('PAID', 'VOID'))
    ledger_debit = sum(_money(e.amount) for e in ledger if (e.direction or '').upper() == 'DEBIT')
    ledger_credit = sum(_money(e.amount) for e in ledger if (e.direction or '').upper() == 'CREDIT')

    status_counts: dict[str, int] = {}
    for inv in invoices:
        status_counts[inv.status or 'UNKNOWN'] = status_counts.get(inv.status or 'UNKNOWN', 0) + 1

    seller_due: dict[int, float] = {}
    for inv in invoices:
        if inv.status not in ('PAID', 'VOID'):
            seller_due[inv.seller_id] = seller_due.get(inv.seller_id, 0.0) + _money(inv.amount_due)

    top_sellers_due = sorted(
        [
            {'seller_id': sid, 'seller_name': seller_names.get(sid), 'amount_due': round(amount, 2), 'currency': 'RSD'}
            for sid, amount in seller_due.items()
        ],
        key=lambda x: x['amount_due'],
        reverse=True,
    )[:10]

    aging = _build_aging(db, date.today())

    return {
        'version': 'V68',
        'title': 'Finance Reports Command Center',
        'environment': os.getenv('ENVIRONMENT', 'local'),
        'kpis': {
            'sellers_count': len(sellers),
            'invoices_count': len(invoices),
            'total_invoiced': round(total_invoiced, 2),
            'total_paid': round(total_paid, 2),
            'total_due': round(total_due, 2),
            'ledger_debit': round(ledger_debit, 2),
            'ledger_credit': round(ledger_credit, 2),
            'ledger_balance': round(ledger_debit - ledger_credit, 2),
            'open_reconciliation_exceptions': len(exceptions),
            'currency': 'RSD',
        },
        'status_counts': status_counts,
        'aging_summary': aging['summary'],
        'top_sellers_due': top_sellers_due,
        'recent_invoices': [_invoice_dict(i) | {'seller_name': seller_names.get(i.seller_id)} for i in invoices[:20]],
        'recent_payments': [
            {
                'id': p.id,
                'seller_invoice_id': p.seller_invoice_id,
                'seller_id': p.seller_id,
                'seller_name': seller_names.get(p.seller_id),
                'provider': p.provider,
                'amount': _money(p.amount),
                'currency': p.currency or 'RSD',
                'status': p.status,
                'payment_date': _iso(p.payment_date),
                'received_at': _iso(p.received_at),
                'notes': p.notes,
            }
            for p in payments
        ],
    }


def _build_aging(db: Session, as_of: date) -> dict:
    invoices = db.query(SellerInvoice).order_by(SellerInvoice.due_date.asc()).all()
    seller_names = _seller_name_map(db)
    summary = {
        'not_due': {'count': 0, 'amount_due': 0.0},
        '1_7': {'count': 0, 'amount_due': 0.0},
        '8_14': {'count': 0, 'amount_due': 0.0},
        '15_30': {'count': 0, 'amount_due': 0.0},
        '31_plus': {'count': 0, 'amount_due': 0.0},
    }
    items = []

    for inv in invoices:
        due = _money(inv.amount_due)
        if due <= 0 or inv.status in ('PAID', 'VOID'):
            continue

        due_date = inv.due_date or as_of
        days_overdue = (as_of - due_date).days
        bucket = _aging_bucket(days_overdue)
        summary[bucket]['count'] += 1
        summary[bucket]['amount_due'] = round(summary[bucket]['amount_due'] + due, 2)

        items.append(
            _invoice_dict(inv)
            | {
                'seller_name': seller_names.get(inv.seller_id),
                'days_overdue': days_overdue,
                'aging_bucket': bucket,
            }
        )

    return {'as_of': as_of.isoformat(), 'summary': summary, 'items': items}


@router.get('/api/admin/finance/reports/aging')
def finance_aging_report(as_of: str | None = Query(None), db: Session = Depends(get_db)):
    return _build_aging(db, _parse_date(as_of, date.today()))


@router.get('/api/admin/finance/reports/monthly-summary')
def finance_monthly_summary(
    year: int = Query(default_factory=lambda: date.today().year),
    month: int = Query(default_factory=lambda: date.today().month, ge=1, le=12),
    db: Session = Depends(get_db),
):
    start, end = _month_bounds(year, month)
    seller_names = _seller_name_map(db)

    invoices = [
        i for i in db.query(SellerInvoice).all()
        if (i.created_at and start <= i.created_at.date() <= end)
        or (i.period_start and i.period_end and i.period_start <= end and i.period_end >= start)
    ]
    payments = [
        p for p in db.query(SellerInvoicePayment).all()
        if (p.payment_date and start <= p.payment_date <= end)
        or (p.created_at and start <= p.created_at.date() <= end)
    ]
    ledger = [
        e for e in db.query(SellerCommissionLedger).all()
        if e.created_at and start <= e.created_at.date() <= end
    ]

    by_seller: dict[int, dict] = {}
    for inv in invoices:
        row = by_seller.setdefault(inv.seller_id, {
            'seller_id': inv.seller_id,
            'seller_name': seller_names.get(inv.seller_id),
            'invoices_count': 0,
            'invoiced': 0.0,
            'paid': 0.0,
            'due': 0.0,
            'currency': inv.currency or 'RSD',
        })
        row['invoices_count'] += 1
        if inv.status != 'VOID':
            row['invoiced'] = round(row['invoiced'] + _money(inv.total_amount), 2)
            row['paid'] = round(row['paid'] + _money(inv.amount_paid), 2)
            row['due'] = round(row['due'] + _money(inv.amount_due), 2)

    ledger_debit = sum(_money(e.amount) for e in ledger if (e.direction or '').upper() == 'DEBIT')
    ledger_credit = sum(_money(e.amount) for e in ledger if (e.direction or '').upper() == 'CREDIT')

    return {
        'period': {'year': year, 'month': month, 'start': start.isoformat(), 'end': end.isoformat()},
        'summary': {
            'invoices_count': len(invoices),
            'payments_count': len(payments),
            'ledger_entries_count': len(ledger),
            'total_invoiced': round(sum(_money(i.total_amount) for i in invoices if i.status != 'VOID'), 2),
            'total_paid_on_invoices': round(sum(_money(i.amount_paid) for i in invoices if i.status != 'VOID'), 2),
            'total_due_on_invoices': round(sum(_money(i.amount_due) for i in invoices if i.status not in ('PAID', 'VOID')), 2),
            'payments_received': round(sum(_money(p.amount) for p in payments if p.status in ('CONFIRMED', 'PAID')), 2),
            'ledger_debit': round(ledger_debit, 2),
            'ledger_credit': round(ledger_credit, 2),
            'ledger_balance': round(ledger_debit - ledger_credit, 2),
            'currency': 'RSD',
        },
        'by_seller': sorted(by_seller.values(), key=lambda x: x['due'], reverse=True),
        'invoices': [_invoice_dict(i) | {'seller_name': seller_names.get(i.seller_id)} for i in invoices],
    }


@router.get('/api/admin/finance/reports/seller-statement')
def finance_seller_statement(
    seller_id: int = Query(...),
    year: int | None = Query(None),
    month: int | None = Query(None, ge=1, le=12),
    db: Session = Depends(get_db),
):
    seller = db.get(Store, seller_id)
    if not seller:
        raise HTTPException(status_code=404, detail='Seller not found')

    start = end = None
    if year and month:
        start, end = _month_bounds(year, month)

    invoices = db.query(SellerInvoice).filter(SellerInvoice.seller_id == seller_id).order_by(SellerInvoice.created_at.desc()).all()
    ledger = db.query(SellerCommissionLedger).filter(SellerCommissionLedger.seller_id == seller_id).order_by(SellerCommissionLedger.created_at.desc()).all()
    payments = db.query(SellerInvoicePayment).filter(SellerInvoicePayment.seller_id == seller_id).order_by(SellerInvoicePayment.created_at.desc()).all()

    if start and end:
        invoices = [i for i in invoices if (i.created_at and start <= i.created_at.date() <= end) or (i.period_start and i.period_end and i.period_start <= end and i.period_end >= start)]
        ledger = [e for e in ledger if e.created_at and start <= e.created_at.date() <= end]
        payments = [p for p in payments if (p.payment_date and start <= p.payment_date <= end) or (p.created_at and start <= p.created_at.date() <= end)]

    debit = sum(_money(e.amount) for e in ledger if (e.direction or '').upper() == 'DEBIT')
    credit = sum(_money(e.amount) for e in ledger if (e.direction or '').upper() == 'CREDIT')

    return {
        'seller': {
            'id': seller.id,
            'name': seller.name,
            'city': getattr(seller, 'city', None),
            'address': getattr(seller, 'address', None),
            'phone': getattr(seller, 'phone', None),
            'verified': getattr(seller, 'verified', None),
        },
        'period': {'year': year, 'month': month, 'start': _iso(start), 'end': _iso(end)},
        'summary': {
            'invoices_count': len(invoices),
            'total_invoiced': round(sum(_money(i.total_amount) for i in invoices if i.status != 'VOID'), 2),
            'total_paid': round(sum(_money(i.amount_paid) for i in invoices if i.status != 'VOID'), 2),
            'total_due': round(sum(_money(i.amount_due) for i in invoices if i.status not in ('PAID', 'VOID')), 2),
            'ledger_debit': round(debit, 2),
            'ledger_credit': round(credit, 2),
            'ledger_balance': round(debit - credit, 2),
            'currency': 'RSD',
        },
        'invoices': [_invoice_dict(i) for i in invoices],
        'ledger': [
            {
                'id': e.id,
                'order_id': e.order_id,
                'invoice_id': e.invoice_id,
                'type': e.type,
                'direction': e.direction,
                'amount': _money(e.amount),
                'currency': e.currency or 'RSD',
                'commission_rate': e.commission_rate,
                'description': e.description,
                'idempotency_key': e.idempotency_key,
                'created_at': _iso(e.created_at),
            }
            for e in ledger
        ],
        'payments': [
            {
                'id': p.id,
                'seller_invoice_id': p.seller_invoice_id,
                'provider': p.provider,
                'amount': _money(p.amount),
                'currency': p.currency or 'RSD',
                'status': p.status,
                'payment_date': _iso(p.payment_date),
                'received_at': _iso(p.received_at),
                'notes': p.notes,
            }
            for p in payments
        ],
    }


@router.get('/api/admin/finance/monthly-close/preview')
def monthly_close_preview(
    year: int = Query(default_factory=lambda: date.today().year),
    month: int = Query(default_factory=lambda: date.today().month, ge=1, le=12),
    db: Session = Depends(get_db),
):
    start, end = _month_bounds(year, month)
    seller_names = _seller_name_map(db)
    entries = db.query(SellerCommissionLedger).filter(SellerCommissionLedger.invoice_id.is_(None)).filter(SellerCommissionLedger.direction == 'DEBIT').all()
    entries = [e for e in entries if not e.created_at or start <= e.created_at.date() <= end]

    by_seller: dict[int, dict] = {}
    for e in entries:
        row = by_seller.setdefault(e.seller_id, {
            'seller_id': e.seller_id,
            'seller_name': seller_names.get(e.seller_id),
            'entries_count': 0,
            'amount': 0.0,
            'currency': e.currency or 'RSD',
            'entry_ids': [],
        })
        row['entries_count'] += 1
        row['amount'] = round(row['amount'] + _money(e.amount), 2)
        row['entry_ids'].append(e.id)

    sellers = sorted(by_seller.values(), key=lambda x: x['amount'], reverse=True)
    return {
        'period': {'year': year, 'month': month, 'start': start.isoformat(), 'end': end.isoformat()},
        'sellers_count': len(sellers),
        'entries_count': len(entries),
        'total_amount': round(sum(x['amount'] for x in sellers), 2),
        'currency': 'RSD',
        'items': sellers,
    }


@router.post('/api/admin/finance/monthly-close/run')
def monthly_close_run(
    year: int = Query(default_factory=lambda: date.today().year),
    month: int = Query(default_factory=lambda: date.today().month, ge=1, le=12),
    min_threshold: float = Query(0.0),
    db: Session = Depends(get_db),
):
    preview = monthly_close_preview(year=year, month=month, db=db)
    start, end = _month_bounds(year, month)
    created = []
    skipped = []

    for row in preview['items']:
        seller_id = row['seller_id']
        amount = _money(row['amount'])
        if amount < min_threshold:
            skipped.append({'seller_id': seller_id, 'reason': 'below_threshold', 'amount': amount})
            continue

        seller = db.get(Store, seller_id)
        if not seller:
            skipped.append({'seller_id': seller_id, 'reason': 'seller_not_found', 'amount': amount})
            continue

        entries = db.query(SellerCommissionLedger).filter(SellerCommissionLedger.id.in_(row['entry_ids'])).all()
        if not entries:
            skipped.append({'seller_id': seller_id, 'reason': 'no_entries_after_refresh', 'amount': amount})
            continue

        invoice_number = f'FS-MC-{year}{month:02d}-{seller_id}-{int(datetime.utcnow().timestamp())}'
        invoice = SellerInvoice(
            seller_id=seller_id,
            period_start=start,
            period_end=end,
            invoice_number=invoice_number,
            status='READY_FOR_REVIEW',
            subtotal_amount=amount,
            adjustment_amount=0.0,
            total_amount=amount,
            amount_paid=0.0,
            amount_due=amount,
            currency='RSD',
            due_date=date.today() + timedelta(days=10),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(invoice)
        db.flush()

        for entry in entries:
            line = SellerInvoiceLine(
                invoice_id=invoice.id,
                ledger_entry_id=entry.id,
                order_id=entry.order_id,
                line_type='COMMISSION',
                description=entry.description or f'Commission ledger entry #{entry.id}',
                quantity=1.0,
                unit_amount=_money(entry.amount),
                total_amount=_money(entry.amount),
                currency=entry.currency or 'RSD',
                created_at=datetime.utcnow(),
            )
            db.add(line)
            entry.invoice_id = invoice.id

        db.add(FinanceAuditLog(
            actor_admin_id=None,
            action='V68_MONTHLY_CLOSE_RUN',
            entity_type='seller_invoice',
            entity_id=invoice.id,
            before_json=None,
            after_json=f'seller_id={seller_id};period={year}-{month:02d};amount={amount};entries={len(entries)}',
            reason='V68 monthly close command center',
            created_at=datetime.utcnow(),
        ))
        created.append({'seller_id': seller_id, 'seller_name': seller.name, 'invoice_id': invoice.id, 'invoice_number': invoice.invoice_number, 'amount': amount})

    db.commit()
    return {'status': 'completed', 'created_count': len(created), 'skipped_count': len(skipped), 'created': created, 'skipped': skipped}


@router.post('/api/admin/finance/invoices/bulk-mark-overdue')
def bulk_mark_overdue(as_of: str | None = Query(None), db: Session = Depends(get_db)):
    as_of_date = _parse_date(as_of, date.today())
    candidates = db.query(SellerInvoice).all()
    changed = []

    for inv in candidates:
        if inv.status in ('PAID', 'VOID', 'DISPUTED'):
            continue
        if _money(inv.amount_due) <= 0:
            continue
        if inv.due_date and inv.due_date < as_of_date:
            before = inv.status
            inv.status = 'OVERDUE'
            inv.updated_at = datetime.utcnow()
            changed.append({'invoice_id': inv.id, 'invoice_number': inv.invoice_number, 'before': before, 'after': inv.status})
            db.add(FinanceAuditLog(
                actor_admin_id=None,
                action='V68_BULK_MARK_OVERDUE',
                entity_type='seller_invoice',
                entity_id=inv.id,
                before_json=f'status={before}',
                after_json=f'status={inv.status}',
                reason=f'Bulk overdue as_of={as_of_date.isoformat()}',
                created_at=datetime.utcnow(),
            ))

    db.commit()
    return {'status': 'completed', 'as_of': as_of_date.isoformat(), 'changed_count': len(changed), 'items': changed}


@router.get('/api/admin/finance/reconciliation/check')
def reconciliation_check(db: Session = Depends(get_db)):
    exceptions = []
    invoices = db.query(SellerInvoice).all()
    payments = db.query(SellerInvoicePayment).all()

    for inv in invoices:
        total = _money(inv.total_amount)
        paid = _money(inv.amount_paid)
        due = _money(inv.amount_due)
        if inv.status == 'PAID' and due > 0:
            exceptions.append({'type': 'PAID_WITH_DUE', 'invoice_id': inv.id, 'amount_due': due})
        if paid > total and total > 0:
            exceptions.append({'type': 'OVERPAID_INVOICE', 'invoice_id': inv.id, 'total': total, 'paid': paid})
        if due < 0:
            exceptions.append({'type': 'NEGATIVE_DUE', 'invoice_id': inv.id, 'amount_due': due})

    payment_sum_by_invoice: dict[int, float] = {}
    for p in payments:
        if p.status in ('CONFIRMED', 'PAID'):
            payment_sum_by_invoice[p.seller_invoice_id] = round(payment_sum_by_invoice.get(p.seller_invoice_id, 0.0) + _money(p.amount), 2)

    invoice_by_id = {i.id: i for i in invoices}
    for invoice_id, amount in payment_sum_by_invoice.items():
        inv = invoice_by_id.get(invoice_id)
        if inv and abs(amount - _money(inv.amount_paid)) > 0.01:
            exceptions.append({'type': 'PAYMENT_SUM_MISMATCH', 'invoice_id': invoice_id, 'payments_sum': amount, 'invoice_amount_paid': _money(inv.amount_paid)})

    return {'status': 'ok' if not exceptions else 'needs_review', 'exceptions_count': len(exceptions), 'items': exceptions}


@router.get('/api/admin/finance/export/invoices.csv')
def export_invoices_csv(db: Session = Depends(get_db)):
    seller_names = _seller_name_map(db)
    rows = [_invoice_dict(i) | {'seller_name': seller_names.get(i.seller_id)} for i in db.query(SellerInvoice).order_by(SellerInvoice.created_at.desc()).all()]
    fields = ['id', 'seller_id', 'seller_name', 'invoice_number', 'status', 'period_start', 'period_end', 'total_amount', 'amount_paid', 'amount_due', 'currency', 'due_date', 'issued_at', 'sent_at', 'paid_at', 'voided_at', 'created_at']
    return _csv_response('food_saver_v68_invoices.csv', rows, fields)


@router.get('/api/admin/finance/export/ledger.csv')
def export_ledger_csv(db: Session = Depends(get_db)):
    seller_names = _seller_name_map(db)
    rows = [
        {
            'id': e.id,
            'seller_id': e.seller_id,
            'seller_name': seller_names.get(e.seller_id),
            'order_id': e.order_id,
            'invoice_id': e.invoice_id,
            'type': e.type,
            'direction': e.direction,
            'amount': _money(e.amount),
            'currency': e.currency or 'RSD',
            'commission_rate': e.commission_rate,
            'description': e.description,
            'idempotency_key': e.idempotency_key,
            'created_at': _iso(e.created_at),
        }
        for e in db.query(SellerCommissionLedger).order_by(SellerCommissionLedger.created_at.desc()).all()
    ]
    fields = ['id', 'seller_id', 'seller_name', 'order_id', 'invoice_id', 'type', 'direction', 'amount', 'currency', 'commission_rate', 'description', 'idempotency_key', 'created_at']
    return _csv_response('food_saver_v68_ledger.csv', rows, fields)


@router.get('/api/admin/finance/export/payments.csv')
def export_payments_csv(db: Session = Depends(get_db)):
    seller_names = _seller_name_map(db)
    rows = [
        {
            'id': p.id,
            'seller_invoice_id': p.seller_invoice_id,
            'seller_id': p.seller_id,
            'seller_name': seller_names.get(p.seller_id),
            'provider': p.provider,
            'provider_payment_id': p.provider_payment_id,
            'amount': _money(p.amount),
            'currency': p.currency or 'RSD',
            'status': p.status,
            'payment_date': _iso(p.payment_date),
            'received_at': _iso(p.received_at),
            'notes': p.notes,
            'created_at': _iso(p.created_at),
        }
        for p in db.query(SellerInvoicePayment).order_by(SellerInvoicePayment.created_at.desc()).all()
    ]
    fields = ['id', 'seller_invoice_id', 'seller_id', 'seller_name', 'provider', 'provider_payment_id', 'amount', 'currency', 'status', 'payment_date', 'received_at', 'notes', 'created_at']
    return _csv_response('food_saver_v68_payments.csv', rows, fields)


@router.get('/api/admin/finance/reports/seller-statement.csv')
def export_seller_statement_csv(seller_id: int = Query(...), db: Session = Depends(get_db)):
    statement = finance_seller_statement(seller_id=seller_id, year=None, month=None, db=db)
    rows = []
    for i in statement['invoices']:
        rows.append({'section': 'invoice', **i})
    for e in statement['ledger']:
        rows.append({'section': 'ledger', **e})
    fields = ['section', 'id', 'invoice_number', 'status', 'seller_id', 'order_id', 'invoice_id', 'type', 'direction', 'total_amount', 'amount_paid', 'amount_due', 'amount', 'currency', 'description', 'created_at']
    return _csv_response(f'food_saver_v68_seller_{seller_id}_statement.csv', rows, fields)


REPORTS_HTML = r"""
<!doctype html>
<html lang="sr">
<head>
<meta charset="utf-8" />
<title>Food Saver Serbia - V68 Finance Reports</title>
<meta name="viewport" content="width=device-width, initial-scale=1" />
<style>
:root { --bg:#f3f5f7; --card:#fff; --ink:#17202a; --muted:#6b7280; --line:#e5e7eb; --brand:#111827; --good:#146c43; --warn:#a16207; --bad:#991b1b; --blue:#1d4ed8; }
* { box-sizing:border-box; }
body { margin:0; font-family:Arial, sans-serif; background:var(--bg); color:var(--ink); }
header { background:var(--brand); color:white; padding:18px 24px; display:flex; justify-content:space-between; align-items:center; gap:16px; }
header h1 { margin:0; font-size:22px; }
main { max-width:1440px; margin:0 auto; padding:20px; }
.grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(210px,1fr)); gap:14px; }
.card { background:var(--card); border:1px solid var(--line); border-radius:14px; padding:16px; box-shadow:0 1px 2px rgba(0,0,0,.04); }
.kpi { font-size:26px; font-weight:bold; margin-top:8px; }
.muted { color:var(--muted); font-size:13px; }
.toolbar { display:flex; flex-wrap:wrap; gap:8px; align-items:center; margin:12px 0; }
button, input, select { padding:9px 11px; border-radius:9px; border:1px solid #cbd5e1; }
button { background:var(--brand); color:white; border:0; cursor:pointer; }
button.good { background:var(--good); } button.warn { background:var(--warn); } button.bad { background:var(--bad); } button.blue { background:var(--blue); }
table { width:100%; border-collapse:collapse; background:white; }
th, td { border-bottom:1px solid var(--line); padding:9px; text-align:left; font-size:13px; vertical-align:top; }
th { background:#eef2f7; position:sticky; top:0; z-index:1; }
.table-wrap { overflow:auto; max-height:520px; border:1px solid var(--line); border-radius:12px; }
.badge { display:inline-block; border-radius:999px; padding:3px 8px; font-size:12px; background:#e5e7eb; }
.badge.PAID { background:#dcfce7; color:#166534; } .badge.OVERDUE { background:#fee2e2; color:#991b1b; } .badge.SENT { background:#dbeafe; color:#1d4ed8; } .badge.READY_FOR_REVIEW { background:#fef3c7; color:#92400e; }
pre { background:#0b1220; color:#e5e7eb; padding:14px; border-radius:12px; overflow:auto; }
.tabs { display:flex; flex-wrap:wrap; gap:8px; margin:16px 0; }
.tab { background:#e5e7eb; color:#111827; } .tab.active { background:#111827; color:white; }
.hidden { display:none; }
.two { display:grid; grid-template-columns:minmax(0,1.2fr) minmax(320px,.8fr); gap:16px; }
@media (max-width: 900px) { .two { grid-template-columns:1fr; } }
</style>
</head>
<body>
<header><h1>V68 Finance Reports Command Center</h1><div>Food Saver Serbia</div></header>
<main>
  <section class="grid" id="kpis"></section>
  <div class="tabs">
    <button class="tab active" onclick="tab('dashboard')">Dashboard</button>
    <button class="tab" onclick="tab('aging')">Aging</button>
    <button class="tab" onclick="tab('monthly')">Monthly Close</button>
    <button class="tab" onclick="tab('seller')">Seller Statement</button>
    <button class="tab" onclick="tab('exports')">Exports</button>
    <button class="tab" onclick="tab('raw')">Raw</button>
  </div>

  <section id="dashboard" class="panel">
    <div class="two">
      <div class="card"><h2>Recent invoices</h2><div class="toolbar"><input id="search" placeholder="Search invoice/seller/status" oninput="renderInvoices()"><select id="statusFilter" onchange="renderInvoices()"><option value="">All statuses</option></select><button onclick="loadAll()">Refresh</button></div><div class="table-wrap" id="invoiceTable"></div></div>
      <div class="card"><h2>Top sellers due</h2><div id="topSellers"></div><h2>Recent payments</h2><div id="payments"></div></div>
    </div>
  </section>

  <section id="aging" class="panel hidden">
    <div class="card"><h2>Aging report</h2><div class="toolbar"><input id="agingDate" type="date"><button onclick="loadAging()">Run aging</button><button class="warn" onclick="bulkOverdue()">Bulk mark overdue</button></div><div id="agingSummary"></div><div class="table-wrap" id="agingTable"></div></div>
  </section>

  <section id="monthly" class="panel hidden">
    <div class="card"><h2>Monthly summary & close</h2><div class="toolbar"><input id="year" type="number"><input id="month" type="number" min="1" max="12"><input id="threshold" type="number" value="0"><button onclick="monthlySummary()">Monthly summary</button><button onclick="monthlyPreview()">Close preview</button><button class="good" onclick="monthlyRun()">Run monthly close</button></div><pre id="monthlyOut"></pre></div>
  </section>

  <section id="seller" class="panel hidden">
    <div class="card"><h2>Seller statement</h2><div class="toolbar"><input id="sellerId" placeholder="seller_id"><button onclick="sellerStatement()">Load statement</button><button onclick="downloadSellerCsv()">Seller CSV</button></div><pre id="sellerOut"></pre></div>
  </section>

  <section id="exports" class="panel hidden">
    <div class="card"><h2>Exports</h2><button onclick="location.href='/api/admin/finance/export/invoices.csv'">Invoices CSV</button><button onclick="location.href='/api/admin/finance/export/ledger.csv'">Ledger CSV</button><button onclick="location.href='/api/admin/finance/export/payments.csv'">Payments CSV</button><button onclick="location.href='/api/admin/finance/export.csv'">Legacy CSV</button><button onclick="reconcile()">Reconciliation check</button><pre id="exportOut"></pre></div>
  </section>

  <section id="raw" class="panel hidden"><div class="card"><h2>Raw payload</h2><pre id="rawOut"></pre></div></section>
</main>
<script>
let dashboard = null; let aging = null;
const today = new Date();
document.getElementById('year').value = today.getFullYear();
document.getElementById('month').value = today.getMonth()+1;
document.getElementById('agingDate').valueAsDate = today;
function fmt(n){ return Number(n||0).toLocaleString('sr-RS',{minimumFractionDigits:2,maximumFractionDigits:2}) + ' RSD'; }
async function api(path, options={}){ const r=await fetch(path, options); const t=await r.text(); let d; try{d=JSON.parse(t)}catch{d=t}; if(!r.ok) throw new Error(JSON.stringify(d,null,2)); return d; }
function tab(id){ document.querySelectorAll('.panel').forEach(x=>x.classList.add('hidden')); document.getElementById(id).classList.remove('hidden'); document.querySelectorAll('.tab').forEach(x=>x.classList.remove('active')); event.target.classList.add('active'); }
function table(rows, cols){ if(!rows||!rows.length) return '<p class="muted">No data</p>'; return '<table><thead><tr>'+cols.map(c=>'<th>'+c.label+'</th>').join('')+'</tr></thead><tbody>'+rows.map(r=>'<tr>'+cols.map(c=>'<td>'+c.render(r)+'</td>').join('')+'</tr>').join('')+'</tbody></table>'; }
function statusBadge(s){ return '<span class="badge '+(s||'')+'">'+(s||'')+'</span>'; }
async function loadAll(){ dashboard=await api('/api/admin/finance/dashboard-data'); document.getElementById('rawOut').textContent=JSON.stringify(dashboard,null,2); renderKpis(); renderInvoices(); renderTop(); renderPayments(); }
function renderKpis(){ const k=dashboard.kpis; const cards=[['Fakturisano',fmt(k.total_invoiced)],['Plaćeno',fmt(k.total_paid)],['Dug',fmt(k.total_due)],['Ledger saldo',fmt(k.ledger_balance)],['Računi',k.invoices_count],['Open exceptions',k.open_reconciliation_exceptions]]; document.getElementById('kpis').innerHTML=cards.map(c=>'<div class="card"><div class="muted">'+c[0]+'</div><div class="kpi">'+c[1]+'</div></div>').join(''); const statuses=Object.keys(dashboard.status_counts||{}); document.getElementById('statusFilter').innerHTML='<option value="">All statuses</option>'+statuses.map(s=>'<option>'+s+'</option>').join(''); }
function renderInvoices(){ const q=(document.getElementById('search').value||'').toLowerCase(); const sf=document.getElementById('statusFilter').value; let rows=(dashboard&&dashboard.recent_invoices)||[]; if(sf) rows=rows.filter(x=>x.status===sf); if(q) rows=rows.filter(x=>JSON.stringify(x).toLowerCase().includes(q)); document.getElementById('invoiceTable').innerHTML=table(rows,[{label:'ID',render:x=>x.id},{label:'Seller',render:x=>(x.seller_name||'')+'<br><span class="muted">#'+x.seller_id+'</span>'},{label:'Invoice',render:x=>x.invoice_number},{label:'Status',render:x=>statusBadge(x.status)},{label:'Total',render:x=>fmt(x.total_amount)},{label:'Paid',render:x=>fmt(x.amount_paid)},{label:'Due',render:x=>fmt(x.amount_due)},{label:'Due date',render:x=>x.due_date||''},{label:'Print',render:x=>'<a target="_blank" href="/admin/finance-console/invoice/'+x.id+'/print">print</a>'}]); }
function renderTop(){ document.getElementById('topSellers').innerHTML=table(dashboard.top_sellers_due,[{label:'Seller',render:x=>(x.seller_name||'')+' #'+x.seller_id},{label:'Due',render:x=>fmt(x.amount_due)}]); }
function renderPayments(){ document.getElementById('payments').innerHTML=table(dashboard.recent_payments,[{label:'Invoice',render:x=>x.seller_invoice_id},{label:'Seller',render:x=>(x.seller_name||'')},{label:'Amount',render:x=>fmt(x.amount)},{label:'Status',render:x=>x.status}]); }
async function loadAging(){ aging=await api('/api/admin/finance/reports/aging?as_of='+document.getElementById('agingDate').value); document.getElementById('agingSummary').innerHTML='<pre>'+JSON.stringify(aging.summary,null,2)+'</pre>'; document.getElementById('agingTable').innerHTML=table(aging.items,[{label:'Invoice',render:x=>x.invoice_number},{label:'Seller',render:x=>(x.seller_name||'')+' #'+x.seller_id},{label:'Status',render:x=>statusBadge(x.status)},{label:'Due',render:x=>fmt(x.amount_due)},{label:'Due date',render:x=>x.due_date||''},{label:'Days',render:x=>x.days_overdue},{label:'Bucket',render:x=>x.aging_bucket}]); }
async function bulkOverdue(){ const x=await api('/api/admin/finance/invoices/bulk-mark-overdue?as_of='+document.getElementById('agingDate').value,{method:'POST'}); alert('Changed: '+x.changed_count); await loadAging(); await loadAll(); }
async function monthlySummary(){ const y=document.getElementById('year').value,m=document.getElementById('month').value; document.getElementById('monthlyOut').textContent=JSON.stringify(await api('/api/admin/finance/reports/monthly-summary?year='+y+'&month='+m),null,2); }
async function monthlyPreview(){ const y=document.getElementById('year').value,m=document.getElementById('month').value; document.getElementById('monthlyOut').textContent=JSON.stringify(await api('/api/admin/finance/monthly-close/preview?year='+y+'&month='+m),null,2); }
async function monthlyRun(){ const y=document.getElementById('year').value,m=document.getElementById('month').value,t=document.getElementById('threshold').value; if(!confirm('Run monthly close?')) return; document.getElementById('monthlyOut').textContent=JSON.stringify(await api('/api/admin/finance/monthly-close/run?year='+y+'&month='+m+'&min_threshold='+t,{method:'POST'}),null,2); await loadAll(); }
async function sellerStatement(){ const sid=document.getElementById('sellerId').value; document.getElementById('sellerOut').textContent=JSON.stringify(await api('/api/admin/finance/reports/seller-statement?seller_id='+sid),null,2); }
function downloadSellerCsv(){ const sid=document.getElementById('sellerId').value; location.href='/api/admin/finance/reports/seller-statement.csv?seller_id='+sid; }
async function reconcile(){ document.getElementById('exportOut').textContent=JSON.stringify(await api('/api/admin/finance/reconciliation/check'),null,2); }
loadAll();
</script>
</body>
</html>
"""


@router.get('/admin/finance-reports-console', response_class=HTMLResponse)
def finance_reports_console():
    return HTMLResponse(REPORTS_HTML)


@router.get('/admin/finance-console/invoice/{invoice_id}/print', response_class=HTMLResponse)
def finance_invoice_print(invoice_id: int, db: Session = Depends(get_db)):
    inv = db.get(SellerInvoice, invoice_id)
    if not inv:
        raise HTTPException(status_code=404, detail='Invoice not found')
    seller = db.get(Store, inv.seller_id)
    lines = db.query(SellerInvoiceLine).filter(SellerInvoiceLine.invoice_id == invoice_id).all()
    payments = db.query(SellerInvoicePayment).filter(SellerInvoicePayment.seller_invoice_id == invoice_id).all()
    line_rows = ''.join(f'<tr><td>{l.description or l.line_type}</td><td>{_money(l.quantity)}</td><td>{_money(l.unit_amount)}</td><td>{_money(l.total_amount)} {l.currency or "RSD"}</td></tr>' for l in lines)
    payment_rows = ''.join(f'<tr><td>{p.provider}</td><td>{_money(p.amount)} {p.currency or "RSD"}</td><td>{p.status}</td><td>{_iso(p.payment_date) or ""}</td></tr>' for p in payments)
    html = f"""<!doctype html><html><head><meta charset="utf-8"><title>{inv.invoice_number}</title><style>body{{font-family:Arial;padding:32px}} .top{{display:flex;justify-content:space-between}} table{{width:100%;border-collapse:collapse;margin-top:16px}}td,th{{border-bottom:1px solid #ddd;padding:8px;text-align:left}} .total{{font-size:22px;font-weight:bold}} @media print{{button{{display:none}}}}</style></head><body><button onclick="window.print()">Print / Save PDF</button><div class="top"><div><h1>Food Saver Serbia</h1><p>Seller commission invoice</p></div><div><h2>{inv.invoice_number}</h2><p>Status: {inv.status}</p><p>Due date: {_iso(inv.due_date) or ''}</p></div></div><hr><h3>Seller</h3><p>{seller.name if seller else inv.seller_id}<br>{getattr(seller, 'city', '') if seller else ''}</p><h3>Invoice lines</h3><table><thead><tr><th>Description</th><th>Qty</th><th>Unit</th><th>Total</th></tr></thead><tbody>{line_rows}</tbody></table><h3>Payments</h3><table><thead><tr><th>Provider</th><th>Amount</th><th>Status</th><th>Date</th></tr></thead><tbody>{payment_rows or '<tr><td colspan="4">No payments</td></tr>'}</tbody></table><hr><p class="total">Total: {_money(inv.total_amount)} {inv.currency or 'RSD'}</p><p class="total">Paid: {_money(inv.amount_paid)} {inv.currency or 'RSD'}</p><p class="total">Due: {_money(inv.amount_due)} {inv.currency or 'RSD'}</p></body></html>"""
    return HTMLResponse(html)
