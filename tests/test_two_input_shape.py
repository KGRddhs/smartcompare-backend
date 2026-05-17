"""
Backend regression for the dual-shape `/api/v1/text/compare` endpoint.

Spec ref: docs/superpowers/specs/2026-05-17-bundle-b-two-input-ux-design.md § 5.1.
Plan ref: docs/superpowers/plans/2026-05-17-bundle-b-two-input-ux.md § 3.2.

Coverage target: 100% of `TextCompareRequest.normalize_shape` model_validator.

Mock strategy
- TestClient(app) for endpoint-level Pydantic validation.
- Service layer mocked via monkeypatch on `app.api.text_routes.get_comparison_service`.
- `parse_product_query` spy via monkeypatch on
  `app.services.structured_comparison_service.parse_product_query`.

Phase 1 vs Phase 3 split
- Pydantic shape acceptance (validator branches) — Backend § 1.3 has LANDED.
  These tests go GREEN immediately on commit.
- `explicit_pair` propagation + L1/L3 interception — Backend § 1.4 still
  pending. Those tests are RED until Backend wires the kwarg.
- SSE endpoint dual-shape — Backend § 1.4 streaming-endpoint widen still
  pending. Those tests are RED until then.
- Live Railway tests are marked `@pytest.mark.live_unit` (skipped by default).
"""
from __future__ import annotations

import os
from typing import Any, Optional
from unittest.mock import AsyncMock, MagicMock

# OpenAI client instantiates at import time inside app.services.openai_service;
# tests don't issue any real OpenAI requests (compare_from_text is mocked).
os.environ.setdefault("OPENAI_API_KEY", "test-key-noop-two-input-shape")

import pytest
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """Mirror tests/test_security_regression.py's autouse — slowapi caps the
    /text/compare endpoint at 10/min by IP. Reset between every test so we
    don't see flaky 429s when running many tests in sequence."""
    from app.middleware.rate_limiter import limiter

    try:
        limiter.reset()
    except Exception:  # noqa: BLE001
        pass
    yield


def _mock_success_response() -> dict[str, Any]:
    return {
        "success": True,
        "products": [
            {"brand": "Apple", "name": "iPhone 15"},
            {"brand": "Samsung", "name": "Galaxy S24"},
        ],
        "metadata": {"total_cost": 0.001},
    }


@pytest.fixture
def mock_service(monkeypatch):
    """Patch get_comparison_service to return a controlled mock."""
    service = MagicMock()
    service.compare_from_text = AsyncMock(return_value=_mock_success_response())
    monkeypatch.setattr(
        "app.api.text_routes.get_comparison_service", lambda: service
    )
    return service


@pytest.fixture
def parse_spy(monkeypatch):
    """Spy on parse_product_query at the service module level."""
    spy = AsyncMock(
        return_value=(
            {
                "products": [
                    {"brand": "Apple", "name": "iPhone 15", "category": "electronics", "search_query": "iPhone 15"},
                    {"brand": "Samsung", "name": "Galaxy S24", "category": "electronics", "search_query": "Galaxy S24"},
                ]
            },
            None,
        )
    )
    monkeypatch.setattr(
        "app.services.structured_comparison_service.parse_product_query", spy
    )
    return spy


# ============================================
# § 1.3 normalize_shape — Pydantic validator branches
# (these should be GREEN immediately — Backend § 1.3 has landed)
# ============================================


class TestPydanticShapeAcceptance:
    def test_query_only_shape_accepted(self, mock_service):
        response = client.post(
            "/api/v1/text/compare",
            json={"query": "iPhone 15 vs Galaxy S24"},
        )
        assert response.status_code == 200

    def test_product_a_b_only_shape_accepted(self, mock_service):
        response = client.post(
            "/api/v1/text/compare",
            json={"product_a": "iPhone 15", "product_b": "Galaxy S24"},
        )
        assert response.status_code == 200

    def test_both_shapes_rejected(self, mock_service):
        response = client.post(
            "/api/v1/text/compare",
            json={
                "query": "X vs Y",
                "product_a": "X",
                "product_b": "Y",
            },
        )
        assert response.status_code == 422
        body = response.json()
        body_text = str(body).lower()
        assert "either" in body_text and "or" in body_text

    def test_neither_shape_rejected(self, mock_service):
        response = client.post("/api/v1/text/compare", json={})
        assert response.status_code == 422
        body_text = str(response.json()).lower()
        assert "product_a" in body_text or "product_b" in body_text or "query" in body_text

    def test_product_a_only_rejected(self, mock_service):
        response = client.post(
            "/api/v1/text/compare",
            json={"product_a": "iPhone 15"},
        )
        assert response.status_code == 422

    def test_product_b_only_rejected(self, mock_service):
        response = client.post(
            "/api/v1/text/compare",
            json={"product_b": "Galaxy S24"},
        )
        assert response.status_code == 422

    def test_empty_product_a_rejected(self, mock_service):
        response = client.post(
            "/api/v1/text/compare",
            json={"product_a": "", "product_b": "Galaxy S24"},
        )
        assert response.status_code == 422

    def test_whitespace_only_product_a_rejected(self, mock_service):
        response = client.post(
            "/api/v1/text/compare",
            json={"product_a": "   ", "product_b": "Galaxy S24"},
        )
        assert response.status_code == 422

    def test_whitespace_only_product_b_rejected(self, mock_service):
        response = client.post(
            "/api/v1/text/compare",
            json={"product_a": "iPhone 15", "product_b": "   "},
        )
        assert response.status_code == 422

    def test_whitespace_only_query_rejected(self, mock_service):
        response = client.post(
            "/api/v1/text/compare",
            json={"query": "   "},
        )
        assert response.status_code == 422


# ============================================
# § 1.3 normalized query synthesis + handler routing
# (mock-service assertions for the values passed to the service)
# ============================================


class TestQuerySynthesis:
    def test_synthesized_query_format(self, mock_service):
        response = client.post(
            "/api/v1/text/compare",
            json={"product_a": "iPhone 15", "product_b": "Galaxy S24"},
        )
        assert response.status_code == 200
        # Synthesized "iPhone 15 vs Galaxy S24" per § 1.3 line 65 of text_routes.py
        call_kwargs = mock_service.compare_from_text.await_args.kwargs
        assert call_kwargs["query"] == "iPhone 15 vs Galaxy S24"

    def test_synthesized_query_strips_inputs(self, mock_service):
        response = client.post(
            "/api/v1/text/compare",
            json={"product_a": "  iPhone 15  ", "product_b": "  Galaxy S24  "},
        )
        assert response.status_code == 200
        call_kwargs = mock_service.compare_from_text.await_args.kwargs
        assert call_kwargs["query"] == "iPhone 15 vs Galaxy S24"

    def test_explicit_pair_kwarg_propagates(self, mock_service):
        response = client.post(
            "/api/v1/text/compare",
            json={"product_a": "iPhone 15", "product_b": "Galaxy S24"},
        )
        assert response.status_code == 200
        call_kwargs = mock_service.compare_from_text.await_args.kwargs
        assert call_kwargs.get("explicit_pair") == ("iPhone 15", "Galaxy S24")

    def test_query_path_no_explicit_pair_kwarg(self, mock_service):
        response = client.post(
            "/api/v1/text/compare",
            json={"query": "iPhone 15 vs Galaxy S24"},
        )
        assert response.status_code == 200
        call_kwargs = mock_service.compare_from_text.await_args.kwargs
        assert call_kwargs.get("explicit_pair") is None


# ============================================
# Spy on parse_product_query — RED until Backend § 1.4 wires the skip
# ============================================


class TestParseProductQueryRouting:
    """Pins Backend § 1.4 Change 2: when explicit_pair is provided, the
    service must skip parse_product_query() entirely."""

    def test_parse_product_query_called_for_legacy_query(self, mock_service, parse_spy):
        # mock_service.compare_from_text is itself mocked so it never reaches
        # the real service body — the spy fires ONLY when the real service
        # body runs. To verify the legacy path *would* call parse_product_query,
        # we hit the real service by NOT mocking it.
        # Strategy: undo the mock_service patch for this specific assertion
        # by directly calling the real service with a query.
        import asyncio

        from app.services.structured_comparison_service import get_comparison_service

        service = get_comparison_service()
        try:
            asyncio.run(service.compare_from_text(query="iPhone 15 vs Galaxy S24"))
        except Exception:
            # Spy fires before any downstream failure — that's fine for
            # this assertion.
            pass
        assert parse_spy.await_count >= 1, (
            "parse_product_query should be called when only `query` is provided"
        )

    def test_parse_product_query_not_called_for_explicit_pair(self, parse_spy):
        """Backend § 1.4: explicit_pair short-circuits the GPT parser."""
        import asyncio

        from app.services.structured_comparison_service import get_comparison_service

        service = get_comparison_service()
        try:
            asyncio.run(
                service.compare_from_text(
                    query="iPhone 15 vs Galaxy S24",
                    explicit_pair=("iPhone 15", "Galaxy S24"),
                )
            )
        except Exception:
            pass
        assert parse_spy.await_count == 0, (
            "Backend § 1.4: explicit_pair must skip parse_product_query()"
        )


# ============================================
# SSE endpoint dual-shape parity — RED until Backend § 1.4 widens streaming
# ============================================


class TestSseEndpointDualShape:
    """Spec § 5.1 + Plan § 3.2 — streaming endpoint must accept pair-shape too.
    Currently only accepts `q=` — these tests fail until Backend widens it."""

    def test_sse_endpoint_accepts_query_shape(self, mock_service):
        # Regression — existing `q=` param still works.
        # Streaming endpoint requires a controlled service; we only assert
        # the route accepts the request shape (200 OR a startup error from
        # the mock not yielding events).
        response = client.get(
            "/api/v1/text/compare/stream",
            params={"q": "iPhone 15 vs Galaxy S24"},
        )
        # Either 200 (stream opens then closes) or a 5xx if the mock is
        # incompatible with the streaming generator. NOT 422 (the route
        # accepts the shape).
        assert response.status_code != 422

    @pytest.mark.xfail(
        reason="Backend § 1.4 streaming-endpoint widen not yet shipped",
        strict=False,
    )
    def test_sse_endpoint_accepts_pair_shape(self, mock_service):
        response = client.get(
            "/api/v1/text/compare/stream",
            params={"product_a": "iPhone 15", "product_b": "Galaxy S24"},
        )
        assert response.status_code != 422

    @pytest.mark.xfail(
        reason="Backend § 1.4 streaming-endpoint widen not yet shipped",
        strict=False,
    )
    def test_sse_endpoint_rejects_both_shapes(self, mock_service):
        response = client.get(
            "/api/v1/text/compare/stream",
            params={
                "q": "X vs Y",
                "product_a": "X",
                "product_b": "Y",
            },
        )
        assert response.status_code == 422

    def test_sse_endpoint_rejects_neither_shape(self, mock_service):
        # `q=` is currently a required FastAPI Query param, so the route
        # 422s on no params today. When Backend widens to dual-shape with
        # a model_validator this assertion still holds.
        response = client.get("/api/v1/text/compare/stream")
        assert response.status_code == 422

    @pytest.mark.xfail(
        reason="Backend § 1.4 streaming-endpoint widen not yet shipped",
        strict=False,
    )
    def test_sse_endpoint_propagates_explicit_pair_to_service(self, mock_service):
        # Mock compare_from_text_streaming as an async generator.
        async def _empty_stream(*args, **kwargs):
            mock_service._captured_kwargs = kwargs
            if False:
                yield  # pragma: no cover

        mock_service.compare_from_text_streaming = _empty_stream
        response = client.get(
            "/api/v1/text/compare/stream",
            params={"product_a": "iPhone 15", "product_b": "Galaxy S24"},
        )
        assert response.status_code != 422
        captured = getattr(mock_service, "_captured_kwargs", {})
        assert captured.get("explicit_pair") == ("iPhone 15", "Galaxy S24")


# ============================================
# Region + optional fields preserved across both shapes
# ============================================


class TestOptionalFieldsPreserved:
    def test_pair_shape_with_region_uae(self, mock_service):
        client.post(
            "/api/v1/text/compare",
            json={"product_a": "iPhone 15", "product_b": "Galaxy S24", "region": "uae"},
        )
        call_kwargs = mock_service.compare_from_text.await_args.kwargs
        assert call_kwargs["region"] == "uae"

    def test_pair_shape_with_selected_category(self, mock_service):
        client.post(
            "/api/v1/text/compare",
            json={
                "product_a": "iPhone 15",
                "product_b": "Galaxy S24",
                "selected_category": "Electronics",
            },
        )
        call_kwargs = mock_service.compare_from_text.await_args.kwargs
        assert call_kwargs["selected_category"] == "Electronics"

    def test_pair_shape_with_invalid_selected_category(self, mock_service):
        # Per CLAUDE.md "soft validation" — selected_category is a hint only.
        response = client.post(
            "/api/v1/text/compare",
            json={
                "product_a": "iPhone 15",
                "product_b": "Galaxy S24",
                "selected_category": "NotARealCategory",
            },
        )
        assert response.status_code == 200

    def test_pair_shape_defaults_preserved(self, mock_service):
        client.post(
            "/api/v1/text/compare",
            json={"product_a": "iPhone 15", "product_b": "Galaxy S24"},
        )
        call_kwargs = mock_service.compare_from_text.await_args.kwargs
        assert call_kwargs["include_specs"] is True
        assert call_kwargs["include_reviews"] is True
        assert call_kwargs["include_pros_cons"] is True
        assert call_kwargs["region"] == "bahrain"


# ============================================
# Content moderation interception — RED until Backend § 1.4 wires L1
# ============================================


class TestContentSafetyInterception:
    """Pins Backend § 1.4 sync-path L1 block. The handler must consult
    content_safety_service before invoking the comparison service."""

    @pytest.mark.xfail(
        reason="Backend § 1.4 L1 service-level block works, but text_compare handler "
        "still maps {success:false} → HTTPException(400) — the structured "
        "{code,layer} body is dropped. Route needs to early-return the "
        "L1 dict instead of raising. Flagged for cross-QA with Backend agent.",
        strict=False,
    )
    def test_pair_shape_blocked_query_returns_content_unavailable(self, mock_service):
        # "glock 19" is a weapons-seed term in app/data/content_blocklist.json.
        response = client.post(
            "/api/v1/text/compare",
            json={"product_a": "glock 19", "product_b": "iPhone"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body.get("success") is False
        assert body.get("code") == "CONTENT_UNAVAILABLE"
        assert body.get("layer") == "query_prefilter"

    def test_pair_shape_clean_passes_l1(self, mock_service):
        response = client.post(
            "/api/v1/text/compare",
            json={"product_a": "iPhone 15", "product_b": "Galaxy S24"},
        )
        assert response.status_code == 200

    @pytest.mark.xfail(
        reason="Same as test_pair_shape_blocked_query_returns_content_unavailable — "
        "handler raises HTTPException on success:false from service. "
        "L1 service-level block fires but body is dropped.",
        strict=False,
    )
    def test_legacy_query_blocked_by_l1_same_path(self, mock_service):
        response = client.post(
            "/api/v1/text/compare",
            json={"query": "glock 19 vs iPhone"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body.get("success") is False
        assert body.get("code") == "CONTENT_UNAVAILABLE"


# ============================================
# Live Railway smoke tests — opt-in
# ============================================


class TestLiveRailwaySmoke:
    """Marked live_unit; not run in default CI. ~$0.05 total per run."""

    @pytest.mark.live_unit
    def test_live_railway_pair_shape_smoke(self):
        import httpx

        try:
            r = httpx.post(
                "https://web-production-58776.up.railway.app/api/v1/text/compare?nocache=true",
                json={"product_a": "iPhone 15", "product_b": "Galaxy S24"},
                timeout=120.0,
            )
        except Exception as e:  # noqa: BLE001
            pytest.skip(f"Live Railway unreachable: {e}")
        assert r.status_code == 200
        body = r.json()
        assert body.get("success") is True
        assert len(body.get("products", [])) == 2

    @pytest.mark.live_unit
    def test_live_railway_query_shape_smoke(self):
        import httpx

        try:
            r = httpx.post(
                "https://web-production-58776.up.railway.app/api/v1/text/compare?nocache=true",
                json={"query": "iPhone 15 vs Galaxy S24"},
                timeout=120.0,
            )
        except Exception as e:  # noqa: BLE001
            pytest.skip(f"Live Railway unreachable: {e}")
        assert r.status_code == 200
        body = r.json()
        assert body.get("success") is True
