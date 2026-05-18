"""Bundle C § 1c — price pipeline invocation + circuit-breaker diagnostic.

Per design § 1c + plan A.2.3: when DEBUG_STAGE_TIMINGS=true, log every
Firecrawl + Scrape.do invocation alongside the relevant credit-state +
breaker-state so post-deploy probes can identify whether mainstream
products fall to `estimated` because of Serper regional gap,
api_budget exhaustion, breaker trip, or parser regression.

The diagnostic is read-only (no behavior change) and zero-overhead with
the flag off — strict adherence to A.10.1 + measure-before-optimize.
"""
import logging
from unittest.mock import patch, AsyncMock, MagicMock

import pytest

from app.services import api_budget_service, firecrawl_service, scrapedo_service


# ---------------------------------------------------------------------------
# A.2.3 helper additions to api_budget_service: get_remaining + get_breaker_state
# ---------------------------------------------------------------------------


def test_api_budget_get_remaining_returns_int_for_known_provider():
    """get_remaining(provider) is a read-only count of credits left."""
    with patch.object(api_budget_service, "_redis_get", return_value=None):
        assert api_budget_service.get_remaining("firecrawl") == 450
        assert api_budget_service.get_remaining("scrapedo") == 900
        assert api_budget_service.get_remaining("serper") == 2200


def test_api_budget_get_remaining_subtracts_used():
    """get_remaining = monthly_limit - used."""
    with patch.object(api_budget_service, "_redis_get", return_value="100"):
        assert api_budget_service.get_remaining("firecrawl") == 350


def test_api_budget_get_remaining_returns_zero_for_unknown_provider():
    assert api_budget_service.get_remaining("nonexistent") == 0


def test_api_budget_get_breaker_state_returns_closed_default():
    """Default state when no Redis entry exists is 'closed'."""
    with patch.object(api_budget_service, "_redis_get", return_value=None):
        assert api_budget_service.get_breaker_state("firecrawl") == "closed"


def test_api_budget_get_breaker_state_returns_open_when_tripped():
    """When circuit breaker has been tripped, state == 'open'."""
    with patch.object(
        api_budget_service,
        "_redis_get",
        return_value='{"state": "open", "failure_count": 5, "tripped_at": 0}',
    ):
        assert api_budget_service.get_breaker_state("firecrawl") == "open"


def test_api_budget_get_breaker_state_fail_open_on_redis_error():
    """Redis errors must not raise — return 'closed' as fail-open."""
    def _raise(*args, **kwargs):
        raise RuntimeError("Redis down")

    with patch.object(api_budget_service, "_redis_get", side_effect=_raise):
        assert api_budget_service.get_breaker_state("firecrawl") == "closed"


# ---------------------------------------------------------------------------
# A.2.3 firecrawl invocation diagnostic
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_firecrawl_invocation_logged_when_flag_on(caplog, monkeypatch):
    """When DEBUG_STAGE_TIMINGS=true, scrape_page emits PRICE_PIPELINE_DIAG
    with url + credits_remaining + breaker_state."""
    monkeypatch.setenv("DEBUG_STAGE_TIMINGS", "true")
    monkeypatch.setattr(firecrawl_service, "_PRICE_PIPELINE_DIAG_FLAG", None, raising=False)
    monkeypatch.setenv("FIRECRAWL_API_KEY", "test-key")

    # Make the actual HTTP call a no-op
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"success": True, "data": {"html": "x" * 600}}

    class _AsyncClient:
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            return False
        async def post(self, *args, **kwargs):
            return mock_resp

    with patch("app.services.firecrawl_service.httpx.AsyncClient", return_value=_AsyncClient()):
        with patch.object(api_budget_service, "get_remaining", return_value=410):
            with patch.object(api_budget_service, "get_breaker_state", return_value="closed"):
                with caplog.at_level(logging.INFO, logger="app.services.firecrawl_service"):
                    await firecrawl_service.scrape_page("https://example.com/product")

    assert "PRICE_PIPELINE_DIAG" in caplog.text
    assert "firecrawl_invocation" in caplog.text
    assert "example.com/product" in caplog.text or "example.com" in caplog.text
    assert "410" in caplog.text  # credits_remaining
    assert "closed" in caplog.text  # breaker_state


@pytest.mark.asyncio
async def test_firecrawl_invocation_silent_when_flag_off(caplog, monkeypatch):
    """Per A.10.1 invariant: zero overhead when flag off."""
    monkeypatch.setenv("DEBUG_STAGE_TIMINGS", "false")
    monkeypatch.setattr(firecrawl_service, "_PRICE_PIPELINE_DIAG_FLAG", None, raising=False)
    monkeypatch.setenv("FIRECRAWL_API_KEY", "test-key")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"success": True, "data": {"html": "x" * 600}}

    class _AsyncClient:
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            return False
        async def post(self, *args, **kwargs):
            return mock_resp

    with patch("app.services.firecrawl_service.httpx.AsyncClient", return_value=_AsyncClient()):
        with caplog.at_level(logging.INFO, logger="app.services.firecrawl_service"):
            await firecrawl_service.scrape_page("https://example.com/product")

    assert "PRICE_PIPELINE_DIAG" not in caplog.text


# ---------------------------------------------------------------------------
# A.2.3 scrapedo invocation diagnostic
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_scrapedo_invocation_logged_when_flag_on(caplog, monkeypatch):
    monkeypatch.setenv("DEBUG_STAGE_TIMINGS", "true")
    monkeypatch.setattr(scrapedo_service, "_PRICE_PIPELINE_DIAG_FLAG", None, raising=False)
    monkeypatch.setenv("SCRAPEDO_API_TOKEN", "test-token")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = "<html>" + ("x" * 600) + "</html>"

    class _AsyncClient:
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            return False
        async def get(self, *args, **kwargs):
            return mock_resp

    with patch("app.services.scrapedo_service.httpx.AsyncClient", return_value=_AsyncClient()):
        with patch.object(api_budget_service, "get_remaining", return_value=820):
            with patch.object(api_budget_service, "get_breaker_state", return_value="closed"):
                with caplog.at_level(logging.INFO, logger="app.services.scrapedo_service"):
                    await scrapedo_service.render_page("https://example.com/product")

    assert "PRICE_PIPELINE_DIAG" in caplog.text
    assert "scrapedo_invocation" in caplog.text
    assert "820" in caplog.text


@pytest.mark.asyncio
async def test_scrapedo_invocation_silent_when_flag_off(caplog, monkeypatch):
    monkeypatch.setenv("DEBUG_STAGE_TIMINGS", "false")
    monkeypatch.setattr(scrapedo_service, "_PRICE_PIPELINE_DIAG_FLAG", None, raising=False)
    monkeypatch.setenv("SCRAPEDO_API_TOKEN", "test-token")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = "<html>" + ("x" * 600) + "</html>"

    class _AsyncClient:
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            return False
        async def get(self, *args, **kwargs):
            return mock_resp

    with patch("app.services.scrapedo_service.httpx.AsyncClient", return_value=_AsyncClient()):
        with caplog.at_level(logging.INFO, logger="app.services.scrapedo_service"):
            await scrapedo_service.render_page("https://example.com/product")

    assert "PRICE_PIPELINE_DIAG" not in caplog.text
