"""Focused regression checks for the one-time platform banner activation."""

import subprocess
import sys


if __name__ == "__main__":
    raise SystemExit(subprocess.call([
        sys.executable, "-m", "unittest", "tests.test_home_banner_delivery",
        "tests.test_content_revisions",
    ]))
