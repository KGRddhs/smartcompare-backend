"""Wave B (B0) — carry the MATCHED identity onto price dicts + cache-gate parity.

The Wave-A review HIGH (wavea_review.json): Wave A relaxed acceptance INSIDE the
adapter matchers (candidate_brand surface, query-confirmed style_code override)
but never carried the matched identity onto the returned price dict — so the
fail-closed downstream gates re-rejected exactly the titles the wave unlocked:
select_best in the consume path reads c["brand"] (-> "") and should_cache_price
replays _selection_match with candidate_brand (-> ""), so the 6thstreet Levi's
501 / L1212 polo prices resolved+displayed live but were NEVER cached (warmed
KPI RED for kpi-fash-003/005), and klinq's brand-omitting fragrance titles were
accepted by _best_match then dropped by select_best.

B0 (this wave):
  1. BRAND STAMP — the matched hit/node brand is stamped onto the returned
     price dict in all three builders (algolia harvest + explicit paths,
     magento shape A/B), mirroring the PR#13 JSON-LD identity stamp. Flag-gated
     (exact_gate_enabled) for flag-OFF byte-identity, matching the precedent.
  2. STYLE-CODE CARRIAGE — the QUERY-CONFIRMED style code rides the price dict
     (key `structured_code`), and should_cache_price gains the SAME bounded
     structured-identity override the algolia matcher runs (A3): ONLY the
     superset/variant-add rejection is relaxed; leak direction
     (strict_title_match), numbers, axis contradictions, listing-url/OOS/
     identity checks all stay enforced.

Both directions pinned: acceptance (Levi's / klinq through the FULL KPI
contract vs the REAL truth entries; polo through the write gate) and
adversarial (a wrong-brand stamp is not a bypass; an unqueried structured_code
relaxes nothing; an axis-contradicting candidate still refuses; a pure-digit
code never bridges models; flag-OFF carries no stamps).

Wave B-FIX BF5 (sweep OR-5) — EVAL-CONTRACT PARITY: the KPI contract
(usable_exact_genuine_for_product) now mirrors the SAME bounded structured-code
override the write gate runs (_structured_code_cache_override, post-BF2
bounds), so the L1212 dict the runtime caches finally also COUNTS usable
against the real truth entry (the polo xfail was promoted). A wrong-brand,
unqueried-code, or variant-add (gift-set) dict still refuses at the KPI end —
pinned in the eval-contract-bounds section below.
"""
import json
import os
from pathlib import Path

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import app.services.algolia_service as alg
import app.services.magento_graphql_service as mg
from app.services.price_service import select_best, should_cache_price
from scripts.eval_runner import load_usable_exact_genuine_truth

# The measure helper (task 3: verify through scripts/measure_warmed_kpi._usable,
# which wraps the authoritative eval_runner.usable_exact_genuine_for_product).
# Importing the module sets warm-flow env knobs at import time — snapshot +
# restore so this test file never contaminates the rest of the suite's env.
_MEASURE_ENV_KEYS = (
    "PRICE_RACE_TIMEOUT", "STREAM_HARD_CAP_SECONDS", "FAN_OUT_BUDGET_SECONDS",
    "FIRECRAWL_TIMEOUT", "SCRAPEDO_TIMEOUT",
)
_saved_env = {k: os.environ.get(k) for k in _MEASURE_ENV_KEYS}
from scripts.measure_warmed_kpi import _usable as measure_usable  # noqa: E402
for _k, _v in _saved_env.items():
    if _v is None:
        os.environ.pop(_k, None)
    else:
        os.environ[_k] = _v

_FX = Path(__file__).parent / "fixtures"

# REAL truth entries (task 3: the FULL KPI contract, not just the write gate).
_TRUTH = {t["id"]: t for t in load_usable_exact_genuine_truth()}
FASH_003 = _TRUTH["kpi-fash-003"]   # Levis 501 Original Fit Jeans
FASH_005 = _TRUTH["kpi-fash-005"]   # Lacoste L1212 Polo
FRAG_001 = _TRUTH["kpi-frag-001"]   # YSL Black Opium Eau de Parfum 90ml


def _levis_payload():
    """Recorded 6thstreet Algolia response (recon-evidenced, brand_name Levi's)."""
    return json.loads((_FX / "algolia_6thstreet_levis.json").read_text(encoding="utf-8"))


# Recon-evidenced 6thstreet hit (recon_fashion 2026-07-02): the display name
# omits the model code; the structured style_code carries it.
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

# klinq (magento Shape B) — the brand-omitting fragrance title; brand_name is
# the store's pinned human-label field (Wave A4). The adapter receives the
# PARSED search query (brand spelled out), the KPI runs the RAW truth query.
_KLINQ_ITEM = {
    "name": "Black Opium Eau De Parfum 90ml",
    "brand_name": "Yves Saint Laurent",
    "sku": "ysl-bo-edp-90",
    "url_key": "black-opium-eau-de-parfum-90ml",
    "stock_status": "IN_STOCK",
    "price_range": {"minimum_price": {
        "final_price": {"value": 45.9, "currency": "BHD"},
        "regular_price": {"value": 45.9, "currency": "BHD"},
    }},
}
_KLINQ_QUERY_PARSED = "Yves Saint Laurent Black Opium Eau de Parfum 90ml"


@pytest.fixture(autouse=True)
def _offline_deterministic(monkeypatch):
    """Offline-deterministic regardless of prod Redis/circuit state (mirrors
    test_algolia_catalog_stores.py) + exact gate ON + magento scrape enabled."""
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "true")
    monkeypatch.setattr(alg, "ENABLE_PAGE_SCRAPE", True, raising=False)
    monkeypatch.setattr(mg, "ENABLE_PAGE_SCRAPE", True, raising=False)
    mg._CONFIG_CACHE.clear()
    with patch("app.services.algolia_service.get_cached", return_value=None), \
         patch("app.services.algolia_service.set_cached", return_value=True), \
         patch("app.services.algolia_service.is_circuit_closed", return_value=True):
        yield
    mg._CONFIG_CACHE.clear()


def _mock_post(payload):
    resp = MagicMock()
    resp.status_code = 200
    resp.json = MagicMock(return_value=payload)
    resp.text = json.dumps(payload)
    return MagicMock(return_value=resp)


async def _fetch_6thstreet(query, payload):
    with patch("curl_cffi.requests.post", _mock_post(payload)):
        return await alg.fetch_algolia_price("en-bh.6thstreet.com", query, "fashion")


class _FakeResp:
    def __init__(self, text: str = "", status_code: int = 200):
        self.text = text
        self.status_code = status_code

    def json(self):
        return json.loads(self.text)


async def _fetch_klinq(query):
    from curl_cffi import requests as curl_requests
    payload = json.dumps({"data": {"products": {"items": [_KLINQ_ITEM]}}})
    with patch.object(curl_requests, "post", lambda *a, **k: _FakeResp(payload)):
        return await mg.fetch_magento_graphql_price(
            "klinq.com", query, resolved_category="fragrances")


def _levis_price_dict(**over):
    """Hand-built cached-dict shape mirroring the algolia explicit builder."""
    base = {
        "amount": 24.0, "currency": "BHD", "retailer": "en-bh.6thstreet.com",
        "url": "https://en-bh.6thstreet.com/501-original-fit-jeans-black-00501-0660.html",
        "in_stock": True, "estimated": False, "source_method": "local_bhd",
        "title": "501 Original Fit Jeans - Black", "confidence": 0.9,
    }
    base.update(over)
    return base


def _polo_price_dict(**over):
    base = {
        "amount": 40.0, "currency": "BHD", "retailer": "en-bh.6thstreet.com",
        "url": "https://en-bh.6thstreet.com/logo-detail-short-sleeves-polo-t-shirt-l1212-white.html",
        "in_stock": True, "estimated": False, "source_method": "local_bhd",
        "title": "Logo Detail Short Sleeves Polo T-Shirt", "confidence": 0.9,
        "brand": "Lacoste", "structured_code": "L1212",
    }
    base.update(over)
    return base


# ---------------------------------------------------------------------------
# (1) builder stamps — brand + query-confirmed structured code on the dict
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_algolia_explicit_builder_stamps_brand_levis():
    out = await _fetch_6thstreet("Levis 501 Original Fit Jeans", _levis_payload())
    assert out is not None
    assert out["brand"] == "Levi's"
    # style_code "00501-0660" is PURE-DIGIT -> never a structured_code stamp
    # (a digit code would inject numeric noise into the identity axes).
    assert "structured_code" not in out
    # legacy keys intact
    assert out["source_method"] == "local_bhd"
    assert out["title"] == "501 Original Fit Jeans - Black"


@pytest.mark.asyncio
async def test_algolia_explicit_builder_stamps_brand_and_code_polo():
    out = await _fetch_6thstreet("Lacoste L1212 Polo", {"hits": [_POLO_HIT]})
    assert out is not None
    assert out["brand"] == "Lacoste"
    assert out["structured_code"] == "L1212"


@pytest.mark.asyncio
async def test_algolia_harvest_builder_stamps_brand_and_code(monkeypatch):
    """The generic harvest path (~:713 builder) gains the same stamps."""
    monkeypatch.setattr(alg, "_harvest_config", AsyncMock(return_value={
        "app_id": "X", "api_key": "Y", "index": "Z"}))
    monkeypatch.setattr(alg, "_algolia_query", AsyncMock(return_value=[_POLO_HIT]))
    out = await alg.fetch_algolia_price("fake-store.bh", "Lacoste L1212 Polo", "fashion")
    assert out is not None
    assert out["brand"] == "Lacoste"
    assert out["structured_code"] == "L1212"


@pytest.mark.asyncio
async def test_magento_shape_b_builder_stamps_brand():
    out = await _fetch_klinq(_KLINQ_QUERY_PARSED)
    assert out is not None
    assert out["brand"] == "Yves Saint Laurent"
    assert out["source_method"] == "magento_graphql_bhd"
    assert out["title"] == "Black Opium Eau De Parfum 90ml"


@pytest.mark.asyncio
async def test_stamps_absent_flag_off(monkeypatch):
    """Flag-OFF byte-identity (the PR#13 JSON-LD stamp precedent): no new keys
    on the rollback path. (klinq flag-OFF: the A4 candidate_brand acceptance is
    itself flag-gated inside strict_title_match, so the brand-omitting title is
    legacy-rejected -> None.)"""
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "false")
    out = await _fetch_6thstreet("Lacoste L1212 Polo", {"hits": [_POLO_HIT]})
    assert out is not None
    assert "brand" not in out
    assert "structured_code" not in out
    assert await _fetch_klinq(_KLINQ_QUERY_PARSED) is None


# ---------------------------------------------------------------------------
# (2) FULL KPI contract — write gate AND usable_exact_genuine, REAL truth rows
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_levis_full_kpi_contract():
    """kpi-fash-003: builder output -> should_cache_price -> measure _usable."""
    out = await _fetch_6thstreet(FASH_003["query"], _levis_payload())
    assert out is not None
    assert out["brand"] == "Levi's"
    assert should_cache_price(FASH_003["query"], out, "fashion") is True
    assert measure_usable(out, FASH_003) is True


@pytest.mark.asyncio
async def test_klinq_full_kpi_contract():
    """kpi-frag-001: the brand stamp is what unlocks BOTH the write gate and
    the KPI identity check (YSL alias fold carries the raw truth query)."""
    out = await _fetch_klinq(_KLINQ_QUERY_PARSED)
    assert out is not None
    assert out["brand"] == "Yves Saint Laurent"
    assert should_cache_price(FRAG_001["query"], out, "fragrances") is True
    assert measure_usable(out, FRAG_001) is True


@pytest.mark.asyncio
async def test_polo_write_gate_passes_via_structured_code():
    """kpi-fash-005 write gate: the query-confirmed structured code relaxes the
    variant-add direction (descriptive 6thstreet words), so the CORRECT product
    now caches."""
    out = await _fetch_6thstreet(FASH_005["query"], {"hits": [_POLO_HIT]})
    assert out is not None
    assert out["structured_code"] == "L1212"
    assert should_cache_price(FASH_005["query"], out, "fashion") is True


@pytest.mark.asyncio
async def test_polo_kpi_contract_counts_via_structured_code():
    """kpi-fash-005 KPI — PROMOTED from the Wave-B xfail (BF5, sweep OR-5):
    the eval contract mirrors the write gate's bounded structured-code
    override (_structured_code_cache_override — query-confirmed code +
    strict leak-direction + numbers + axis checks, post-BF2 tightening), so
    the cached L1212 dict now COUNTS usable against the REAL truth entry.
    The KPI definition is "exact requested SKU" — a query-confirmed retailer
    style code IS exactness evidence, but ONLY under the full BF2 bounds."""
    out = await _fetch_6thstreet(FASH_005["query"], {"hits": [_POLO_HIT]})
    assert out is not None
    assert should_cache_price(FASH_005["query"], out, "fashion") is True
    assert measure_usable(out, FASH_005) is True


# ---------------------------------------------------------------------------
# (2b) BF5 eval-contract BOUNDS — the KPI-side override is the SAME bounded
# override as the write gate; it must never become a bypass either.
# ---------------------------------------------------------------------------

def test_kpi_contract_wrong_brand_dict_still_refuses():
    """BF5 bound: the KPI-side override keeps strict's leak direction — a
    wrong-brand stamp leaves the query's own 'lacoste' token missing from the
    brand+title+code surface, so the dict never counts usable."""
    assert measure_usable(_polo_price_dict(brand="Fred Perry"), FASH_005) is False


def test_kpi_contract_unqueried_code_still_refuses():
    """BF5 bound: a code the truth query never stated relaxes NOTHING at the
    KPI end (query_confirmed_structured_code returns ''), and a dict with no
    code at all keeps the plain _selection_match verdict (refuses on the
    descriptive variant-adds)."""
    assert measure_usable(
        _polo_price_dict(structured_code="PH4012"), FASH_005) is False
    bare = {k: v for k, v in _polo_price_dict().items()
            if k != "structured_code"}
    assert measure_usable(bare, FASH_005) is False


def test_kpi_contract_variant_add_through_code_still_refuses():
    """BF5 bound: the BF2 sellable-unit fence holds at the KPI end too — a
    gift-set add riding the confirmed model code is a DIFFERENT purchasable
    unit and never counts usable."""
    p = _polo_price_dict(
        title="Logo Detail Short Sleeves Polo T-Shirt Gift Set with Cap")
    assert measure_usable(p, FASH_005) is False


# ---------------------------------------------------------------------------
# (3) adversarial — the stamps/override must never become a bypass
# ---------------------------------------------------------------------------

def test_wrong_brand_stamp_is_not_a_bypass():
    """A wrong-brand stamp keeps the QUERY's own brand token required — on the
    main _selection_match path AND inside the structured-code override."""
    wrong = _levis_price_dict(title="501 Slim Fit Chinos - Black", brand="Dockers")
    assert should_cache_price("Levis 501 Original Fit Jeans", wrong, "fashion") is False
    assert select_best([wrong], "Levis 501 Original Fit Jeans", "fashion") is None
    # override path: confirmed code + WRONG brand still refuses (strict leak
    # direction: "lacoste" is required and absent from the surface).
    wrong2 = _polo_price_dict(brand="Fred Perry")
    assert should_cache_price("Lacoste L1212 Polo", wrong2, "fashion") is False


def test_unqueried_structured_code_relaxes_nothing():
    # a code the QUERY never stated must not engage the override...
    p = _polo_price_dict(structured_code="PH4012")
    assert should_cache_price("Lacoste L1212 Polo", p, "fashion") is False
    # ...and a query without the code token gets no relaxation either.
    p2 = _polo_price_dict()
    assert should_cache_price("Lacoste Classic Polo", p2, "fashion") is False


def test_structured_code_never_overrides_axis_contradiction():
    """A confirmed code must NOT bridge an explicit discriminating axis: the
    clothing-size axis (Size M queried vs Size L candidate — single letters
    survive strict_title_match's len>2 filter, so ONLY the axis catches it)."""
    p = _polo_price_dict(title="Logo Detail Short Sleeves Polo T-Shirt Size L")
    assert should_cache_price("Lacoste L1212 Polo Size M", p, "fashion") is False


def test_pure_digit_structured_code_never_relaxes():
    """A pure-digit code ("501" — catalog plumbing, not a model assertion) must
    never bridge a different model: without the letter+digit guard the override
    surface would pass strict/numbers/axis and wrongly cache."""
    p = _levis_price_dict(title="Jeans - Black", brand="Levi's", structured_code="501")
    assert should_cache_price("Levis 501 Jeans", p, "fashion") is False


def test_missing_stamp_stays_fail_closed():
    """No brand stamp (legacy dict) -> the brand-omitting title still refuses:
    the stamp is the ONLY unlock (pins the review's reproduction)."""
    klinq_bare = {
        "amount": 45.9, "currency": "BHD", "retailer": "klinq.com",
        "url": "https://klinq.com/black-opium-eau-de-parfum-90ml.html",
        "in_stock": True, "estimated": False,
        "source_method": "magento_graphql_bhd",
        "title": "Black Opium Eau De Parfum 90ml", "confidence": 0.9,
    }
    assert should_cache_price(FRAG_001["query"], klinq_bare, "fragrances") is False


# ---------------------------------------------------------------------------
# (4) select_best consume path (scs._consume_adapter_prefetch reads c["brand"])
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_select_best_keeps_brand_stamped_klinq_candidate():
    """The review's (b) scenario: _best_match accepts the brand-omitting klinq
    title, then select_best in the consume path dropped it (brand key missing).
    With the stamp the candidate is KEPT; without it, still dropped."""
    out = await _fetch_klinq(_KLINQ_QUERY_PARSED)
    assert out is not None
    kept = select_best([out], FRAG_001["query"], "fragrances")
    assert kept is not None
    assert kept["retailer"] == "klinq.com"
    bare = {k: v for k, v in out.items() if k != "brand"}
    assert select_best([bare], FRAG_001["query"], "fragrances") is None
