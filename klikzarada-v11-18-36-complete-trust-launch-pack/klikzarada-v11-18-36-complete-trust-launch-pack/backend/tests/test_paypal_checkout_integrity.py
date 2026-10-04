"""Provider responses are simulated; no live PayPal or production DB is used."""

import os
import sys
import unittest
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

from app.database import Base  # noqa: E402
from app.models import AdvertiserBudgetTransaction, PayPalCheckout, User  # noqa: E402
from app.ui_api import _complete_paypal_checkout  # noqa: E402


class PayPalCheckoutIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()
        self.advertiser = User(
            full_name="Test oglasivac", email="advertiser@example.test", password_hash="test-only",
            role="oglasivac", advertiser_budget_rsd=0,
        )
        self.db.add(self.advertiser)
        self.db.flush()
        self.checkout = PayPalCheckout(
            advertiser_id=self.advertiser.id, paypal_order_id="order-1", request_id="request-1",
            capture_request_id="capture-request-1", amount_rsd=1170, amount_eur=10,
            exchange_rate=117, currency="EUR", status="created",
        )
        self.db.add(self.checkout)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    @staticmethod
    def order(value="10.00", currency="EUR"):
        return {"id": "order-1", "purchase_units": [{"payments": {"captures": [{
            "id": "capture-1", "status": "COMPLETED",
            "amount": {"currency_code": currency, "value": value},
        }]}}]}

    def test_repeated_capture_credits_budget_only_once(self):
        self.assertTrue(_complete_paypal_checkout(self.db, self.checkout, self.order()))
        self.db.commit()
        self.assertFalse(_complete_paypal_checkout(self.db, self.checkout, self.order()))
        self.db.commit()

        self.db.refresh(self.advertiser)
        self.assertEqual(self.advertiser.advertiser_budget_rsd, 1170)
        self.assertEqual(self.db.query(AdvertiserBudgetTransaction).count(), 1)
        self.assertEqual(self.checkout.paypal_capture_id, "capture-1")

    def test_wrong_amount_or_currency_never_credits_budget(self):
        for order in (self.order(value="9.99"), self.order(currency="USD")):
            with self.subTest(order=order), self.assertRaises(HTTPException) as caught:
                _complete_paypal_checkout(self.db, self.checkout, order)
            self.assertEqual(caught.exception.status_code, 400)
            self.db.rollback()
            self.db.refresh(self.checkout)
            self.db.refresh(self.advertiser)
            self.assertEqual(self.advertiser.advertiser_budget_rsd, 0)
            self.assertEqual(self.db.query(AdvertiserBudgetTransaction).count(), 0)

    def test_capture_for_another_order_is_not_credited(self):
        order = self.order()
        order["id"] = "order-2"
        with self.assertRaises(HTTPException) as caught:
            _complete_paypal_checkout(self.db, self.checkout, order)
        self.assertEqual(caught.exception.status_code, 400)
        self.assertEqual(self.db.query(AdvertiserBudgetTransaction).count(), 0)
