"""Bundle C § 1c A.3.3-fix-1 — Serper meter instrumentation hole.

Per qa-bundle-c D.1.3 follow-up (`docs/investigations/2026-05-17-
bundle-c-cold-cache-evidence.md`): `record_usage("serper")` is NOT
called at any Serper invocation site. `/api/v1/admin/costs` Serper
counter reads 0 not because Serper is uncalled, but because the call
sites never report. Add `record_usage("serper")` after each successful
Serper call so the credit meter reflects reality.

Scope: pure instrumentation. NO behavioral change beyond bumping the
Redis counter. Failed calls (non-200, exceptions, missing API key)
must NOT increment — the counter tracks billable usage, not attempts.
"""
import logging
from unittest.mock import patch, AsyncMock, MagicMock

import pytest

from app.services import serper_service


def _mock_response(status_code: int = 200, json_data: dict | None = None) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {"organic": []}
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = Exception(f"HTTP {status_code}")
    return resp


def _patch_httpx(response: MagicMock):
    """Context-manager that swaps httpx.AsyncClient.post for our mock."""
    class _AsyncClient:
        def __init__(self, *args, **kwargs):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            return False
        async def post(self, *args, **kwargs):
            return response
    return patch("app.services.serper_service.httpx.AsyncClient", _AsyncClient)


# #60 — this module asserts METER behaviour, not budget behaviour. Stub the
# Redis counter read so the new serper budget gate is deterministically OPEN
# and no assertion here depends on the live Upstash lifetime counter.
@pytest.fixture(autouse=True)
def _budget_gate_open():
    from app.services import api_budget_service

    with patch.object(api_budget_service, "_redis_get", return_value=None):
        yield


# ---------------------------------------------------------------------------
# Successful calls record usage
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_web_records_usage_on_200(monkeypatch):
    monkeypatch.setattr(serper_service, "SERPER_API_KEY", "test-key")
    resp = _mock_response(200, {"organic": [{"title": "x"}]})
    with _patch_httpx(resp):
        with patch.object(serper_service, "record_usage") as mock_record:
            await serper_service.search_web("test query")
    mock_record.assert_called_with("serper")


@pytest.mark.asyncio
async def test_search_product_prices_records_usage_on_200(monkeypatch):
    monkeypatch.setattr(serper_service, "SERPER_API_KEY", "test-key")
    resp = _mock_response(200, {"shopping": [{"title": "x"}]})
    with _patch_httpx(resp):
        with patch.object(serper_service, "record_usage") as mock_record:
            await serper_service.search_product_prices("iPhone 16")
    mock_record.assert_called_with("serper")


@pytest.mark.asyncio
async def test_gcc_search_product_prices_records_usage_exactly_once(monkeypatch):
    """#60 — the always-empty gl=<gcc> primary leg is no longer purchased, so a
    GCC shopping search is ONE billable Serper credit, not two."""
    monkeypatch.delenv("SERPER_SHOPPING_PRIMARY_COUNTRIES", raising=False)
    monkeypatch.setattr(serper_service, "SERPER_API_KEY", "test-key")
    resp = _mock_response(200, {"shopping": [{"title": "x"}]})
    with _patch_httpx(resp):
        with patch.object(serper_service, "record_usage") as mock_record:
            await serper_service.search_product_prices("iPhone 16", country="bh")
    assert mock_record.call_count == 1
    assert mock_record.call_args_list[0].args == ("serper",)


@pytest.mark.asyncio
async def test_search_price_organic_records_usage_on_200(monkeypatch):
    monkeypatch.setattr(serper_service, "SERPER_API_KEY", "test-key")
    resp = _mock_response(200, {"organic": [{"title": "x"}]})
    with _patch_httpx(resp):
        with patch.object(serper_service, "record_usage") as mock_record:
            await serper_service.search_price_organic("iPhone 16")
    mock_record.assert_called_with("serper")


@pytest.mark.asyncio
async def test_search_videos_records_usage_on_200(monkeypatch):
    monkeypatch.setattr(serper_service, "SERPER_API_KEY", "test-key")
    resp = _mock_response(200, {"videos": []})
    with _patch_httpx(resp):
        with patch.object(serper_service, "record_usage") as mock_record:
            await serper_service.search_videos("test")
    mock_record.assert_called_with("serper")


@pytest.mark.asyncio
async def test_search_images_records_usage_on_200(monkeypatch):
    monkeypatch.setattr(serper_service, "SERPER_API_KEY", "test-key")
    resp = _mock_response(200, {"images": []})
    with _patch_httpx(resp):
        with patch.object(serper_service, "record_usage") as mock_record:
            await serper_service.search_images("test")
    mock_record.assert_called_with("serper")


@pytest.mark.asyncio
async def test_search_news_records_usage_on_200(monkeypatch):
    monkeypatch.setattr(serper_service, "SERPER_API_KEY", "test-key")
    resp = _mock_response(200, {"news": []})
    with _patch_httpx(resp):
        with patch.object(serper_service, "record_usage") as mock_record:
            await serper_service.search_news("test")
    mock_record.assert_called_with("serper")


# ---------------------------------------------------------------------------
# Missing API key — no record_usage
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_record_usage_when_api_key_missing(monkeypatch):
    """When SERPER_API_KEY is unset, the call short-circuits — no Redis
    counter bump (would be an over-count of billable usage)."""
    monkeypatch.setattr(serper_service, "SERPER_API_KEY", None)
    with patch.object(serper_service, "record_usage") as mock_record:
        await serper_service.search_web("test")
    mock_record.assert_not_called()


@pytest.mark.asyncio
async def test_no_record_usage_when_exception_raised(monkeypatch):
    """Exceptions during the call should NOT record usage — failed calls
    aren't billable. Confirms try/except wraps record_usage correctly."""
    monkeypatch.setattr(serper_service, "SERPER_API_KEY", "test-key")

    class _RaisingClient:
        def __init__(self, *args, **kwargs):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            return False
        async def post(self, *args, **kwargs):
            raise RuntimeError("network down")

    with patch("app.services.serper_service.httpx.AsyncClient", _RaisingClient):
        with patch.object(serper_service, "record_usage") as mock_record:
            await serper_service.search_web("test")
    mock_record.assert_not_called()
