"""#51 part (a) — ENABLE_CONVERTED_PROVENANCE_STAMP.

A price whose AMOUNT was converted (the extractor stamped ``converted_usd``)
must not end up wearing a member of ``_GENUINE_BH_SOURCE_METHODS``. Four sites
in structured_comparison_service.py overwrite the extractor's honest label:

  * ``_curl_scraper``     — candidate ``source_method`` is always
    ``page_scrape_jsonld`` (raw_data survives, so ``_is_genuine_bh_candidate``
    already says no, but the candidate label itself lies).
  * ``_firecrawl_scraper`` — ``price["source_method"] = "firecrawl"`` STOMPS
    raw_data before ``_is_genuine_bh_candidate`` ever reads it.
  * ``_scrapedo_scraper``  — same, with ``scrapedo_rendered``.
  * ``_finalize_fan_winner`` — clobbers raw_data's label with the candidate
    rank-name, so a converted winner banks at the 7d genuine TTL.

Every assertion below is pinned in BOTH directions: flag-ON does the honest
thing, flag-OFF is byte-identical to the pre-fix behaviour.
"""
import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

import pytest
from unittest.mock import AsyncMock, patch

import app.services.structured_comparison_service as scs
from app.services.price_service import (
    _GENUINE_BH_SOURCE_METHODS,
    _confirmed,
    _is_genuine_bh_candidate,
    _select_best,
    price_cache_ttl,
)

FLAG = "ENABLE_CONVERTED_PROVENANCE_STAMP"

# An OFF-registry Bahrain retailer PDP (registry_tier -> None) so the existing
# global-tier downgrade in _curl_scraper is NOT what produces converted_usd —
# the extractor's own relabel is.
OFF_REGISTRY_URL = "https://some-random-shop.example/product/widget"
OFF_REGISTRY_DOMAIN = "some-random-shop.example"


def _converted_price(retailer=OFF_REGISTRY_DOMAIN, url=OFF_REGISTRY_URL):
    """What the extractor returns for an AED page with a BHD target: the amount
    was converted, and (b)/(c) already relabel it honestly."""
    return {
        "amount": 102.5,
        "currency": "BHD",
        "original_currency": "AED",
        "retailer": retailer,
        "url": url,
        "source_method": "converted_usd",
        "estimated": False,
    }


def _genuine_price(retailer=OFF_REGISTRY_DOMAIN, url=OFF_REGISTRY_URL):
    """Control: a native-BHD page the extractor labels genuinely."""
    return {
        "amount": 244.99,
        "currency": "BHD",
        "original_currency": "BHD",
        "retailer": retailer,
        "url": url,
        "source_method": "page_scrape",
        "estimated": False,
    }


@pytest.fixture(autouse=True)
def _clean_flag(monkeypatch):
    monkeypatch.delenv(FLAG, raising=False)
    yield


def _set_flag(monkeypatch, on: bool):
    if on:
        monkeypatch.setenv(FLAG, "true")
    else:
        monkeypatch.delenv(FLAG, raising=False)


# ---------------------------------------------------------------------------
# the flag itself
# ---------------------------------------------------------------------------
class TestFlagContract:
    def test_defaults_off(self, monkeypatch):
        monkeypatch.delenv(FLAG, raising=False)
        assert scs._converted_provenance_enabled() is False

    @pytest.mark.parametrize("val", ["true", "1", "yes", "on", "TRUE", " On "])
    def test_truthy_values_turn_it_on(self, monkeypatch, val):
        monkeypatch.setenv(FLAG, val)
        assert scs._converted_provenance_enabled() is True

    @pytest.mark.parametrize("val", ["false", "0", "no", "off", "", "banana"])
    def test_everything_else_stays_off(self, monkeypatch, val):
        monkeypatch.setenv(FLAG, val)
        assert scs._converted_provenance_enabled() is False

    def test_read_per_call_not_cached_at_import(self, monkeypatch):
        """Railway must be able to flip it without a restart."""
        monkeypatch.delenv(FLAG, raising=False)
        assert scs._converted_provenance_enabled() is False
        monkeypatch.setenv(FLAG, "true")
        assert scs._converted_provenance_enabled() is True
        monkeypatch.setenv(FLAG, "false")
        assert scs._converted_provenance_enabled() is False


# ---------------------------------------------------------------------------
# _curl_scraper
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
class TestCurlScraperKeepsConverted:
    async def _run(self, monkeypatch, page_price):
        async def fake_fetch_page_price(url, full_name, currency):
            return dict(page_price)

        monkeypatch.setattr(scs, "fetch_page_price", fake_fetch_page_price)
        return await scs._curl_scraper(
            OFF_REGISTRY_URL, "Test Widget", "BHD", OFF_REGISTRY_DOMAIN
        )

    async def test_flag_off_still_stamps_genuine_rank_name(self, monkeypatch):
        """Byte-identical legacy: the converted extractor result is handed back
        wearing page_scrape_jsonld, a genuine-set member."""
        _set_flag(monkeypatch, False)
        cand = await self._run(monkeypatch, _converted_price())
        assert cand["source_method"] == "page_scrape_jsonld"
        assert cand["source_method"] in _GENUINE_BH_SOURCE_METHODS
        assert cand["rank"] == scs._RANK_PAGE_SCRAPE_JSONLD

    async def test_flag_on_keeps_converted_label(self, monkeypatch):
        _set_flag(monkeypatch, True)
        cand = await self._run(monkeypatch, _converted_price())
        assert cand["source_method"] == "converted_usd"
        assert cand["source_method"] not in _GENUINE_BH_SOURCE_METHODS
        assert cand["raw_data"]["source_method"] == "converted_usd"
        # rank must NOT move (issue #51: within-tier ordering unchanged)
        assert cand["rank"] == scs._RANK_PAGE_SCRAPE_JSONLD
        assert _is_genuine_bh_candidate(cand) is False

    @pytest.mark.parametrize("flag_on", [False, True])
    async def test_genuine_extractor_result_unaffected(self, monkeypatch, flag_on):
        """Control: a native-BHD page keeps page_scrape_jsonld in BOTH modes."""
        _set_flag(monkeypatch, flag_on)
        cand = await self._run(monkeypatch, _genuine_price())
        assert cand["source_method"] == "page_scrape_jsonld"
        assert cand["raw_data"]["source_method"] == "page_scrape"
        assert _is_genuine_bh_candidate(cand) is True

    @pytest.mark.parametrize("flag_on", [False, True])
    async def test_global_tier_downgrade_untouched(self, monkeypatch, flag_on):
        """The existing apple.com downgrade must survive both modes."""
        _set_flag(monkeypatch, flag_on)

        async def fake_fetch_page_price(url, full_name, currency):
            return _genuine_price(retailer="apple.com", url=url)

        monkeypatch.setattr(scs, "fetch_page_price", fake_fetch_page_price)
        cand = await scs._curl_scraper(
            "https://www.apple.com/shop/product/x", "Apple iPhone 15", "BHD", "apple.com"
        )
        assert cand["source_method"] == "converted_usd"
        assert cand["raw_data"]["source_method"] == "converted_usd"


# ---------------------------------------------------------------------------
# _firecrawl_scraper / _scrapedo_scraper — the two that STOMP raw_data
# ---------------------------------------------------------------------------
def _stub_render_providers(monkeypatch, price):
    """Neutralise budget/breaker/telemetry so the scraper body runs."""
    monkeypatch.setattr(scs.firecrawl_service, "is_available", lambda: True)
    monkeypatch.setattr(scs.scrapedo_service, "is_available", lambda: True)

    async def _gate_ok(provider):
        return True

    monkeypatch.setattr(scs, "_provider_gate_ok_async", _gate_ok)
    monkeypatch.setattr(scs, "_record_provider_attempt", lambda **kw: None)
    monkeypatch.setattr(scs, "record_usage", lambda *a, **k: None)
    monkeypatch.setattr(scs, "record_failure", lambda *a, **k: None)
    monkeypatch.setattr(scs, "record_success", lambda *a, **k: None)
    monkeypatch.setattr(scs, "validate_scrape_url", lambda url: True)
    monkeypatch.setattr(
        scs, "extract_price_from_html", lambda *a, **k: dict(price)
    )

    async def _fc(url):
        return "<html>Test Widget</html>", 200

    async def _sd(url):
        return "<html>Test Widget</html>", 200, 5

    monkeypatch.setattr(scs.firecrawl_service, "scrape_page_with_status", _fc)
    monkeypatch.setattr(scs.scrapedo_service, "render_page_with_status", _sd)


@pytest.mark.asyncio
class TestRenderScrapersKeepConverted:
    async def test_firecrawl_flag_off_stomps_raw_data(self, monkeypatch):
        """Legacy: the honest converted_usd on raw_data is overwritten with the
        genuine-set 'firecrawl', so the candidate reads as a genuine BH price."""
        _set_flag(monkeypatch, False)
        _stub_render_providers(monkeypatch, _converted_price())
        cand = await scs._firecrawl_scraper(
            OFF_REGISTRY_URL, "Test Widget", "BHD", OFF_REGISTRY_DOMAIN
        )
        assert cand["raw_data"]["source_method"] == "firecrawl"
        assert cand["source_method"] == "firecrawl_brand_domain"
        assert _is_genuine_bh_candidate(cand) is True  # the bug, pinned

    async def test_firecrawl_flag_on_preserves_converted(self, monkeypatch):
        _set_flag(monkeypatch, True)
        _stub_render_providers(monkeypatch, _converted_price())
        cand = await scs._firecrawl_scraper(
            OFF_REGISTRY_URL, "Test Widget", "BHD", OFF_REGISTRY_DOMAIN
        )
        assert cand["raw_data"]["source_method"] == "converted_usd"
        assert cand["source_method"] == "converted_usd"
        assert cand["source_method"] not in _GENUINE_BH_SOURCE_METHODS
        assert cand["rank"] == scs._RANK_FIRECRAWL_BRAND_DOMAIN
        assert _is_genuine_bh_candidate(cand) is False
        # retailer stamping is unchanged
        assert cand["raw_data"]["retailer"] == OFF_REGISTRY_DOMAIN

    @pytest.mark.parametrize("flag_on", [False, True])
    async def test_firecrawl_genuine_result_unaffected(self, monkeypatch, flag_on):
        _set_flag(monkeypatch, flag_on)
        _stub_render_providers(monkeypatch, _genuine_price())
        cand = await scs._firecrawl_scraper(
            OFF_REGISTRY_URL, "Test Widget", "BHD", OFF_REGISTRY_DOMAIN
        )
        assert cand["raw_data"]["source_method"] == "firecrawl"
        assert cand["source_method"] == "firecrawl_brand_domain"
        assert _is_genuine_bh_candidate(cand) is True

    async def test_scrapedo_flag_off_stomps_raw_data(self, monkeypatch):
        _set_flag(monkeypatch, False)
        _stub_render_providers(monkeypatch, _converted_price())
        cand = await scs._scrapedo_scraper(
            OFF_REGISTRY_URL, "Test Widget", "BHD", OFF_REGISTRY_DOMAIN
        )
        assert cand["raw_data"]["source_method"] == "scrapedo_rendered"
        assert cand["source_method"] == "scrapedo_rendered"
        assert _is_genuine_bh_candidate(cand) is True  # the bug, pinned

    async def test_scrapedo_flag_on_preserves_converted(self, monkeypatch):
        _set_flag(monkeypatch, True)
        _stub_render_providers(monkeypatch, _converted_price())
        cand = await scs._scrapedo_scraper(
            OFF_REGISTRY_URL, "Test Widget", "BHD", OFF_REGISTRY_DOMAIN
        )
        assert cand["raw_data"]["source_method"] == "converted_usd"
        assert cand["source_method"] == "converted_usd"
        assert cand["rank"] == scs._RANK_SCRAPEDO_RENDERED
        assert _is_genuine_bh_candidate(cand) is False

    @pytest.mark.parametrize("flag_on", [False, True])
    async def test_scrapedo_genuine_result_unaffected(self, monkeypatch, flag_on):
        _set_flag(monkeypatch, flag_on)
        _stub_render_providers(monkeypatch, _genuine_price())
        cand = await scs._scrapedo_scraper(
            OFF_REGISTRY_URL, "Test Widget", "BHD", OFF_REGISTRY_DOMAIN
        )
        assert cand["raw_data"]["source_method"] == "scrapedo_rendered"
        assert cand["source_method"] == "scrapedo_rendered"
        assert _is_genuine_bh_candidate(cand) is True


# ---------------------------------------------------------------------------
# the downstream consequence: selection + race-confirmation
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
class TestConvertedRenderCandidateLosesAuthority:
    async def _firecrawl_converted(self, monkeypatch):
        _stub_render_providers(monkeypatch, _converted_price())
        return await scs._firecrawl_scraper(
            OFF_REGISTRY_URL, "Test Widget", "BHD", OFF_REGISTRY_DOMAIN
        )

    async def test_flag_on_converted_render_loses_to_genuine(self, monkeypatch):
        _set_flag(monkeypatch, True)
        conv = await self._firecrawl_converted(monkeypatch)
        genuine = {
            "value": 244.99,
            "source_method": "page_scrape_jsonld",
            "rank": scs._RANK_PAGE_SCRAPE_JSONLD,
            "raw_data": {
                "amount": 244.99,
                "retailer": "bahrain.sharafdg.com",
                "source_method": "page_scrape",
            },
        }
        # conv has the HIGHER rank (90 > 85) and the LOWER price — it only loses
        # because its provenance is honest now.
        best = _select_best([conv, genuine])
        assert best["raw_data"]["retailer"] == "bahrain.sharafdg.com"
        assert _confirmed([conv]) is False

    async def test_flag_off_converted_render_wins_and_confirms(self, monkeypatch):
        """Pins the pre-fix damage so the fix cannot be a no-op."""
        _set_flag(monkeypatch, False)
        conv = await self._firecrawl_converted(monkeypatch)
        genuine = {
            "value": 244.99,
            "source_method": "page_scrape_jsonld",
            "rank": scs._RANK_PAGE_SCRAPE_JSONLD,
            "raw_data": {
                "amount": 244.99,
                "retailer": "bahrain.sharafdg.com",
                "source_method": "page_scrape",
            },
        }
        best = _select_best([conv, genuine])
        assert best["raw_data"]["retailer"] == OFF_REGISTRY_DOMAIN
        assert _confirmed([conv]) is True


# ---------------------------------------------------------------------------
# _finalize_fan_winner
# ---------------------------------------------------------------------------
class TestFanWinnerSourceMethod:
    """_finalize_fan_winner is a closure; the label decision lives in the
    module-level helper it calls."""

    def test_flag_off_takes_candidate_rank_name(self, monkeypatch):
        _set_flag(monkeypatch, False)
        best = {
            "source_method": "firecrawl_brand_domain",
            "raw_data": {"amount": 102.5, "source_method": "converted_usd"},
        }
        assert scs._fan_winner_source_method(best) == "firecrawl_brand_domain"

    def test_flag_on_keeps_converted_raw_label(self, monkeypatch):
        _set_flag(monkeypatch, True)
        best = {
            "source_method": "firecrawl_brand_domain",
            "raw_data": {"amount": 102.5, "source_method": "converted_usd"},
        }
        assert scs._fan_winner_source_method(best) == "converted_usd"

    @pytest.mark.parametrize("flag_on", [False, True])
    def test_genuine_raw_label_still_takes_candidate_name(self, monkeypatch, flag_on):
        _set_flag(monkeypatch, flag_on)
        best = {
            "source_method": "page_scrape_jsonld",
            "raw_data": {"amount": 244.99, "source_method": "page_scrape"},
        }
        assert scs._fan_winner_source_method(best) == "page_scrape_jsonld"

    @pytest.mark.parametrize("flag_on", [False, True])
    def test_missing_candidate_label_defaults_to_page_scrape(self, monkeypatch, flag_on):
        _set_flag(monkeypatch, flag_on)
        assert scs._fan_winner_source_method({"raw_data": {}}) == "page_scrape"

    def test_flag_on_missing_candidate_label_still_prefers_converted_raw(
        self, monkeypatch
    ):
        _set_flag(monkeypatch, True)
        best = {"raw_data": {"source_method": "converted_usd"}}
        assert scs._fan_winner_source_method(best) == "converted_usd"


_INT_DOMAIN = "bahrain.sharafdg.com"
_INT_URL = "https://bahrain.sharafdg.com/product/test-widget"


@pytest.mark.asyncio
class TestFinalizeFanWinnerIntegration:
    """End to end through _get_price: a fan_out winner whose raw_data says
    converted_usd must not be banked as a genuine 7d Bahrain shelf price."""

    async def _run(self, monkeypatch, flag_on):
        _set_flag(monkeypatch, flag_on)
        svc = scs.StructuredComparisonService()
        ssc = "app.services.structured_comparison_service"
        captured = {}

        async def fake_shopping(*_a, **_k):
            return {"shopping": [], "organic": [], "shopping_region": "bh"}

        async def fake_fan_out(*_a, **_k):
            return {
                "best": {
                    "raw_data": {
                        "amount": 102.5,
                        "currency": "BHD",
                        "original_currency": "AED",
                        "retailer": _INT_DOMAIN,
                        "url": _INT_URL,
                        "source_method": "converted_usd",
                        "in_stock": True,
                    },
                    "source_method": "firecrawl_brand_domain",
                    "rank": 90,
                },
                "alternates": [],
                "cancelled_count": 0,
                "elapsed_seconds": 1.0,
            }

        def fake_set_cached(key, value, ttl=None, **kw):
            if isinstance(value, dict) and value.get("amount") == 102.5:
                captured["ttl"] = ttl
                captured["source_method"] = value.get("source_method")
            return True

        with patch(f"{ssc}.search_product_prices", new=AsyncMock(side_effect=fake_shopping)), \
             patch(f"{ssc}.extract_price_from_shopping", return_value=None), \
             patch(f"{ssc}.validate_scrape_url", return_value=True), \
             patch(f"{ssc}._should_escalate_price_scrape", return_value=True), \
             patch(f"{ssc}.fan_out_price_lookup", new=AsyncMock(side_effect=fake_fan_out)), \
             patch(f"{ssc}.search_web", new=AsyncMock(return_value={"organic": [
                 {"link": _INT_URL, "title": "Test Widget"}]})), \
             patch(f"{ssc}.get_shopify_sources_for_category", return_value=[]), \
             patch(f"{ssc}.get_algolia_sources_for_category", return_value=[]), \
             patch(f"{ssc}.get_unbxd_sources_for_category", return_value=[]), \
             patch(f"{ssc}.get_noon_sources_for_category", return_value=[]), \
             patch(f"{ssc}.get_cached", return_value=None), \
             patch(f"{ssc}.set_cached", side_effect=fake_set_cached), \
             patch("app.services.product_data_service.get_cached_price", new=AsyncMock(return_value=None)), \
             patch.object(svc, "_save_price_to_db"):
            price = await svc._get_price(
                brand="Test", name="Widget", variant=None, region="bahrain",
                search_query="Test Widget", nocache=True, category="electronics",
            )
        return price, captured

    async def test_flag_off_banks_converted_as_genuine(self, monkeypatch):
        price, captured = await self._run(monkeypatch, flag_on=False)
        assert price is not None and abs(price["amount"] - 102.5) < 0.01
        assert price["source_method"] == "firecrawl_brand_domain"
        assert price["source_method"] in _GENUINE_BH_SOURCE_METHODS
        # the 7d genuine TTL is exactly the damage
        assert price_cache_ttl(price) == price_cache_ttl(
            {"source_method": "page_scrape"}
        )

    async def test_flag_on_keeps_converted_and_short_ttl(self, monkeypatch):
        price, captured = await self._run(monkeypatch, flag_on=True)
        assert price is not None and abs(price["amount"] - 102.5) < 0.01
        assert price["source_method"] == "converted_usd"
        assert price["source_method"] not in _GENUINE_BH_SOURCE_METHODS
        assert price_cache_ttl(price) < price_cache_ttl(
            {"source_method": "page_scrape"}
        )
