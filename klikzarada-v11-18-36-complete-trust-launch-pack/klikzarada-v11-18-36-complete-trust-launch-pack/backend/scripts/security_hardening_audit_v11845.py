"""Run the isolated V11.18.45 security regression suite."""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


backend = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend))

from app import database, main  # noqa: E402

assert main.app.version == "11.18.45"
engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
sessions = sessionmaker(bind=engine)
with patch.object(database, "SessionLocal", sessions), patch.object(main, "SessionLocal", sessions), patch.object(main, "engine", engine):
    with TestClient(main.app) as client:
        assert client.get("/openapi.json").status_code == 200
engine.dispose()

suite = unittest.defaultTestLoader.discover(str(backend / "tests"), pattern="test_security_hardening.py")
result = unittest.TextTestRunner(verbosity=2).run(suite)
if not result.wasSuccessful():
    raise SystemExit(1)
