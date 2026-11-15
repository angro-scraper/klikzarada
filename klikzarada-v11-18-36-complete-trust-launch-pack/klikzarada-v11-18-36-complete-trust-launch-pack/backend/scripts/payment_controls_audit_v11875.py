"""Ponovljiva provera kontrola uplata i isplata bez pristupa pravoj banci."""

import subprocess
import sys


if __name__ == "__main__":
    for command in (
        [sys.executable, "-m", "compileall", "-q", "app/main.py", "app/ui_api.py", "app/models.py"],
        [sys.executable, "-m", "pytest", "-q", "--disable-warnings", "tests/test_bank_payment_controls.py",
         "tests/test_paypal_checkout_integrity.py", "tests/test_referral_payout.py"],
    ):
        result = subprocess.call(command)
        if result:
            raise SystemExit(result)
    raise SystemExit(0)
