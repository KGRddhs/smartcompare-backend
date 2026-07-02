"""KPI Wave A3 — revive en-bh.6thstreet.com (the only wired genuine-BH fashion source).

Recon (recon_cascade R3 + recon_fashion 2026-07-02): the store is ALIVE and
genuine-BHD, but three defects starved it —
  1. the config HARVEST broke: 6thstreet moved the index token out of the
     landing HTML into its JS chunk, and the pinned ALGOLIA_STORES index was
     applied only AFTER the all-fields completeness check, so a pinned store
     still failed on the missing HTML token;
  2. no ALGOLIA_EXPLICIT_STORES row — the live public config (app_id
     02X7U6O3SI, search-only key, en_bh index) is now pinned like sharafdg's,
     so a harvest drift can never zero the store again;
  3. the hit MATCH surface ignored the structured style_code/sku fields (the
     display name omits the model code: "Logo Detail Short Sleeves Polo
     T-Shirt" + style_code L1212), and the trailing "- {Colour} - {SKU-digits}"
     name tails tripped the numeric identity axis in _selection_match.

All HTTP + Redis mocked; the Levi's payload is a recorded 6thstreet response
(tests/fixtures/algolia_6thstreet_levis.json, recon-evidenced hits).
"""
import json
import os
from pathlib import Path

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

_FX = Path(__file__).parent / "fixtures"


def _levis_payload():
    return json.loads((_FX / "algolia_6thstreet_levis.json").read_text(encoding="utf-8"))


# Real minified 6thstreet chunk snippet (appId + search-key init defaults), as in
# test_algolia_service.py — WITHOUT the index token (variant A) and WITH it
# (variant B: the token now lives in the chunk, not the landing HTML).
_CHUNK_KEY_ONLY = (
    'o=t.env,l=void 0===o?"production":o,u=t.appId,'
    'd=void 0===u?"02X7U6O3SI":u,v=t.adminKey,'
    'p=void 0===v?"6e9a600dc69be19481363bddd793e2f2":v,'
    'f=t.index,h=void 0===f?"":f;ye.init(d,p),ye.setIndex.'
)
_CHUNK_KEY_AND_INDEX = (
    _CHUNK_KEY_ONLY
    + 'var Ee="enterprise_magento_en_bh_products";ye.setIndex(Ee);'
)

# Landing HTML with the DSN preconnect + chunk script but NO index token —
# the exact live 6thstreet shape the harvest now sees.
_PAGE_HTML_NO_INDEX = (
    '<link rel="preconnect" href="https://02X7U6O3SI-dsn.algolia.net/" '
    'crossorigin="anonymous">'
    '<script src="https://d33potchz7aua6.cloudfront.net/static/js/'
    'main.42cbd9c3.chunk.js"></script>'
)

_POLO_HIT = {
    "objectID": "901224",
    "name": "Logo Detail Short Sleeves Polo T-Shirt",
    "brand_name": "Lacoste",
    "main_brand": "Lacoste",
    "sku": "L1212_White",
    "style_code": "L1212",
    "color": "White",
    "url": "https://en-bh.6thstreet.com/logo-detail-short-sleeves-polo-t-shirt-l1212-white.html",
    "in_stock": 1,
    "price": [{"BHD": {"default": 40, "default_formated": "BHD 40.000"}}],
}


@pytest.fixture(autouse=True)
def _no_live_cache():
    # Offline-deterministic regardless of prod Redis/circuit state (mirrors
    # test_algolia_catalog_stores.py).
    with patch("app.services.algolia_service.get_cached", return_value=None), \
         patch("app.services.algolia_service.set_cached", return_value=True), \
         patch("app.services.algolia_service.is_circuit_closed", return_value=True):
        yield


def _mock_post(payload):
    resp = MagicMock()
    resp.status_code = 200
    resp.json = MagicMock(return_value=payload)
    resp.text = json.dumps(payload)
    return MagicMock(return_value=resp)


def _mock_get_pages(landing_html, chunk_js):
    """curl_cffi.requests.get replacement: landing page first, chunk second."""
    landing = MagicMock(status_code=200, text=landing_html)
    chunk = MagicMock(status_code=200, text=chunk_js)
    return MagicMock(side_effect=[landing, chunk])


# ---------------------------------------------------------------------------
# (a) generic harvest — index token found in the JS chunk
# ---------------------------------------------------------------------------

def test_extract_config_index_from_chunk_js_when_html_lacks_token():
    import app.services.algolia_service as alg
    cfg = alg.extract_algolia_config(_PAGE_HTML_NO_INDEX, _CHUNK_KEY_AND_INDEX)
    assert cfg is not None
    assert cfg["app_id"] == "02X7U6O3SI"
    assert cfg["api_key"] == "6e9a600dc69be19481363bddd793e2f2"
    assert cfg["index"] == "enterprise_magento_en_bh_products"


def test_extract_config_index_nowhere_and_no_pin_still_none():
    """Completeness preserved: no token anywhere and no pin -> None (a partial
    config would 400 the Algolia call)."""
    import app.services.algolia_service as alg
    assert alg.extract_algolia_config(_PAGE_HTML_NO_INDEX, _CHUNK_KEY_ONLY) is None


# ---------------------------------------------------------------------------
# (b) pinned index completes / overrides the harvest
# ---------------------------------------------------------------------------

def test_extract_config_pinned_index_completes_missing_harvest():
    import app.services.algolia_service as alg
    cfg = alg.extract_algolia_config(
        _PAGE_HTML_NO_INDEX, _CHUNK_KEY_ONLY,
        pinned_index="enterprise_magento_en_bh_products",
    )
    assert cfg is not None
    assert cfg["index"] == "enterprise_magento_en_bh_products"


def test_extract_config_pinned_index_overrides_drifted_token():
    """The pin wins over a drifted harvested token (HTML tokens rotate; the
    english_products index returns AED — wrong for BH)."""
    import app.services.algolia_service as alg
    html = _PAGE_HTML_NO_INDEX + '<a href="/women.html?idx=english_products">x</a>'
    cfg = alg.extract_algolia_config(
        html, _CHUNK_KEY_ONLY, pinned_index="enterprise_magento_en_bh_products",
    )
    assert cfg is not None
    assert cfg["index"] == "enterprise_magento_en_bh_products"


@pytest.mark.asyncio
async def test_harvest_config_pinned_store_survives_missing_html_index():
    """The regression that zeroed the store: a PINNED-index store must never
    fail completeness on the missing HTML token (the pin used to be applied
    only AFTER cfg was already None)."""
    import app.services.algolia_service as alg
    with patch("curl_cffi.requests.get",
               _mock_get_pages(_PAGE_HTML_NO_INDEX, _CHUNK_KEY_ONLY)):
        cfg = await alg._harvest_config("en-bh.6thstreet.com")
    assert cfg is not None
    assert cfg["index"] == "enterprise_magento_en_bh_products"
    assert cfg["app_id"] == "02X7U6O3SI"


# ---------------------------------------------------------------------------
# explicit-store row + routing
# ---------------------------------------------------------------------------

def test_6thstreet_explicit_store_row_mirrors_sharafdg_shape():
    import app.services.algolia_service as alg
    row = alg.ALGOLIA_EXPLICIT_STORES.get("en-bh.6thstreet.com")
    assert row is not None
    assert row["app_id"] == "02X7U6O3SI"
    assert row["api_key"] == "6e9a600dc69be19481363bddd793e2f2"
    # the en_bh index — english_products is the AED index (wrong for BH).
    assert row["index"] == "enterprise_magento_en_bh_products"
    assert row["currency"] == "BHD"
    assert row["genuine"] is True


@pytest.mark.asyncio
async def test_fetch_price_6thstreet_routes_explicit_not_harvest():
    """With the pinned row, 6thstreet must not depend on the fragile harvest."""
    import app.services.algolia_service as alg
    harvest = AsyncMock()
    with patch("app.services.algolia_service._harvest_config", new=harvest), \
         patch("curl_cffi.requests.post", _mock_post(_levis_payload())):
        out = await alg.fetch_algolia_price(
            "en-bh.6thstreet.com", "Levis 501", "fashion")
    assert out is not None
    harvest.assert_not_called()


# ---------------------------------------------------------------------------
# (c) recorded Levi's 501 payload -> genuine local_bhd, SKU tail stripped
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_levis_501_resolves_genuine_local_bhd_with_clean_title():
    import app.services.algolia_service as alg
    with patch("curl_cffi.requests.post", _mock_post(_levis_payload())):
        out = await alg.fetch_algolia_price(
            "en-bh.6thstreet.com", "Levis 501", "fashion")
    assert out is not None
    assert out["currency"] == "BHD"
    assert out["amount"] == pytest.approx(24.0)
    assert out["source_method"] == "local_bhd"
    assert out["estimated"] is False
    assert out["in_stock"] is True
    assert out["retailer"] == "en-bh.6thstreet.com"
    assert out["url"] == (
        "https://en-bh.6thstreet.com/501-original-fit-jeans-black-00501-0660.html"
    )
    # SKU-digit tail stripped from the STORED title; the colour word stays
    # (it is a legit axis).
    assert out["title"] == "501 Original Fit Jeans - Black"
    assert "00501" not in out["title"]


# ---------------------------------------------------------------------------
# SKU-tail strip — conservative by construction
# ---------------------------------------------------------------------------

def test_strip_sku_tail_conservative():
    import app.services.algolia_service as alg
    strip = alg._strip_sku_tail
    # strips: trailing digits-and-dashes SKU segments
    assert strip("501 Original Fit Jeans - Black - 00501-0660") == \
        "501 Original Fit Jeans - Black"
    assert strip("Air Jordan 1 - 555088") == "Air Jordan 1"
    # keeps: colour words, short/meaningful numbers, 4-digit year-form tails
    assert strip("501 Original Fit Jeans - Black") == "501 Original Fit Jeans - Black"
    assert strip("Levis - 501") == "Levis - 501"
    assert strip("Galaxy Tab S9 - 2023") == "Galaxy Tab S9 - 2023"
    assert strip("Air Force 1") == "Air Force 1"
    assert strip("") == ""
    # keeps: SEASON/YEAR-RANGE tails (Wave B2, review LOW) — "- 2023-24" on a
    # sports jersey is the season, i.e. product IDENTITY, not catalog plumbing.
    # Stripping it broke numbers_match against a season-stated query AND lost
    # the discriminator from the stored title. Only a leading-zero or 5+-digit
    # first run is SKU-shaped for the dash form ("00501-0660" still strips).
    assert strip("Real Madrid Home Jersey - 2023-24") == \
        "Real Madrid Home Jersey - 2023-24"
    assert strip("Nike Dunk Low - 2024-25") == "Nike Dunk Low - 2024-25"
    # still strips: SKU-shaped dash runs (leading zero / 5+-digit first run)
    assert strip("Jersey - 12345-678") == "Jersey"
    assert strip("Thing - 0123-456") == "Thing"


def test_season_range_survives_in_match_surface_and_stored_title():
    """Wave B2 — the season tail must survive BOTH the match surface
    (_hit_title strips via _strip_sku_tail) and the stored title (the fetch
    path strips with the same function), so numbers_match keeps working for a
    season-stated query and the cached title keeps its discriminator."""
    import app.services.algolia_service as alg
    hit = {"name": "Real Madrid Home Jersey - 2023-24", "brand_name": "Adidas"}
    assert alg._hit_title(hit) == "Adidas Real Madrid Home Jersey - 2023-24"
    assert alg._strip_sku_tail("Real Madrid Home Jersey - 2023-24") == \
        "Real Madrid Home Jersey - 2023-24"


# ---------------------------------------------------------------------------
# (d) style_code in the match surface — BOTH directions
# ---------------------------------------------------------------------------

def _store():
    import app.services.algolia_service as alg
    return alg.ALGOLIA_EXPLICIT_STORES["en-bh.6thstreet.com"]


def test_l1212_query_matches_polo_hit_via_style_code():
    """The display name omits the model code — the structured style_code is
    what lets 'Lacoste L1212 Polo' find the listing."""
    import app.services.algolia_service as alg
    matched = alg._catalog_match_hit(
        [_POLO_HIT], "Lacoste L1212 Polo", _store(), resolved_category="fashion")
    assert matched is not None
    assert matched["style_code"] == "L1212"


def test_different_style_code_hit_does_not_match():
    """Reject direction 1: a DIFFERENT style_code must not bridge the match."""
    import app.services.algolia_service as alg
    other = dict(_POLO_HIT, style_code="PH4012", sku="PH4012_Navy")
    assert alg._catalog_match_hit(
        [other], "Lacoste L1212 Polo", _store(), resolved_category="fashion") is None


def test_polo_hit_without_style_code_does_not_match():
    """Reject direction 2: the L1212 query matches ONLY when the structured
    code is present — the bare descriptive name stays rejected."""
    import app.services.algolia_service as alg
    bare = {k: v for k, v in _POLO_HIT.items() if k not in ("style_code", "sku")}
    assert alg._catalog_match_hit(
        [bare], "Lacoste L1212 Polo", _store(), resolved_category="fashion") is None


def test_style_code_surface_generic_path_parity():
    """The harvest-path matcher gains the same structured-code surface (future
    Algolia stores get the fix for free)."""
    import app.services.algolia_service as alg
    matched = alg._match_algolia_hit(
        [_POLO_HIT], "Lacoste L1212 Polo", resolved_category="fashion")
    assert matched is not None


def test_style_code_confirmation_still_respects_leak_gate():
    """The structured-code override relaxes ONLY the variant-add direction —
    a query discriminator missing from the surface (leak direction) still
    rejects even with the style_code confirmed."""
    import app.services.algolia_service as alg
    assert alg._catalog_match_hit(
        [_POLO_HIT], "Lacoste L1212 Slim Fit Polo", _store(),
        resolved_category="fashion") is None


def test_confirmed_style_code_rules():
    """Letter+digit model codes only (a pure-digit code would inject numeric
    noise into the identity axes), and QUERY-CONFIRMED only (an unqueried code
    in the surface would read as a variant-add and over-reject)."""
    import app.services.algolia_service as alg
    # confirmed: query carries the code
    assert alg._confirmed_style_code(_POLO_HIT, {"lacoste", "l1212", "polo"}) == "L1212"
    # sku fallback when style_code absent
    sku_only = {k: v for k, v in _POLO_HIT.items() if k != "style_code"}
    assert alg._confirmed_style_code(sku_only, {"lacoste", "l1212", "polo"}) == "L1212"
    # hyphen-folded comparison (normalize_words strips hyphens in query tokens)
    assert alg._confirmed_style_code(
        {"style_code": "NKCW4554-001"}, {"nike", "nkcw4554001"}) == "NKCW4554-001"
    # NOT confirmed: code absent from the query
    assert alg._confirmed_style_code(_POLO_HIT, {"lacoste", "polo"}) == ""
    # pure-digit codes never enter the surface
    assert alg._confirmed_style_code(
        {"style_code": "00501-0660", "sku": "00501-0660_BLACK"},
        {"levis", "501", "005010660"}) == ""


@pytest.mark.asyncio
async def test_polo_end_to_end_genuine_local_bhd():
    import app.services.algolia_service as alg
    with patch("curl_cffi.requests.post", _mock_post({"hits": [_POLO_HIT]})):
        out = await alg.fetch_algolia_price(
            "en-bh.6thstreet.com", "Lacoste L1212 Polo", "fashion")
    assert out is not None
    assert out["amount"] == pytest.approx(40.0)
    assert out["source_method"] == "local_bhd"
    assert out["in_stock"] is True


# ---------------------------------------------------------------------------
# Wave B2 (review LOW) — explicit-"other" re-inference in the override path
# ---------------------------------------------------------------------------
# _selection_match re-infers an explicit "other" category before its axes
# (price_service.py explicit-other re-inference), so it rejects a both-stated
# fashion contradiction — but the structured-identity override then called
# _axis_mismatch with the RAW "other" (category-blind: fashion clothing-size /
# colour / material / fit axes skipped) and re-ACCEPTED the hit the selector
# had just rejected. Both matchers must mirror the re-inference.

_XXL_POLO_HIT = dict(_POLO_HIT, name="Logo Detail Short Sleeves Polo T-Shirt XXL")

# "t-shirt" makes _infer_category_from_query resolve fashion; XL vs the hit's
# XXL is a BOTH-STATED clothing-size contradiction (a fashion-scoped axis).
_OTHER_CAT_QUERY = "Lacoste L1212 Polo T-Shirt XL"


def test_catalog_override_reinfers_explicit_other():
    """Catalog path: an "other"-category query with a both-stated clothing-size
    contradiction must reject THROUGH the structured-identity override too."""
    import app.services.algolia_service as alg
    assert alg._catalog_match_hit(
        [_XXL_POLO_HIT], _OTHER_CAT_QUERY, _store(),
        resolved_category="other") is None


def test_algolia_override_reinfers_explicit_other():
    """Harvest path (_match_algolia_hit): same re-inference parity."""
    import app.services.algolia_service as alg
    assert alg._match_algolia_hit(
        [_XXL_POLO_HIT], _OTHER_CAT_QUERY, resolved_category="other") is None


def test_override_under_other_still_accepts_without_contradiction():
    """Over-rejection guard for the fix: the SAME query shape WITHOUT the size
    contradiction keeps matching under explicit "other" — the override still
    accepts descriptive-word supersets around a query-confirmed style code."""
    import app.services.algolia_service as alg
    q = "Lacoste L1212 Polo T-Shirt"
    assert alg._catalog_match_hit(
        [_POLO_HIT], q, _store(), resolved_category="other") is not None
    assert alg._match_algolia_hit(
        [_POLO_HIT], q, resolved_category="other") is not None
