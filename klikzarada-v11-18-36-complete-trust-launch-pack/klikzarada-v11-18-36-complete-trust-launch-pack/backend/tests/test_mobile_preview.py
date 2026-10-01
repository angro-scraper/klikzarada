import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from fastapi.testclient import TestClient

from app import main


class MobilePreviewTests(unittest.TestCase):
    def test_separate_mobile_entry_uses_existing_protected_api(self):
        with TemporaryDirectory() as directory, patch.object(main, "MOBILE_DIR", Path(directory)):
            (Path(directory) / "index.html").write_text("<html>mobile shell</html>", encoding="utf-8")
            client = TestClient(main.app)
            response = client.get("/mobilna", headers={"accept": "text/html"})
            self.assertEqual(response.status_code, 200)
            self.assertIn("mobile shell", response.text)
            self.assertIn("no-store", response.headers["cache-control"])
            self.assertEqual(client.get("/api/ui/user/dashboard").status_code, 401)


if __name__ == "__main__":
    unittest.main()
