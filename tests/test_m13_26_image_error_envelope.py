"""M13-26 — the camera comparison path returned raw str(e) to the client, which
routinely embeds hostnames, table names, Postgres codes and upstream URLs. Mirror
_surface_comparison_failure in text_routes: a constant user message + request_id
on the wire, str(e) only to the log/Sentry path.
"""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app

_SECRET = "SECRET_DB_HOST_internal.db.invalid:5432 table=users code=42P01"


@pytest.fixture()
def client():
    return TestClient(app)


def _two_product_vision(monkeypatch):
    """Make vision return 2 products and content-safety allow, so the handler
    reaches the auto-compare branch."""
    monkeypatch.setattr(
        "app.api.image_routes.identify_products",
        AsyncMock(return_value={
            "products": [{"brand": "A", "name": "x"}, {"brand": "B", "name": "y"}],
            "cost": 0,
        }),
    )
    safety = MagicMock()
    safety.moderate_vision_output = AsyncMock(return_value=SimpleNamespace(allowed=True))
    monkeypatch.setattr(
        "app.services.content_safety_service.get_content_safety_service",
        lambda: safety,
    )


def test_internal_error_is_not_leaked_to_client(client, monkeypatch):
    _two_product_vision(monkeypatch)
    # The comparison raises an internal error carrying secret infrastructure detail.
    svc = MagicMock()
    svc.compare_from_text = AsyncMock(side_effect=Exception(_SECRET))
    monkeypatch.setattr("app.api.image_routes.StructuredComparisonService", lambda *a, **k: svc)

    jpeg = b"\xff\xd8\xff\xe0" + b"0" * 32
    resp = client.post(
        "/api/v1/image/identify",
        files=[
            ("images", ("a.jpg", jpeg, "image/jpeg")),
            ("images", ("b.jpg", jpeg, "image/jpeg")),
        ],
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()

    # The raw exception text must NOT appear anywhere in the response body.
    assert _SECRET not in resp.text
    assert "42P01" not in resp.text
    assert "internal.db.invalid" not in resp.text

    # Unified-envelope shape: constant message + request_id, and the fallback
    # contract (action + products) is preserved for the text-compare fallback.
    assert body["action"] == "comparison_failed"
    assert body.get("request_id")
    assert isinstance(body.get("error"), str) and body["error"]
    assert "products" in body
