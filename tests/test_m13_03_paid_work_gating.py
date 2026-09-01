"""M13-03 — paid-work gating.

Part A (correction): GET /text/price-kpi runs a real OpenAI parse + full Serper
cascade with NO auth. It gets Depends(verify_admin_key) like its sibling debug
routes (DELETE /text/cache, GET /text/parse). Pin: unauthenticated -> 401/403,
never 200.

Part B (flag ENABLE_ANON_USAGE_GATE, default OFF): the freemium gate is extended
to anonymous callers on /text/quick and /image/identify, keyed on the
regex-validated X-Device-Fingerprint header. Flag-OFF = today (byte-identical).

Free-tier only; the comparison service / vision call are mocked so no network.
"""
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests._route_introspection import assert_route_table_visible, find_route

_VALID_FP = "a" * 64  # SHA-256 hex


@pytest.fixture()
def client():
    return TestClient(app)


# ---------------------------------------------------------------------------
# Part A — /text/price-kpi now requires the admin key
# ---------------------------------------------------------------------------

def test_price_kpi_rejects_wrong_admin_key(client):
    """A wrong X-Admin-Key -> 403 (ADMIN_API_KEY is unset in tests, so
    verify_admin_key rejects any key). Never reaches the paid pipeline."""
    resp = client.get(
        "/api/v1/text/price-kpi", params={"q": "iphone 15"},
        headers={"X-Admin-Key": "definitely-wrong"},
    )
    assert resp.status_code == 403, resp.text
    assert resp.status_code != 200


def test_price_kpi_rejects_missing_admin_header(client):
    """No X-Admin-Key header at all -> not a 200 (FastAPI 422 for the missing
    required header). The point is: no anonymous access to the paid endpoint."""
    resp = client.get("/api/v1/text/price-kpi", params={"q": "iphone 15"})
    assert resp.status_code in (401, 403, 422), resp.text
    assert resp.status_code != 200


def test_price_kpi_route_declares_admin_dependency():
    """Structural pin: verify_admin_key is a dependency of the route.

    THIS IS A SECURITY PIN — it must be able to go red. The old
    `next(r for r in app.routes if getattr(r, "path", "") == ...)` idiom could
    not: on the pinned fastapi 0.141 the route lives inside an `_IncludedRouter`
    wrapper with no `.path`, so the generator found nothing and raised
    StopIteration — an ERROR with no diagnostic, and the admin dependency went
    unverified in CI while the pin looked like it was doing its job.
    Route lookup now goes through the version-robust walker, and a missing
    route is an explicit assertion failure, not a StopIteration.
    """
    from app.api.admin_routes import verify_admin_key

    assert_route_table_visible(app)
    entry = find_route(app, "/api/v1/text/price-kpi", method="GET")
    assert entry is not None, (
        "GET /api/v1/text/price-kpi is not mounted at all -- the paid-work "
        "endpoint this pin guards has moved or been removed."
    )

    dep_calls = [d.call for d in entry.route.dependant.dependencies]
    assert verify_admin_key in dep_calls, (
        "GET /api/v1/text/price-kpi no longer declares "
        "Depends(verify_admin_key). It runs a real OpenAI parse + full Serper "
        f"cascade -- it must not be reachable anonymously. Dependencies seen: "
        f"{[getattr(c, '__name__', repr(c)) for c in dep_calls]}"
    )


# ---------------------------------------------------------------------------
# Part B — anonymous usage gate on /text/quick
# ---------------------------------------------------------------------------

def _stub_service(monkeypatch):
    """Patch the comparison service so /quick never hits the network."""
    svc = MagicMock()
    svc.compare_from_text = AsyncMock(
        return_value={"success": True, "products": [], "metadata": {}}
    )
    monkeypatch.setattr("app.api.text_routes.get_comparison_service", lambda: svc)
    return svc


def test_quick_flag_off_does_not_consult_gate(client, monkeypatch):
    """Flag OFF: byte-identical to today — the anon gate function is never
    called even with a valid fingerprint header, and the request proceeds."""
    monkeypatch.delenv("ENABLE_ANON_USAGE_GATE", raising=False)
    gate = AsyncMock(return_value={"allowed": False, "reason": "daily_limit",
                                   "tier": "free", "remaining": {}})
    monkeypatch.setattr("app.api.text_routes.check_anon_usage_allowed", gate)
    _stub_service(monkeypatch)

    resp = client.post(
        "/api/v1/text/quick",
        json={"product1": "a", "product2": "b"},
        headers={"X-Device-Fingerprint": _VALID_FP},
    )
    assert resp.status_code == 200, resp.text
    gate.assert_not_awaited()


def test_quick_flag_on_blocks_over_limit_device(client, monkeypatch):
    """Flag ON + valid fingerprint + over-limit -> 429 USAGE_LIMIT, and the paid
    comparison never runs."""
    monkeypatch.setenv("ENABLE_ANON_USAGE_GATE", "true")
    monkeypatch.setattr(
        "app.api.text_routes.check_anon_usage_allowed",
        AsyncMock(return_value={"allowed": False, "reason": "daily_limit",
                                "tier": "free", "remaining": {"daily": 0}}),
    )
    svc = _stub_service(monkeypatch)

    resp = client.post(
        "/api/v1/text/quick",
        json={"product1": "a", "product2": "b"},
        headers={"X-Device-Fingerprint": _VALID_FP},
    )
    assert resp.status_code == 429, resp.text
    assert resp.json().get("code") == "USAGE_LIMIT", resp.text
    svc.compare_from_text.assert_not_awaited()


def test_quick_flag_on_invalid_fingerprint_not_gated(client, monkeypatch):
    """Flag ON but a malformed X-Device-Fingerprint -> the gate does not apply
    (the regex rejects it), so the request proceeds. Proves the validation."""
    monkeypatch.setenv("ENABLE_ANON_USAGE_GATE", "true")
    gate = AsyncMock(return_value={"allowed": False, "reason": "daily_limit",
                                   "tier": "free", "remaining": {}})
    monkeypatch.setattr("app.api.text_routes.check_anon_usage_allowed", gate)
    _stub_service(monkeypatch)

    resp = client.post(
        "/api/v1/text/quick",
        json={"product1": "a", "product2": "b"},
        headers={"X-Device-Fingerprint": "NOT-A-VALID-FP"},
    )
    assert resp.status_code == 200, resp.text
    gate.assert_not_awaited()


def test_quick_flag_on_allowed_device_proceeds(client, monkeypatch):
    """Flag ON + valid fingerprint + under limit -> proceeds normally."""
    monkeypatch.setenv("ENABLE_ANON_USAGE_GATE", "true")
    monkeypatch.setattr(
        "app.api.text_routes.check_anon_usage_allowed",
        AsyncMock(return_value={"allowed": True, "reason": None,
                                "tier": "free", "remaining": {"daily": 2}}),
    )
    _stub_service(monkeypatch)

    resp = client.post(
        "/api/v1/text/quick",
        json={"product1": "a", "product2": "b"},
        headers={"X-Device-Fingerprint": _VALID_FP},
    )
    assert resp.status_code == 200, resp.text


# ---------------------------------------------------------------------------
# Part B — anonymous usage gate on /image/identify (gates before the Vision call)
# ---------------------------------------------------------------------------

def test_image_flag_on_blocks_before_vision(client, monkeypatch):
    """Flag ON + valid fingerprint + over-limit -> 429 before identify_products
    (the paid Vision call) is ever made."""
    monkeypatch.setenv("ENABLE_ANON_USAGE_GATE", "true")
    monkeypatch.setattr(
        "app.api.image_routes.check_anon_usage_allowed",
        AsyncMock(return_value={"allowed": False, "reason": "daily_limit",
                                "tier": "free", "remaining": {"daily": 0}}),
    )
    vision = AsyncMock(return_value={"products": [], "cost": 0})
    monkeypatch.setattr("app.api.image_routes.identify_products", vision)

    jpeg = b"\xff\xd8\xff\xe0" + b"0" * 32
    resp = client.post(
        "/api/v1/image/identify",
        files=[("images", ("a.jpg", jpeg, "image/jpeg"))],
        headers={"X-Device-Fingerprint": _VALID_FP},
    )
    assert resp.status_code == 429, resp.text
    assert resp.json().get("code") == "USAGE_LIMIT", resp.text
    vision.assert_not_awaited()


def test_image_flag_off_no_gate(client, monkeypatch):
    """Flag OFF: the anon gate function is never consulted even with a valid
    fingerprint (byte-identical to today)."""
    monkeypatch.delenv("ENABLE_ANON_USAGE_GATE", raising=False)
    gate = AsyncMock(return_value={"allowed": False, "reason": "daily_limit",
                                   "tier": "free", "remaining": {}})
    monkeypatch.setattr("app.api.image_routes.check_anon_usage_allowed", gate)
    # Vision returns 0 products -> the handler returns an "error" action at 200
    # without any network; we only care that the gate was not consulted.
    monkeypatch.setattr(
        "app.api.image_routes.identify_products",
        AsyncMock(return_value={"products": [], "cost": 0}),
    )

    jpeg = b"\xff\xd8\xff\xe0" + b"0" * 32
    resp = client.post(
        "/api/v1/image/identify",
        files=[("images", ("a.jpg", jpeg, "image/jpeg"))],
        headers={"X-Device-Fingerprint": _VALID_FP},
    )
    assert resp.status_code == 200, resp.text
    gate.assert_not_awaited()
