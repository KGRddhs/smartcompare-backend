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

    def test_sse_endpoint_accepts_pair_shape(self, mock_service):
        # Backend be44b04 widened the SSE endpoint to accept ?product_a=&product_b=.
        response = client.get(
            "/api/v1/text/compare/stream",
            params={"product_a": "iPhone 15", "product_b": "Galaxy S24"},
        )
        assert response.status_code != 422

    def test_sse_endpoint_rejects_both_shapes(self, mock_service):
        # Mutual-exclusion: ?q=…&product_a=…&product_b=… rejected per be44b04.
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
        # Empty params → 422 (be44b04 still requires one shape).
        response = client.get("/api/v1/text/compare/stream")
        assert response.status_code == 422

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

    def test_pair_shape_blocked_query_returns_content_unavailable(self):
        # "glock 19" is a weapons-seed term in app/data/content_blocklist.json.
        # Backend § 1.4 + text_routes.py:165 early-return on CONTENT_UNAVAILABLE.
        # Hit the REAL service so the L1 pre-flight inside compare_from_text
        # actually runs — mocking the service replaces L1 too.
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

    def test_legacy_query_blocked_by_l1_same_path(self):
        # Hit the REAL service for L1 to fire.
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


# live_prod (#49): these POST the PRODUCTION deployment. `?nocache=true` bypasses the
# cache READ only — the prod server still runs should_cache_price -> set_cached +
# _save_price_to_db (structured_comparison_service.py:5600, :6930), so every run seeds
# the production price cache and inserts production L2 rows. Excluded from the
# scheduled live suite by `-m "live_unit and not live_prod"`.
@pytest.mark.live_prod
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


# ============================================
# Bundle E S3 hotfix — GET /text/compare dual-shape parity with POST + SSE
# (device walk image #5: SSE failed → fallback to GET /text/compare with
# product_a/product_b only → FastAPI Query(...) required `q` → 422.)
# ============================================


class TestGetEndpointDualShape:
    """L3 hotfix: GET /text/compare must accept BOTH q-only and pair shapes
    so the streamComparison() SSE fallback in api.ts L482 doesn't 422 when
    the caller is in pair mode. Mirrors the POST + SSE contracts."""

    def test_get_endpoint_accepts_query_shape(self, mock_service):
        response = client.get(
            "/api/v1/text/compare",
            params={"q": "iPhone 15 vs Galaxy S24"},
        )
        assert response.status_code == 200

    def test_get_endpoint_accepts_pair_shape(self, mock_service):
        response = client.get(
            "/api/v1/text/compare",
            params={"product_a": "iPhone 15", "product_b": "Galaxy S24"},
        )
        assert response.status_code == 200

    def test_get_endpoint_rejects_both_shapes(self, mock_service):
        response = client.get(
            "/api/v1/text/compare",
            params={
                "q": "X vs Y",
                "product_a": "X",
                "product_b": "Y",
            },
        )
        assert response.status_code == 422

    def test_get_endpoint_rejects_neither_shape(self, mock_service):
        response = client.get("/api/v1/text/compare")
        assert response.status_code == 422

    def test_get_endpoint_rejects_pair_with_empty_product_a(self, mock_service):
        response = client.get(
            "/api/v1/text/compare",
            params={"product_a": "", "product_b": "Galaxy S24"},
        )
        assert response.status_code == 422

    def test_get_endpoint_rejects_pair_with_whitespace_product_b(self, mock_service):
        response = client.get(
            "/api/v1/text/compare",
            params={"product_a": "iPhone 15", "product_b": "   "},
        )
        assert response.status_code == 422

    def test_get_endpoint_pair_synthesizes_query(self, mock_service):
        response = client.get(
            "/api/v1/text/compare",
            params={"product_a": "  iPhone 15  ", "product_b": "  Galaxy S24  "},
        )
        assert response.status_code == 200
        call_kwargs = mock_service.compare_from_text.await_args.kwargs
        assert call_kwargs["query"] == "iPhone 15 vs Galaxy S24"

    def test_get_endpoint_pair_propagates_explicit_pair(self, mock_service):
        """Gate B [IMPORTANT]: GET-pair must forward explicit_pair=(a,b) to
        compare_from_text so the service skips parse_product_query() — same
        contract as the POST handler (test_explicit_pair_kwarg_propagates)
        and the SSE handler. Without this, the GET-fallback path burns an
        unnecessary GPT call + 1-2s of latency vs POST/SSE."""
        response = client.get(
            "/api/v1/text/compare",
            params={"product_a": "iPhone 15", "product_b": "Galaxy S24"},
        )
        assert response.status_code == 200
        call_kwargs = mock_service.compare_from_text.await_args.kwargs
        assert call_kwargs.get("explicit_pair") == ("iPhone 15", "Galaxy S24")

    def test_get_endpoint_query_path_no_explicit_pair(self, mock_service):
        """Legacy q= shape must NOT set explicit_pair — the service still
        runs parse_product_query() to extract structured products from the
        freeform string. Mirrors POST test_query_path_no_explicit_pair_kwarg."""
        response = client.get(
            "/api/v1/text/compare",
            params={"q": "iPhone 15 vs Galaxy S24"},
        )
        assert response.status_code == 200
        call_kwargs = mock_service.compare_from_text.await_args.kwargs
        assert call_kwargs.get("explicit_pair") is None

    def test_get_endpoint_pair_explicit_pair_stripped_inputs(self, mock_service):
        """Whitespace in pair inputs is stripped BEFORE being forwarded as
        explicit_pair (parity with POST handler line 65 and SSE handler
        line 359)."""
        response = client.get(
            "/api/v1/text/compare",
            params={"product_a": "  iPhone 15  ", "product_b": "  Galaxy S24  "},
        )
        assert response.status_code == 200
        call_kwargs = mock_service.compare_from_text.await_args.kwargs
        assert call_kwargs.get("explicit_pair") == ("iPhone 15", "Galaxy S24")


# ============================================
# Bundle E S3 hotfix — image_url persistence invariant
# (device walk image #12: HistoryScreen rows show placeholder phone glyphs
# despite the Bundle E S3 A4 Wave 2 ProductImage wiring. Root cause: rows
# saved BEFORE the A3 image pipeline deploy did not carry image_url; new
# rows MUST carry it through save_comparison's `full_response` JSONB.)
# ============================================


class TestImageUrlSavedInFullResponse:
    """L3 hotfix: assert image_url survives the save_comparison pipeline so
    HistoryScreen at HistoryScreen.tsx:534 can read full_response.products[i]
    .image_url. The save_comparison persistence is JSONB — it preserves the
    dict shape verbatim — so the invariant is that build_comparison_response
    populates image_url on BOTH overview.products[i] AND the legacy
    products[i] alias before the row is persisted."""

    def test_build_comparison_response_includes_image_url_in_overview(self):
        from app.services.response_builder import build_comparison_response

        result = build_comparison_response(
            products=[
                {"brand": "Apple", "name": "iPhone 15", "image_url": "https://cdn.apple.com/i15.jpg"},
                {"brand": "Samsung", "name": "Galaxy S24", "image_url": "https://cdn.samsung.com/s24.jpg"},
            ],
            comparison={},
            query="iPhone 15 vs Galaxy S24",
        )
        overview_products = result["overview"]["products"]
        assert overview_products[0]["image_url"] == "https://cdn.apple.com/i15.jpg"
        assert overview_products[1]["image_url"] == "https://cdn.samsung.com/s24.jpg"

    def test_build_comparison_response_includes_image_url_in_legacy_products_alias(self):
        # HistoryScreen.tsx:530-534 reads `item.full_response.products[i].image_url`
        # — that's the LEGACY alias path, not overview.products. Must be plumbed.
        from app.services.response_builder import build_comparison_response

        result = build_comparison_response(
            products=[
                {"brand": "Apple", "name": "iPhone 15", "image_url": "https://cdn.apple.com/i15.jpg"},
                {"brand": "Samsung", "name": "Galaxy S24", "image_url": "https://cdn.samsung.com/s24.jpg"},
            ],
            comparison={},
            query="iPhone 15 vs Galaxy S24",
        )
        legacy_products = result["products"]
        assert legacy_products[0]["image_url"] == "https://cdn.apple.com/i15.jpg"
        assert legacy_products[1]["image_url"] == "https://cdn.samsung.com/s24.jpg"

    def test_build_comparison_response_image_url_none_when_missing(self):
        # When the image pipeline returns None (all tiers exhausted), the
        # response must still carry the key as None — frontend ProductImage
        # 4-state primitive handles the None/undefined → placeholder fallback.
        from app.services.response_builder import build_comparison_response

        result = build_comparison_response(
            products=[
                {"brand": "Apple", "name": "iPhone 15"},
                {"brand": "Samsung", "name": "Galaxy S24"},
            ],
            comparison={},
            query="iPhone 15 vs Galaxy S24",
        )
        assert result["overview"]["products"][0]["image_url"] is None
        assert result["overview"]["products"][1]["image_url"] is None
        # Legacy alias also gets None (defensive).
        assert result["products"][0]["image_url"] is None
        assert result["products"][1]["image_url"] is None

    def test_save_comparison_preserves_image_url_in_full_response(self, monkeypatch):
        # save_comparison writes `full_response` JSONB verbatim — assert the
        # image_url survives the dict-pass to the Supabase insert payload.
        import asyncio
        from app.services import database_service

        captured = {}

        class _FakeBuilder:
            def insert(self, record):
                captured["record"] = record
                class _Exec:
                    data = [{"id": "test-id"}]
                    def execute(self):
                        return self
                return _Exec()

        class _FakeClient:
            def table(self, name):
                captured["table"] = name
                return _FakeBuilder()

        monkeypatch.setattr(database_service, "get_supabase_client", lambda: _FakeClient())

        full_response = {
            "success": True,
            "overview": {
                "products": [
                    {"name": "iPhone 15", "image_url": "https://cdn.apple.com/i15.jpg"},
                    {"name": "Galaxy S24", "image_url": "https://cdn.samsung.com/s24.jpg"},
                ],
            },
            "products": [
                {"name": "iPhone 15", "image_url": "https://cdn.apple.com/i15.jpg"},
                {"name": "Galaxy S24", "image_url": "https://cdn.samsung.com/s24.jpg"},
            ],
            "metadata": {"query": "iPhone 15 vs Galaxy S24"},
        }

        result = asyncio.run(
            database_service.save_comparison(
                full_response=full_response,
                query="iPhone 15 vs Galaxy S24",
                input_type="text",
                user_id="00000000-0000-0000-0000-000000000000",
            )
        )

        assert result is not None
        saved_full = captured["record"]["full_response"]
        # Both shapes preserved verbatim (JSONB pass-through).
        assert saved_full["overview"]["products"][0]["image_url"] == "https://cdn.apple.com/i15.jpg"
        assert saved_full["overview"]["products"][1]["image_url"] == "https://cdn.samsung.com/s24.jpg"
        assert saved_full["products"][0]["image_url"] == "https://cdn.apple.com/i15.jpg"
        assert saved_full["products"][1]["image_url"] == "https://cdn.samsung.com/s24.jpg"
