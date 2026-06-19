from __future__ import annotations

"""
Optional WSGI entrypoint for DirectAdmin/Passenger-style Python hosting.

FastAPI is ASGI. If the hosting panel only accepts WSGI, install
requirements-adriahost.txt so a2wsgi can adapt the app.
"""

try:
    from a2wsgi import ASGIMiddleware
except Exception as exc:  # pragma: no cover - only used on hosting
    raise RuntimeError("Install requirements-adriahost.txt before starting Passenger.") from exc

from app.main import app as asgi_app


application = ASGIMiddleware(asgi_app)
