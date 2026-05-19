"""Bundle C A.10.1 — diagnostic loggers stay silent when flag off.

Per plan A.10.1 + the project measure-before-optimize rule: every
Bundle C diagnostic added in A.2.1 / A.2.2 / A.2.3 MUST be gated on
DEBUG_STAGE_TIMINGS=true. With the flag off, none of the
PROS_CONS_DIAGNOSTIC / FACTUAL_VERDICT_DIAGNOSTIC / PRICE_PIPELINE_DIAG
log lines may fire — zero production overhead.

This is a regression guard: if a future change makes the diagnostics
unconditional (e.g., someone deletes the flag check), this test
catches it.

The detailed flag-on behavior tests already live in:
- tests/test_extraction_pros_cons_diagnostic.py (A.2.1)
- tests/test_response_builder_factual_verdict_diagnostic.py (A.2.2)
- tests/test_price_pipeline_diagnostic.py (A.2.3)
"""
import logging
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from app.services import extraction_service, response_builder
from app.services import firecrawl_service, scrapedo_service


# ---------------------------------------------------------------------------
# All three diagnostics silent when DEBUG_STAGE_TIMINGS=false
# ---------------------------------------------------------------------------


def _reset_diagnostic_caches(monkeypatch):
    """All three diagnostics cache the env-var read once per process via
    module-level singletons. Reset each so the monkeypatched env is
    actually picked up."""
    monkeypatch.setattr(extraction_service, "_PROS_CONS_DIAG_FLAG", None, raising=False)
    monkeypatch.setattr(response_builder, "_FACTUAL_VERDICT_DIAG_FLAG", None, raising=False)
    monkeypatch.setattr(firecrawl_service, "_PRICE_PIPELINE_DIAG_FLAG", None, raising=False)
    monkeypatch.setattr(scrapedo_service, "_PRICE_PIPELINE_DIAG_FLAG", None, raising=False)


@pytest.mark.asyncio
async def test_pros_cons_diag_silent_when_flag_off(caplog, monkeypatch):
    """A.2.1 invariant: PROS_CONS_DIAGNOSTIC never fires when
    DEBUG_STAGE_TIMINGS=false, even on the failure path that empties
    pros/cons."""
    monkeypatch.setenv("DEBUG_STAGE_TIMINGS", "false")
    _reset_diagnostic_caches(monkeypatch)

    fake_content = (
        '{"winner_index": 0, "winner_declaration": "X", '
        '"product_0_pros": [], "product_1_pros": [], '
        '"product_0_cons": [], "product_1_cons": []}'
    )
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = fake_content
    mock_response.usage = MagicMock(total_tokens=100, prompt_tokens=80, completion_tokens=20)

    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    with patch("app.services.extraction_service.get_client", return_value=mock_client):
        with caplog.at_level(logging.WARNING, logger="app.services.extraction_service"):
            await extraction_service.generate_comparison(
                product1={"name": "A", "brand": "X"},
                product2={"name": "B", "brand": "Y"},
                region="bahrain",
            )

    assert "PROS_CONS_DIAGNOSTIC" not in caplog.text


def test_factual_verdict_diag_silent_when_flag_off(caplog, monkeypatch):
    """A.2.2 invariant: FACTUAL_VERDICT_DIAGNOSTIC never fires when
    DEBUG_STAGE_TIMINGS=false, even when the builder is patched to
    return None."""
    monkeypatch.setenv("DEBUG_STAGE_TIMINGS", "false")
    _reset_diagnostic_caches(monkeypatch)
    monkeypatch.setattr(
        response_builder, "_build_factual_verdict",
        lambda *a, **kw: None,
    )

    with caplog.at_level(logging.WARNING, logger="app.services.response_builder"):
        response_builder._build_scoring_v2(
            product_data=[
                {"name": "iPhone 16", "price": {"amount": 350.0}, "rating": 4.5},
                {"name": "Galaxy S25", "price": {"amount": 280.0}, "rating": 4.4},
            ],
            scoring_result={"scores": {
                "product_0": {"overall": 75, "breakdown": {}},
                "product_1": {"overall": 82, "breakdown": {}},
            }},
            category="electronics",
            winner_index=1,
        )

    assert "FACTUAL_VERDICT_DIAGNOSTIC" not in caplog.text


@pytest.mark.asyncio
async def test_firecrawl_price_pipeline_diag_silent_when_flag_off(caplog, monkeypatch):
    """A.2.3 invariant: PRICE_PIPELINE_DIAG never fires from
    firecrawl_service when DEBUG_STAGE_TIMINGS=false."""
    monkeypatch.setenv("DEBUG_STAGE_TIMINGS", "false")
    _reset_diagnostic_caches(monkeypatch)
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


@pytest.mark.asyncio
async def test_scrapedo_price_pipeline_diag_silent_when_flag_off(caplog, monkeypatch):
    """A.2.3 invariant: PRICE_PIPELINE_DIAG never fires from
    scrapedo_service when DEBUG_STAGE_TIMINGS=false."""
    monkeypatch.setenv("DEBUG_STAGE_TIMINGS", "false")
    _reset_diagnostic_caches(monkeypatch)
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


def test_all_three_diagnostic_flags_share_single_env_var():
    """Single source of truth: all three diagnostic groups read from
    the SAME env var (DEBUG_STAGE_TIMINGS). This is the contract
    documented in CLAUDE.md and qa-bundle-c's D.1.3 evidence — Ahmed
    flips ONE flag on Railway to enable/disable all three diagnostic
    groups in one operation."""
    import inspect

    sources = {
        "extraction": inspect.getsource(extraction_service._pros_cons_diag_enabled),
        "response_builder": inspect.getsource(response_builder._factual_verdict_diag_enabled),
        "firecrawl": inspect.getsource(firecrawl_service._diag_enabled),
        "scrapedo": inspect.getsource(scrapedo_service._diag_enabled),
    }
    for name, src in sources.items():
        assert "DEBUG_STAGE_TIMINGS" in src, (
            f"{name} diagnostic helper does NOT read DEBUG_STAGE_TIMINGS — "
            f"single-flag contract broken"
        )
