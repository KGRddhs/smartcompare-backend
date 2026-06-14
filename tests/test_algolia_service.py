"""S3 #21 — generic Algolia harvester (6thStreet, Namshi-ready).

Harvests the PUBLIC search-only Algolia config (app-id + search-key + index)
from a storefront's page JS, then queries the Algolia `/queries` endpoint
directly for genuine BHD prices. Read-only search ONLY (never write/admin).

Mirrors the Shopify adapter's discipline: strict title/brand matching (reuses
price_service.strict_title_match/numbers_match/normalize_words) so a fuzzy
Algolia hit (e.g. "Tom Ford" → "TOMS" shoes) is REJECTED, never shipped as a
wrong-brand price. Genuine BHD only — source_method="local_bhd".

All HTTP + Redis mocked; the Algolia response fixture is a real recorded
6thStreet response (tests/fixtures/algolia_6thstreet_tomford.json).
"""

import json
import os
from pathlib import Path

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


_FIXTURE = Path(__file__).parent / "fixtures" / "algolia_6thstreet_tomford.json"

# Real minified config snippet from 6thStreet main.<hash>.chunk.js (the appId +
# search-key defaults) — verbatim so the extractor is tested against reality.
_REAL_CHUNK_SNIPPET = (
    'o=t.env,l=void 0===o?"production":o,u=t.appId,'
    'd=void 0===u?"02X7U6O3SI":u,v=t.adminKey,'
    'p=void 0===v?"6e9a600dc69be19481363bddd793e2f2":v,'
    'f=t.index,h=void 0===f?"":f;ye.init(d,p),ye.setIndex.'
)

# Minimal page HTML carrying the DSN preconnect (app-id) + index name, as the
# real 6thStreet landing page does.
_REAL_PAGE_HTML = (
    '<link rel="preconnect" href="https://02X7U6O3SI-dsn.algolia.net/" '
    'crossorigin="anonymous">'
    '<script src="https://d33potchz7aua6.cloudfront.net/static/js/'
    'main.919c9ed2.chunk.js"></script>'
    '<a href="/women.html?idx=enterprise_magento_en_bh_products">x</a>'
)


def _load_fixture():
    return json.loads(_FIXTURE.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# extract_algolia_config — the generic primitive (Namshi reuses it)
# ---------------------------------------------------------------------------

def test_extract_config_from_html_and_chunk():
    import app.services.algolia_service as alg
    cfg = alg.extract_algolia_config(_REAL_PAGE_HTML, _REAL_CHUNK_SNIPPET)
    assert cfg is not None
    assert cfg["app_id"] == "02X7U6O3SI"
    assert cfg["api_key"] == "6e9a600dc69be19481363bddd793e2f2"
    assert cfg["index"] == "enterprise_magento_en_bh_products"


def test_extract_config_missing_key_returns_none():
    """No api_key derivable (chunk absent / no adminKey pattern) → None, never a
    partial config that would 400 the Algolia call."""
    import app.services.algolia_service as alg
    cfg = alg.extract_algolia_config(_REAL_PAGE_HTML, "no algolia config here")
    assert cfg is None


def test_extract_config_missing_appid_returns_none():
    import app.services.algolia_service as alg
    cfg = alg.extract_algolia_config("<html>no dsn no index</html>", _REAL_CHUNK_SNIPPET)
    assert cfg is None


# ---------------------------------------------------------------------------
# _parse_algolia_price — nested price[0].BHD.default extraction
# ---------------------------------------------------------------------------

def test_parse_price_extracts_bhd_default():
    import app.services.algolia_service as alg
    hit = _load_fixture()["hits"][0]
    amount = alg._parse_algolia_price(hit)
    assert amount == 21.0  # price[0].BHD.default == 21


def test_parse_price_none_when_no_bhd():
    import app.services.algolia_service as alg
    assert alg._parse_algolia_price({"price": [{"USD": {"default": 9}}]}) is None
    assert alg._parse_algolia_price({"price": []}) is None
    assert alg._parse_algolia_price({}) is None
    assert alg._parse_algolia_price({"price": [{"BHD": {"default": 0}}]}) is None  # 0 invalid


# ---------------------------------------------------------------------------
# _match_algolia_hit — STRICT matching; reject the wrong-brand fuzzy hit
# ---------------------------------------------------------------------------

def test_match_rejects_wrong_brand_fuzzy_hit():
    """The killer test: 'Tom Ford Black Orchid' must NOT match the TOMS shoes
    that Algolia fuzzy-returned. Wrong-product protection (iPhone16→14 class)."""
    import app.services.algolia_service as alg
    hits = _load_fixture()["hits"]  # all brand_name="Toms" sneakers
    matched = alg._match_algolia_hit(hits, "Tom Ford Black Orchid")
    assert matched is None  # strict_title_match drops ford/black/orchid-absent titles


def test_match_accepts_real_title_match():
    import app.services.algolia_service as alg
    hits = [
        {"name": "Pro Filt'r Soft Matte Longwear Foundation",
         "brand_name": "Fenty Beauty",
         "price": [{"BHD": {"default": 18.5, "default_formated": "BHD 18.500"}}],
         "url": "https://en-bh.6thstreet.com/buy-fenty-pro-filtr.html",
         "in_stock": True},
    ]
    matched = alg._match_algolia_hit(hits, "Fenty Pro Filt'r Foundation")
    assert matched is not None
    assert matched["name"].startswith("Pro Filt'r")


def test_match_real_nike_fixture_positive_gate():
    """POSITIVE GATE (real recorded 6thStreet response): 'Nike Air Max SC'
    matches the genuine Nike hit and yields BHD 32.000. Proves the genuine-BHD
    path on a product 6thStreet actually carries (the fashion lever — the
    harvested index is fashion/footwear-strong, beauty-thin)."""
    import json
    from pathlib import Path
    import app.services.algolia_service as alg
    fx = json.loads(
        (Path(__file__).parent / "fixtures" / "algolia_6thstreet_nike.json")
        .read_text(encoding="utf-8")
    )
    matched = alg._match_algolia_hit(fx["hits"], "Nike Air Max SC")
    assert matched is not None
    assert matched.get("brand_name") == "Nike"
    assert alg._parse_algolia_price(matched) == 32.0


def test_match_picks_best_overlap_among_candidates():
    import app.services.algolia_service as alg
    hits = [
        {"name": "Sauvage Eau de Parfum", "brand_name": "Dior",
         "price": [{"BHD": {"default": 40}}], "url": "u1", "in_stock": True},
        {"name": "Sauvage Elixir Parfum", "brand_name": "Dior",
         "price": [{"BHD": {"default": 55}}], "url": "u2", "in_stock": True},
    ]
    matched = alg._match_algolia_hit(hits, "Dior Sauvage Elixir")
    assert matched is not None
    assert "Elixir" in matched["name"]  # better word overlap than plain Sauvage


# Real-behavior stub for variant_mismatch (mirrors price_service.variant_mismatch
# qualifier-set logic) so these tests verify _match_algolia_hit CONSULTS it +
# respects its verdict, independent of whether the real price_service impl is on
# this branch yet (it lives on L1's integration branch; my module defensive-
# imports it with a no-op fallback).
_VARIANT_QUALS = {"pro", "max", "plus", "ultra", "mini", "air"}


def _stub_variant_mismatch(query: str, title: str) -> bool:
    import re as _re
    q = set(_re.findall(r"[a-z]+", (query or "").lower())) & _VARIANT_QUALS
    t = set(_re.findall(r"[a-z]+", (title or "").lower())) & _VARIANT_QUALS
    return q != t


def test_match_rejects_prefix_variant_mismatch():
    """L1 hardening: a base-model query must NOT match a pricier model-line
    variant whose name is a superset ('Galaxy S24' query vs 'Galaxy S24 Ultra'
    hit — passes strict_title_match + overlap, but a different SKU). The
    variant_mismatch guard closes this prefix-variant hole on the Algolia path.
    """
    import app.services.algolia_service as alg
    hits = [
        {"name": "Galaxy S24 Ultra 5G", "brand_name": "Samsung",
         "price": [{"BHD": {"default": 410}}], "url": "u", "in_stock": True},
    ]
    with patch("app.services.algolia_service.variant_mismatch", new=_stub_variant_mismatch):
        matched = alg._match_algolia_hit(hits, "Samsung Galaxy S24")
    assert matched is None  # Ultra is a different model-line variant — rejected


def test_match_keeps_exact_variant_when_query_specifies_it():
    """Guard is precise: 'Galaxy S24 Ultra' query DOES match the Ultra hit
    (qualifier sets equal) — variant_mismatch must not over-reject."""
    import app.services.algolia_service as alg
    hits = [
        {"name": "Galaxy S24 Ultra 5G", "brand_name": "Samsung",
         "price": [{"BHD": {"default": 410}}], "url": "u", "in_stock": True},
    ]
    with patch("app.services.algolia_service.variant_mismatch", new=_stub_variant_mismatch):
        matched = alg._match_algolia_hit(hits, "Samsung Galaxy S24 Ultra")
    assert matched is not None
    assert "Ultra" in matched["name"]


# ---------------------------------------------------------------------------
# fetch_algolia_price — orchestrator (config harvest → query → match → price)
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _no_live_cache():
    with patch("app.services.algolia_service.get_cached", return_value=None), \
         patch("app.services.algolia_service.set_cached", return_value=True):
        yield


@pytest.mark.asyncio
async def test_fetch_price_happy_path_genuine_bhd():
    """End-to-end with mocked HTTP: config harvested → Algolia query → strict
    match → genuine BHD dict with source_method=local_bhd, estimated=False."""
    import app.services.algolia_service as alg

    fenty_hit = {
        "name": "Pro Filt'r Soft Matte Longwear Foundation",
        "brand_name": "Fenty Beauty",
        "price": [{"BHD": {"default": 18.5, "default_formated": "BHD 18.500"}}],
        "url": "https://en-bh.6thstreet.com/buy-fenty-pro-filtr-230.html",
        "in_stock": True,
    }

    with patch("app.services.algolia_service._harvest_config",
               new=AsyncMock(return_value={
                   "app_id": "02X7U6O3SI",
                   "api_key": "6e9a600dc69be19481363bddd793e2f2",
                   "index": "enterprise_magento_en_bh_products",
               })), \
         patch("app.services.algolia_service._algolia_query",
               new=AsyncMock(return_value=[fenty_hit])):
        out = await alg.fetch_algolia_price(
            "en-bh.6thstreet.com", "Fenty Pro Filt'r Foundation", "makeup",
        )

    assert out is not None
    assert out["currency"] == "BHD"
    assert out["amount"] == 18.5
    assert out["source_method"] == "local_bhd"
    assert out["estimated"] is False
    assert out["retailer"] == "en-bh.6thstreet.com"
    assert out["url"].startswith("https://en-bh.6thstreet.com/")


@pytest.mark.asyncio
async def test_fetch_price_wrong_brand_returns_none():
    """The real TOMS-shoes fixture for a Tom Ford query → None (no wrong-brand
    price shipped), even though Algolia returned 1492 fuzzy hits."""
    import app.services.algolia_service as alg
    hits = _load_fixture()["hits"]

    with patch("app.services.algolia_service._harvest_config",
               new=AsyncMock(return_value={
                   "app_id": "X", "api_key": "Y", "index": "Z",
               })), \
         patch("app.services.algolia_service._algolia_query",
               new=AsyncMock(return_value=hits)):
        out = await alg.fetch_algolia_price(
            "en-bh.6thstreet.com", "Tom Ford Black Orchid", "fragrances",
        )
    assert out is None


@pytest.mark.asyncio
async def test_fetch_price_config_harvest_fails_returns_none():
    import app.services.algolia_service as alg
    with patch("app.services.algolia_service._harvest_config",
               new=AsyncMock(return_value=None)):
        out = await alg.fetch_algolia_price("x.com", "anything", "makeup")
    assert out is None


@pytest.mark.asyncio
async def test_fetch_price_empty_results_returns_none():
    import app.services.algolia_service as alg
    with patch("app.services.algolia_service._harvest_config",
               new=AsyncMock(return_value={"app_id": "X", "api_key": "Y", "index": "Z"})), \
         patch("app.services.algolia_service._algolia_query",
               new=AsyncMock(return_value=[])):
        out = await alg.fetch_algolia_price("x.com", "ghost product", "makeup")
    assert out is None


@pytest.mark.asyncio
async def test_fetch_price_query_error_returns_none_never_raises():
    import app.services.algolia_service as alg
    with patch("app.services.algolia_service._harvest_config",
               new=AsyncMock(return_value={"app_id": "X", "api_key": "Y", "index": "Z"})), \
         patch("app.services.algolia_service._algolia_query",
               new=AsyncMock(side_effect=RuntimeError("algolia 500"))):
        out = await alg.fetch_algolia_price("x.com", "anything", "makeup")
    assert out is None  # graceful — never raises


@pytest.mark.asyncio
async def test_fetch_price_disabled_by_flag(monkeypatch):
    """ENABLE_PAGE_SCRAPE gate (shared with the other Tier-1.5 entry points)."""
    import app.services.algolia_service as alg
    monkeypatch.setattr(alg, "ENABLE_PAGE_SCRAPE", False)
    harvest = AsyncMock()
    with patch("app.services.algolia_service._harvest_config", new=harvest):
        out = await alg.fetch_algolia_price("x.com", "anything", "makeup")
    assert out is None
    harvest.assert_not_called()
