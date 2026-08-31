"""M13-21 — /openapi.json must be suppressed in the Railway (production) env.

FastAPI(docs_url=None, redoc_url=None) still registers /openapi.json, so the
full contract — all admin endpoints, the X-Admin-Key header, the debug routes,
every request-model constraint — was world-readable in prod. Gate openapi_url on
RAILWAY_ENVIRONMENT, keeping it served for local dev + the test suite.
"""
from fastapi import FastAPI
from fastapi.testclient import TestClient


def test_openapi_url_helper_none_when_railway_env_set(monkeypatch):
    import app.main as main

    monkeypatch.setenv("RAILWAY_ENVIRONMENT", "production")
    assert main._openapi_url() is None


def test_openapi_url_helper_served_when_unset(monkeypatch):
    import app.main as main

    monkeypatch.delenv("RAILWAY_ENVIRONMENT", raising=False)
    assert main._openapi_url() == "/openapi.json"


def test_openapi_none_yields_404():
    """Contract: openapi_url=None de-registers the route -> 404 (the behaviour a
    RAILWAY_ENVIRONMENT deploy now gets)."""
    gated = FastAPI(openapi_url=None)
    assert TestClient(gated).get("/openapi.json").status_code == 404


def test_openapi_served_in_test_env():
    """RAILWAY_ENVIRONMENT is unset in the test suite, so the live app keeps
    serving the schema (local dev + tests unaffected)."""
    from app.main import app

    resp = TestClient(app).get("/openapi.json")
    assert resp.status_code == 200
    assert resp.json().get("openapi")
