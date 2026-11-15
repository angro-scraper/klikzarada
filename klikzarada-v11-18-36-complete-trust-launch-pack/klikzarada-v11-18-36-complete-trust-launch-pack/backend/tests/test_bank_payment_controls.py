"""Financial controls use an isolated database; no bank or provider is contacted."""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

from app.database import Base, get_db  # noqa: E402
from app import main, ui_api  # noqa: E402
from app.bank_accounts import company_bank_config  # noqa: E402
from app.models import (  # noqa: E402
    AdvertiserBudgetTransaction, BankPayoutSettlement, BankTransferConfirmation,
    FraudSignalV11, PaymentIntentV8, PayoutBatchItem, PayoutMethodV11, SystemSetting, User, Withdrawal,
)


class BankPaymentControlsTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.sessions = sessionmaker(bind=self.engine)

        def test_db():
            with self.sessions() as db:
                yield db

        main.app.dependency_overrides[get_db] = test_db
        self.client = TestClient(main.app)
        with self.sessions() as db:
            advertiser = User(full_name="Oglasivac", email="adv@example.test", password_hash="test", role="oglasivac", advertiser_budget_rsd=0)
            admin = User(full_name="Admin", email="admin@example.test", password_hash="test", role="admin")
            earner = User(full_name="Korisnik", email="user@example.test", password_hash="test", role="korisnik", balance_rsd=0)
            db.add_all([advertiser, admin, earner])
            db.flush()
            self.admin_id = admin.id
            self.earner_id = earner.id
            db.add_all([
                PaymentIntentV8(advertiser_id=advertiser.id, amount_rsd=1200, reference="CARD-1", method="card", status="pending"),
                PaymentIntentV8(advertiser_id=advertiser.id, amount_rsd=800, reference="BANK-1", method="bank_transfer", status="pending"),
            ])
            db.commit()

    def tearDown(self):
        self.client.close()
        main.app.dependency_overrides.clear()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def webhook(self, reference="CARD-1", amount="1200", currency="RSD", secret="secret", status="paid"):
        return self.client.post("/api/v1/payments/webhook", json={
            "reference": reference, "amount": amount, "currency": currency, "status": status,
        }, headers={"x-kz-webhook-secret": secret})

    def test_webhook_requires_configuration_and_exact_payment(self):
        with patch.object(main, "v11847_payment_provider_config", return_value={"webhook_secret": ""}):
            self.assertEqual(self.webhook().status_code, 503)
        with patch.object(main, "v11847_payment_provider_config", return_value={"webhook_secret": "secret"}):
            self.assertEqual(self.webhook(secret="wrong").status_code, 401)
            self.assertEqual(self.webhook(amount="1201").status_code, 400)
            self.assertEqual(self.webhook(currency="EUR").status_code, 400)
            self.assertEqual(self.webhook(reference="BANK-1", amount="800").status_code, 409)
            self.assertEqual(self.webhook().status_code, 200)
            self.assertEqual(self.webhook().status_code, 200)
            self.assertEqual(self.webhook(status="failed").status_code, 200)
        with self.sessions() as db:
            card = db.query(PaymentIntentV8).filter_by(reference="CARD-1").one()
            self.assertEqual(card.status, "confirmed")
            self.assertEqual(card.advertiser.advertiser_budget_rsd, 1200)
            self.assertEqual(db.query(AdvertiserBudgetTransaction).count(), 1)

    def test_bank_confirmation_requires_statement_evidence_and_unique_reference(self):
        with self.sessions() as db:
            admin = db.get(User, self.admin_id)
        with patch.object(main, "require", return_value=admin), patch.object(main, "check_role"):
            path = "/admin/payments-v8/2/confirm"
            self.assertEqual(self.client.post(path, data={"bank_reference": "STAT-1", "statement_amount_rsd": "799"}).status_code, 400)
            self.assertEqual(self.client.post(path, data={"bank_reference": "", "statement_amount_rsd": "800"}).status_code, 400)
            self.assertEqual(self.client.post(path, data={"bank_reference": "STAT-1", "statement_amount_rsd": "800"}, follow_redirects=False).status_code, 303)
        with self.sessions() as db:
            bank = db.query(PaymentIntentV8).filter_by(reference="BANK-1").one()
            self.assertEqual(bank.advertiser.advertiser_budget_rsd, 800)
            self.assertEqual(db.query(BankTransferConfirmation).count(), 1)

    def test_bank_payout_needs_verified_account_and_reference(self):
        with self.sessions() as db:
            user = db.get(User, self.earner_id)
            admin = db.get(User, self.admin_id)
            withdrawal = Withdrawal(user_id=user.id, amount_rsd=1000, payment_method="bank_transfer", payment_details="123-1234567890123-12", status="pending")
            db.add(withdrawal)
            db.commit()
            self.assertEqual(main.v11832_pay_withdrawal(db, admin, withdrawal, "STAT-PAY-1"), "payout_method_not_ready")
            db.add(PayoutMethodV11(user_id=user.id, method_type="bank", account_holder=user.full_name,
                                   account_data=withdrawal.payment_details, status="verified"))
            db.commit()
            self.assertEqual(main.v11832_pay_withdrawal(db, admin, withdrawal, ""), "bank_reference_required")
            self.assertEqual(main.v11832_pay_withdrawal(db, admin, withdrawal, "STAT-PAY-1"), "paid")
            self.assertEqual(main.v11832_pay_withdrawal(db, admin, withdrawal, "STAT-PAY-1"), "already_paid")
            self.assertEqual(db.query(BankPayoutSettlement).count(), 1)

    def test_legacy_direct_topup_cannot_credit_budget(self):
        with self.sessions() as db:
            advertiser = db.query(User).filter_by(email="adv@example.test").one()
            admin = db.get(User, self.admin_id)
            self.assertEqual(main.v11833_admin_topup(db, admin, advertiser, 2000, "test"), "use_payment_intent")
            db.refresh(advertiser)
            self.assertEqual(advertiser.advertiser_budget_rsd, 0)
            self.assertEqual(db.query(AdvertiserBudgetTransaction).count(), 0)

    def test_payment_request_rejects_invalid_method_and_amount(self):
        with self.sessions() as db:
            advertiser = db.query(User).filter_by(email="adv@example.test").one()
        with patch.object(main, "require", return_value=advertiser), patch.object(main, "check_role"):
            for amount, method in (("nan", "bank_transfer"), ("inf", "bank_transfer"),
                                   ("1200.001", "bank_transfer"), ("1200", "unknown")):
                response = self.client.post("/oglasivac/payments-v8/create",
                                            data={"amount_rsd": amount, "method": method}, follow_redirects=False)
                self.assertEqual(response.status_code, 400)
        with self.sessions() as db:
            self.assertEqual(db.query(PaymentIntentV8).count(), 2)

    def test_company_bank_account_is_disabled_until_real_configuration(self):
        with self.sessions() as db:
            db.add(SystemSetting(key="advertiser_payment_account", value="Dodaj broj računa u adminu"))
            db.commit()
            self.assertFalse(company_bank_config(db)["bank_payments_ready"])
            advertiser = db.query(User).filter_by(email="adv@example.test").one()
        with patch.object(main, "require", return_value=advertiser), patch.object(main, "check_role"):
            response = self.client.post("/oglasivac/payments-v8/create",
                                        data={"amount_rsd": "1200", "method": "bank_transfer"})
            self.assertEqual(response.status_code, 409)
        with self.sessions() as db:
            self.assertEqual(db.query(PaymentIntentV8).count(), 2)

    def test_bank_payout_is_separate_from_paypal_and_requires_verified_method(self):
        with self.sessions() as db:
            user = db.get(User, self.earner_id)
            user.balance_rsd = 1500
            user.payment_method = "PayPal"
            user.payment_details = "old@example.test"
            db.commit()
        with patch.object(ui_api, "_require_user", side_effect=lambda request, db, roles: db.get(User, self.earner_id)):
            saved = self.client.put("/api/ui/user/bank-payout-method",
                                    json={"account_number": "123-0000000000000-45"})
            self.assertEqual(saved.status_code, 200)
            self.assertEqual(saved.json()["method"], {"status": "pending", "last_four": "0045"})
            first = self.client.post("/api/ui/user/withdrawals", json={
                "amount_rsd": 1000, "payment_method": "bank_transfer", "payment_details": "verified",
            })
            self.assertEqual(first.status_code, 409)
            with self.sessions() as db:
                db.add_all([
                    SystemSetting(key="user_payout_account", value="123000000000000045"),
                    SystemSetting(key="user_payout_holder", value="AMIA"),
                ])
                method = db.query(PayoutMethodV11).filter_by(user_id=self.earner_id).one()
                method.status = "verified"
                db.commit()
            second = self.client.post("/api/ui/user/withdrawals", json={
                "amount_rsd": 1000, "payment_method": "bank_transfer", "payment_details": "verified",
            })
            self.assertEqual(second.status_code, 201)
        with self.sessions() as db:
            user = db.get(User, self.earner_id)
            self.assertEqual(user.balance_rsd, 500)
            self.assertEqual(user.payment_details, "old@example.test")
            self.assertEqual(db.query(Withdrawal).filter_by(payment_method="bank_transfer").one().payment_details,
                             "123000000000000045")

    def test_mobile_bank_deposit_waits_for_company_account_and_bank_statement(self):
        with patch.object(ui_api, "_require_user", side_effect=lambda request, db, roles: db.query(User).filter_by(email="adv@example.test").one()):
            unavailable = self.client.post("/api/ui/advertiser/bank-payment", json={"amount_rsd": 1200})
            self.assertEqual(unavailable.status_code, 409)
            with self.sessions() as db:
                db.add_all([
                    SystemSetting(key="advertiser_payment_account", value="123000000000000045"),
                    SystemSetting(key="advertiser_payment_holder", value="AMIA"),
                ])
                db.commit()
            created = self.client.post("/api/ui/advertiser/bank-payment", json={"amount_rsd": 1200})
            self.assertEqual(created.status_code, 201)
            self.assertEqual(created.json()["intent"]["status"], "pending")
            self.assertEqual(self.client.get("/api/ui/advertiser/bank-payment").json()["account"], "123000000000000045")
        with self.sessions() as db:
            advertiser = db.query(User).filter_by(email="adv@example.test").one()
            self.assertEqual(advertiser.advertiser_budget_rsd, 0)
            self.assertEqual(db.query(AdvertiserBudgetTransaction).count(), 0)

    def test_high_risk_user_excluded_from_bank_payout_queue(self):
        with self.sessions() as db:
            user = db.get(User, self.earner_id)
            admin = db.get(User, self.admin_id)
            withdrawal = Withdrawal(user_id=user.id, amount_rsd=1000, payment_method="bank_transfer",
                                    payment_details="123-1234567890123-12", status="pending")
            db.add_all([withdrawal, PayoutMethodV11(user_id=user.id, method_type="bank",
                account_holder=user.full_name, account_data=withdrawal.payment_details, status="verified")])
            db.add(FraudSignalV11(user_id=user.id, signal_type="test", risk_score=90, status="open"))
            db.commit()
            self.assertEqual(main.v11832_pay_withdrawal(db, admin, withdrawal, "PAY-RISK-1"), "payout_method_not_ready")
            self.assertEqual(db.query(BankPayoutSettlement).count(), 0)
            self.assertEqual(db.query(PayoutBatchItem).count(), 0)


if __name__ == "__main__":
    unittest.main()
