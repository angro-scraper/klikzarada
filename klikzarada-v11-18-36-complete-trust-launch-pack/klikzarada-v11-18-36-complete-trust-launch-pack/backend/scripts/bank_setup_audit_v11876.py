"""Provera bankarskog setup-a bez pristupa stvarnim racunima."""

import subprocess
import sys


if __name__ == "__main__":
    for command in (
        [sys.executable, "-m", "compileall", "-q", "app/main.py", "app/ui_api.py", "app/bank_accounts.py"],
        [sys.executable, "-m", "pytest", "-q", "--disable-warnings", "tests/test_bank_payment_controls.py"],
        [sys.executable, "-c", "from app.main import app; assert app.version == '11.18.76'"],
    ):
        code = subprocess.call(command)
        if code:
            raise SystemExit(code)
