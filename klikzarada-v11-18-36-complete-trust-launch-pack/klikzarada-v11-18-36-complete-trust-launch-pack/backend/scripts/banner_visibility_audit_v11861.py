"""Focused regression audit for banner visibility and the iOS task route."""

import subprocess
import sys


if __name__ == "__main__":
    raise SystemExit(subprocess.call([sys.executable, "-m", "unittest", "tests.test_content_revisions"]))
