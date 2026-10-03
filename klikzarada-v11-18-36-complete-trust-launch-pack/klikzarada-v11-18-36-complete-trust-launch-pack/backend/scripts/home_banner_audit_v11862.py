"""Focused audit for homepage banner timing and iOS task destination."""

import subprocess
import sys


if __name__ == "__main__":
    raise SystemExit(subprocess.call([
        sys.executable, "-m", "unittest", "tests.test_home_banner_delivery", "tests.test_content_revisions",
    ]))
