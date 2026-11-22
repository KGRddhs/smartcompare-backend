"""PC1 PARK-KEEP-GENUINE (S98-FIX incident data lane): the RED rows.

Spec: PC1_SPEC.md of the S98-FIX lane (the research plan of 2026-11-21, section 3.4 PC1).
Switch: ENABLE_PRICE_NOT_LOST (INC-P2, PR #418), default OFF, read per call; OFF on web.
GREEN rule (spec section 3): inside ENABLE_PRICE_NOT_LOST a converted adapter yield never
replaces a genuine park on the request; and, ONLY if the owner joins the size fix to this
unit (spec section 3.2, rows R15-R19), the Shopify matcher prices the variant of the typed
size and sorts sizes as numbers.

Classes: RED = fails on main d2f49d8b on an AssertionError; PIN = passes on main and must
keep passing. Nothing here was run when it was written: the RED gate runs it at the base.

Data (nothing in this file reaches a shop or the network):
- LOG: the relay's read of the server log of 2026-11-18, 18:43-18:44 UTC (R0 fact sheet,
  section (a)): the Tier-1 pick "Selected: Asgharali (tier 0.5) at BHD 59.41 ... (1
  candidates; variant_rank=2.0 size=200ml conc=EDP)" from shopping_region=us_fallback;
  "Shopify reseller hit parked as fallback, 29.900 BHD via bh.asgharali.com" (Maheeb) and
  "10.000 BHD via bh.asgharali.com" (Mubeen); two "[L2.6] Phase 1 race timeout for price
  (limit 15.0s)" lines; "race miss for Maheeb Edp 200ML -> returning parked converted_usd
  price (never None)"; no converted adapter line for Mubeen; PRICE_OUTCOME slot 0 shown=no
  size_ml=200 pend_reason=pending_genuine display_rule=non_pdp_url, slot 1 shown=no
  size_ml=none pend_reason=pending_genuine display_rule=none.
- PAGE: the relay's read of the house shop's public pages on 2026-11-21 (research track P2,
  section 1.1): store currency BHD, country BH; single-variant items; titles carry the size
  and "Edp"; the search page lists "Maheeb Edp 200ML" at BHD 29.900
  (/products/maheeb-edp-200ml-1) and "Mubeen Edp 100ml" at BHD 10.000
  (/products/mubeen-edp-100ml); vendor strings "Asgharali" and "Asgharali - Bahrain". The
  stock flag and the variant title were NOT read (the shop answered 429): "available" is
  walked both ways (R11) and "Default Title" stands for the one variant (an assumption).
- SYNTHETIC: the 59.41 row's url (the shop's search link, what build_retailer_url maps this
  seller to) and title (a title the identity rule accepts, as the logged pick shows); the
  converted Gulf row (store-kw.example.com, 11.250); the multi-variant house products
  (house-b.example.com, line word "Lumen", 4.500 / 6.500 / 10.000); the YSL Y sellers.

The cap is replayed with the primitive the Phase-1 race uses (asyncio.wait_for around the
REAL _get_price) and, on the timeout, the same handler call (_price_fallback_on_miss), as
structured_comparison_service.py does at d2f49d8b (:6362-6369, :6644-6654). The cascade's
network leaves are stubbed as tests/test_negcache_outage_and_converted_fallback.py does
(_stub_cascade); the discovery search never returns, so the cap fires after the Shopify
block and the adapter consume, where it fired on 2026-11-18.

Pure ASCII, LF.
"""
from __future__ import annotations

import asyncio
import contextvars
import copy
import logging
import os
import re
from types import SimpleNamespace

import pytest

os.environ.setdefault("OPENAI_API_KEY", "sk" + "-test-dummy")

import app.main  # noqa: F401,E402  (FIRST: the dotenv guard)
from app.services import price_service as ps  # noqa: E402
from app.services import response_builder as rb  # noqa: E402
import app.services.structured_comparison_service as scs  # noqa: E402

FRAG = "fragrances"
PNL = "ENABLE_PRICE_NOT_LOST"
VG = "ENABLE_VARIANT_MIN_PRICE_GUARD"
PRIO = "ENABLE_GENUINE_PRICE_PRIORITY"
LMG = "ENABLE_LISTING_MATCH_GUARD"
FIX = "ENABLE_FRAGRANCE_SIZE_RECONCILE_FIX"
AXES = "ENABLE_VARIANT_DESCRIPTOR_AXES"

# The production configuration (H12 c + H13 c, the R0 fact sheet section (b)), as the INC-P2
# pure file sets it. ENABLE_GENUINE_PRICE_PRIORITY and ENABLE_FRAGRANCE_SIZE_RECONCILE_FIX are
# SET on web with unknown values: the rows that depend on them walk both.
PROD_ON = (
    "ENABLE_LLM_LEDGER_V2", "ENABLE_LLM_SPEND_BREAKER", "ENABLE_REQUEST_CONTEXT_HEADERS",
    "ENABLE_OPENAI_EGRESS_STOP", "ENABLE_OPENAI_PRE_V3", "ENABLE_ANTHROPIC_TEXT",
    "ENABLE_ANTHROPIC_VERDICT", "ENABLE_LEGACY_FINGERPRINT_READER", "ENABLE_CONSENT_PERSIST",
    "ENABLE_COMPARE_AUTH_REQUIRED", "ENABLE_OFFLOOP_DNS_RESOLVE", "ENABLE_PRICE_PARSE_OFFLOAD",
    "ENABLE_EXACT_PRICE_GATE",
)
PROD_OFF = (
    "ENABLE_ANTHROPIC_MODERATION", "ENABLE_ANTHROPIC_VISION", "ENABLE_KB_INGEST",
    "ENABLE_KB_FIRST_SERVE", "ENABLE_FIELD_STATUS_METADATA", "ENABLE_RESULT_STATUS_METADATA",
    "ENABLE_FRAGRANCE_ONLY_GATE", "ENABLE_DATA_GUARDS_V2", "ENABLE_ASYNC_REDIS_OFFLOAD",
    "ENABLE_COMPARE_RUN_LEDGER", "ENABLE_GENUINE_PRICE_PRIORITY", "ENABLE_LISTING_MATCH_GUARD",
    "ENABLE_REGION_CURRENCY_GUARD", "ENABLE_PRESCORING_SHOWABLE_GUARD", "WARMER_CONTEXT",
    "ENABLE_CONFIDENCE_SINGLE_COMPUTATION", "ENABLE_L2_PROMOTION_REMAINING_TTL",
)
# Not set on web (R0 section (b)) or a flag of a unit not merged: unset in every row unless the
# row sets it.
UNIT_UNSET = (
    PNL, VG, FIX, AXES, "ENABLE_PRODUCT_RESOLVER", "ENABLE_WIDE_SIGNAL_TEXT",
    "ENABLE_SHOPPING_STRICT_CURRENCY", "ENABLE_SHOPPING_CURRENCY_TRUTH",
    "ENABLE_SHOPPING_DISCOVERY_URL_SPLIT", "ENABLE_PARK_LISTING_URL_TIER1",
    "ENABLE_HOME_SAVINGS_AGGREGATE", "ENABLE_BH_GCC_CATALOG_SOURCES", "ENABLE_ZYTE_RENDER",
    "ENABLE_MATCH_FOLD", "PRICE_CACHE_BUST",
)

CAP_S = 4.0  # the replayed price cap (production: 15.0 s); the cascade hangs in discovery

# --------------------------------------------------------------------------- the logged case
MAHEEB = "Maheeb Edp 200ML"   # the typed halves of "Maheeb Edp 200ML vs Mubeen Edp 100ml"
MUBEEN = "Mubeen Edp 100ml"
PAIR_Q = "%s vs %s" % (MAHEEB, MUBEEN)
HOUSE_HOST = "bh.asgharali.com"
MAHEEB_URL = "https://bh.asgharali.com/products/maheeb-edp-200ml-1"
MUBEEN_URL = "https://bh.asgharali.com/products/mubeen-edp-100ml"


def house_catalog(available=True):
    """The house shop's /products.json as the page reading shows it (PAGE): BHD store, the two
    products, one variant each, the size in the title."""
    return {"_store_currency": "BHD", "products": [
        {"title": "Maheeb Edp 200ML", "handle": "maheeb-edp-200ml-1", "vendor": "Asgharali",
         "product_type": "", "tags": ["Perfumes"],
         "variants": [{"title": "Default Title", "price": "29.900", "available": available}]},
        {"title": "Mubeen Edp 100ml", "handle": "mubeen-edp-100ml", "vendor": "Asgharali - Bahrain",
         "product_type": "", "tags": ["Perfumes"],
         "variants": [{"title": "Default Title", "price": "10.000", "available": available}]},
    ]}


def maheeb_tier1_park():
    """The logged Tier-1 pick (LOG): BHD 59.41, seller Asgharali, tier 0.5, 200ml, EDP, from
    the us_fallback pool, parked as converted_usd (the race-miss line names that method)."""
    return {"amount": 59.41, "currency": "BHD", "source_method": "converted_usd",
            "retailer": "Asgharali", "retailer_score": 0.5,
            "url": "https://bh.asgharali.com/search?q=Maheeb+Edp+200ML",
            "title": "Maheeb Eau De Parfum 200ml", "size": "200ml", "in_stock": True,
            "estimated": False}


def gulf_converted_row():
    """SYNTHETIC: a Gulf adapter's converted-only yield for Mubeen (the PNL-3 order), in the
    shape the woo adapter returns (tests/test_negcache_outage_and_converted_fallback.py)."""
    return {"amount": 11.25, "currency": "BHD", "retailer": "store-kw.example.com",
            "url": "https://store-kw.example.com/product/mubeen-edp-100ml", "in_stock": True,
            "estimated": False, "confidence": 0.85, "source_method": "converted_usd",
            "original_currency": "KWD", "title": "Mubeen Edp 100ml"}


def lumen_catalog(variants, title="Lumen Edp 100ml"):
    """SYNTHETIC multi-variant house product (H16: a pin that needs several sizes is built from
    a fixture); the shape of tests/test_variant_min_price_guard.py::_shopify_catalog."""
    return {"_store_currency": "BHD", "products": [
        {"title": title, "vendor": "House B", "handle": "lumen-edp", "variants": variants}]}


def v(size, price, available=True):
    return {"title": size, "price": price, "available": available}


LUMEN_HOST = "house-b.example.com"
LUMEN_TYPED = "Lumen Edp 100ml"
# Shape 1: the title states the typed size, the FIRST variant is another size.
LUMEN_FIRST_30 = [v("30ml", "4.500"), v("100ml", "10.000")]
# Shape 2: the title states the typed size, NO variant is that size.
LUMEN_NO_100 = [v("30ml", "4.500"), v("50ml", "6.500")]


# --------------------------------------------------------------------------- env and flags
@pytest.fixture(autouse=True)
def _env(monkeypatch):
    for name in PROD_ON:
        monkeypatch.setenv(name, "true")
    for name in PROD_OFF + UNIT_UNSET:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "syn" + "thetic-" + "pc1")
    yield


def setflags(mp, pnl=None, vg=None, prio=None, lmg=None, fix=None, axes=None):
    for name, val in ((PNL, pnl), (VG, vg), (PRIO, prio), (LMG, lmg), (FIX, fix), (AXES, axes)):
        if val is None:
            mp.delenv(name, raising=False)
        else:
            mp.setenv(name, val)


PRIOCELLS = [pytest.param(None, id="prio0"), pytest.param("true", id="prio1")]
FIXCELLS = [pytest.param(None, id="fix0"), pytest.param("true", id="fix1")]
CAPCELLS = [pytest.param(False, id="cap0"), pytest.param(True, id="cap1")]


# --------------------------------------------------------------------------- the price task
_SELECTORS = (
    "get_shopify_sources_for_category", "get_algolia_sources_for_category",
    "get_sitemap_sources_for_category", "get_jsonapi_sources_for_category",
    "get_woo_sources_for_category", "get_salla_sources_for_category",
    "get_occ_sources_for_category", "get_magento_gql_sources_for_category",
    "get_unbxd_sources_for_category", "get_restjson_sources_for_category",
    "get_noon_sources_for_category", "get_gcc_shopify_pagescrape_sources_for_category",
)


class Calls:
    def __init__(self):
        self.shop, self.woo, self.search_web = [], [], []


def install_cascade(mp, svc, *, tier1=None, catalog=None, gulf=None):
    """Drive the REAL _get_price with zero network (the _stub_cascade set of
    tests/test_negcache_outage_and_converted_fallback.py, plus the case's three sources):
    `tier1` = the Tier-1 pick per typed name (None = every shopping row refused, as logged);
    `catalog` = the house shop's /products.json (None = no Shopify source); `gulf` = the
    converted adapter yield per typed name (None = no adapter yields, as logged)."""
    calls = Calls()
    mp.setattr(scs, "get_cached", lambda *a, **k: None)
    mp.setattr(scs, "set_cached", lambda *a, **k: None)
    mp.setattr(scs, "get_negative_cache", lambda *a, **k: None)
    mp.setattr(scs, "set_negative_cache", lambda *a, **k: None)
    mp.setattr(scs, "validate_price_query", lambda *a, **k: True)

    async def _no_db_price(*a, **k):
        return None
    mp.setattr("app.services.product_data_service.get_cached_price", _no_db_price, raising=False)
    mp.setattr(svc, "_save_price_to_db", lambda *a, **k: None, raising=False)
    mp.setattr(scs, "_should_escalate_price_scrape", lambda *a, **k: True)
    for name in _SELECTORS:
        mp.setattr(scs, name, lambda c: [])
    mp.setattr(scs, "sitemap_discovery_is_cold", lambda c: False)
    mp.setattr(scs, "sitemap_unbuilt_domains", lambda c: [])
    mp.setattr(scs, "ENABLE_PAGE_SCRAPE", True)
    mp.setattr(scs, "get_official_domain", lambda *a, **k: None)  # the shop was a reseller (LOG)

    async def _shopping(*a, **k):
        return {"shopping": [], "organic": [], "shopping_region": "us_fallback"}
    mp.setattr(scs, "search_product_prices", _shopping)
    picks = dict(tier1 or {})
    mp.setattr(scs, "extract_price_from_shopping",
               lambda full_name, *a, **k: copy.deepcopy(picks.get(full_name)))

    async def _no_organic(*a, **k):
        return {"organic": [], "knowledge_graph": None}
    mp.setattr(scs, "search_price_organic", _no_organic, raising=False)

    async def _no_extract(*a, **k):
        return None, {}
    mp.setattr(scs, "extract_price", _no_extract)
    mp.setattr(scs, "extract_price_from_training_data", _no_extract)

    async def _discovery_never_returns(*a, **k):
        calls.search_web.append(a)
        await asyncio.sleep(3600)
    mp.setattr(scs, "search_web", _discovery_never_returns)
    if catalog is not None:
        mp.setattr(scs, "get_shopify_sources_for_category", lambda c: [SimpleNamespace(domain=HOUSE_HOST)])

        async def _shop(domain, product_name, currency="BHD", resolved_category=None):
            calls.shop.append(product_name)
            return ps._match_shopify_product(copy.deepcopy(catalog), product_name, currency, domain,
                                             resolved_category)
        mp.setattr(scs, "fetch_shopify_price", _shop)
    if gulf is not None:
        rows = dict(gulf)
        mp.setattr(scs, "get_woo_sources_for_category",
                   lambda c: [SimpleNamespace(domain="store-kw.example.com")])

        async def _woo(domain, product_name, currency="BHD", resolved_category=None):
            calls.woo.append(product_name)
            return copy.deepcopy(rows.get(product_name))
        mp.setattr(scs, "fetch_woocommerce_store_api_price", _woo)
    return calls


def run_price(svc, typed):
    """(price, timed_out, full_name): the price task for one typed half, cut by the cap."""
    full = scs._shopping_cache_key("", typed, None)

    async def _go():
        try:
            got = await asyncio.wait_for(
                svc._get_price("", typed, None, "bahrain", typed, nocache=True, category=FRAG),
                timeout=CAP_S)
            return got, False
        except asyncio.TimeoutError:
            # The Phase-1 handler (SCS :6644-6654): the cap fired -> the race-miss fallback.
            return svc._price_fallback_on_miss("price", full, FRAG), True
    got, timed_out = asyncio.run(_go())
    return got, timed_out, full


def msgs(caplog):
    return [r.getMessage() for r in caplog.records]


def reseller_line(caplog, typed, amount_text):
    want = "Shopify reseller hit for %s parked as fallback: %s BHD via %s" % (typed, amount_text, HOUSE_HOST)
    return any(want in m for m in msgs(caplog))


def assert_house_hit(price, amount, url):
    assert isinstance(price, dict), price
    assert price.get("amount") == amount, price
    assert price.get("source_method") == "shopify_json", price
    assert price.get("retailer") == HOUSE_HOST and price.get("url") == url, price
    assert price.get("currency") == "BHD", price


# --------------------------------------------------------------------------- the pair build
def scoring():
    return {"winner_index": 0,
            "scores": {"product_0": {"overall": 60.0}, "product_1": {"overall": 50.0}},
            "tradeoff_pairs": [], "value_badges": [], "comparison_quality": "normal",
            "personalization": {"applied_shifts": []}, "price_tiers": {},
            "comparison_pair": ["product_a", "product_b"], "verdict_text": "Test.",
            "key_differences": []}


def prod(typed, price):
    """The product dict the orchestrator hands the reconcile with the resolver OFF (INC-P2 pure
    file `prod`): brand '', name = full_name = the typed half."""
    d = {"brand": "", "name": typed, "full_name": typed, "variant": None, "category": FRAG,
         "price": copy.deepcopy(price),
         "best_price": price.get("amount") if isinstance(price, dict) else None,
         "retailer": price.get("retailer") if isinstance(price, dict) else None,
         "specs": {}, "reviews": None, "rating": 4.2, "rating_source": None,
         "review_count": 5, "fact_check": {}}
    return d


def build_pair(a_typed, a_price, b_typed, b_price, cap=False, cands=None):
    """reconcile_pair_fairness then build_comparison_response in one copied context (the SCS
    order at :4788 and the builder), the capability token bound for cap=True."""
    q = "%s vs %s" % (a_typed, b_typed)
    pd = [prod(a_typed, a_price), prod(b_typed, b_price)]

    def _go():
        if cap:
            ps.price_size_cap_bind(True)
        ps.reconcile_pair_fairness(pd, q, FRAG, candidates_by_name=cands or {})
        return rb.build_comparison_response(
            query=q, product_data=pd, scoring_result=scoring(), comparison=None,
            region="bahrain", api_calls=0, elapsed_seconds=0.0, total_cost=0.0, gpt_calls=0,
            serper_calls=0, from_cache=False, verdict_validation={}, category_used=FRAG)
    return contextvars.copy_context().run(_go)


def ov(body):
    return [p.get("price") for p in body["overview"]["products"]]


def legacy(body):
    return [p.get("price") for p in body["products"]]


def shown(price):
    return (isinstance(price, dict) and price.get("unavailable") is not True
            and isinstance(price.get("amount"), (int, float)))


def pending(price, reason=None):
    ok = isinstance(price, dict) and price.get("unavailable") is True and price.get("amount") is None
    return ok and (reason is None or price.get("reason") == reason)


_KV = re.compile(r"(\w+)=(\S*)")


def outcome(caplog):
    """{slot: {field: value}} of the PRICE_OUTCOME lines (response_builder._p2_price_outcome)."""
    out = {}
    for m in msgs(caplog):
        if m.startswith("PRICE_OUTCOME "):
            fields = dict(_KV.findall(m))
            out[int(fields["slot"])] = fields
    return out


def amounts_in(obj, acc):
    """Every number under a price field (offsize_listing included), for the never-shown rows."""
    if isinstance(obj, dict):
        for k, val in obj.items():
            if k in ("amount", "best_price") and isinstance(val, (int, float)):
                acc.append(float(val))
            amounts_in(val, acc)
    elif isinstance(obj, list):
        for val in obj:
            amounts_in(val, acc)
    return acc


def house_hit(typed, available=True):
    """What the REAL matcher returns for one typed half from the page-read catalog (the dict the
    race-miss fallback returns: _p2_park_reseller parks it unchanged, method shopify_json)."""
    return ps._match_shopify_product(house_catalog(available), typed, "BHD", HOUSE_HOST, FRAG)


# =========================================================================== R01-R07 the price task
@pytest.mark.parametrize("prio", PRIOCELLS)
def test_r01_maheeb_flag_on_house_hit_replaces_the_5941_park(monkeypatch, caplog, prio):
    """R01 PIN (PLAN 3.4 pin 1 and 2; SCS :8609 -> _p2_park_reseller :9805-9827, :7437-7444):
    switch ON, the logged Maheeb run cut by the cap returns the house hit 29.900 BHD from the
    product page, never the parked 59.41 row. Both values of ENABLE_GENUINE_PRICE_PRIORITY."""
    setflags(monkeypatch, pnl="true", prio=prio)
    caplog.set_level(logging.INFO)
    svc = scs.StructuredComparisonService()
    install_cascade(monkeypatch, svc, tier1={MAHEEB: maheeb_tier1_park()}, catalog=house_catalog())
    got, timed_out, _ = run_price(svc, MAHEEB)
    assert timed_out is True
    assert reseller_line(caplog, MAHEEB, "29.900"), [m for m in msgs(caplog) if "Shopify" in m]
    assert_house_hit(got, 29.9, MAHEEB_URL)


@pytest.mark.parametrize("prio", PRIOCELLS)
def test_r02_maheeb_flag_off_returns_the_logged_park(monkeypatch, caplog, prio):
    """R02 PIN (flag-OFF identity, the 18 Nov run): switch OFF the same run logs the reseller
    line and returns the parked converted 59.41 row on the cap miss (the logged race-miss
    line); the house hit stays in the local variable."""
    setflags(monkeypatch, pnl=None, prio=prio)
    caplog.set_level(logging.INFO)
    svc = scs.StructuredComparisonService()
    install_cascade(monkeypatch, svc, tier1={MAHEEB: maheeb_tier1_park()}, catalog=house_catalog())
    got, timed_out, full = run_price(svc, MAHEEB)
    assert timed_out is True
    assert reseller_line(caplog, MAHEEB, "29.900")
    assert isinstance(got, dict) and got.get("amount") == 59.41, got
    assert got.get("source_method") == "converted_usd", got
    assert any("race miss for %s" % MAHEEB in m and "returning parked converted_usd price (never None)" in m
               for m in msgs(caplog)), [m for m in msgs(caplog) if "race miss" in m]
    assert svc._parked_price[full].get("amount") == 59.41


@pytest.mark.parametrize("prio", PRIOCELLS)
@pytest.mark.parametrize("pnl", [pytest.param(None, id="pnl0"), pytest.param("true", id="pnl1")])
def test_r03_mubeen_as_logged(monkeypatch, caplog, pnl, prio):
    """R03 PIN (the logged Mubeen run: every shopping row refused, no adapter yield): switch ON
    the cap miss returns the house hit 10.000 BHD; switch OFF it returns None (display_rule
    none), as logged."""
    setflags(monkeypatch, pnl=pnl, prio=prio)
    caplog.set_level(logging.INFO)
    svc = scs.StructuredComparisonService()
    install_cascade(monkeypatch, svc, tier1={}, catalog=house_catalog())
    got, timed_out, _ = run_price(svc, MUBEEN)
    assert timed_out is True
    assert reseller_line(caplog, MUBEEN, "10.000")
    if pnl:
        assert_house_hit(got, 10.0, MUBEEN_URL)
    else:
        assert got is None, got


def _pnl3_run(monkeypatch, caplog, prio):
    setflags(monkeypatch, pnl="true", prio=prio)
    caplog.set_level(logging.INFO)
    svc = scs.StructuredComparisonService()
    calls = install_cascade(monkeypatch, svc, tier1={}, catalog=house_catalog(),
                            gulf={MUBEEN: gulf_converted_row()})
    got, timed_out, full = run_price(svc, MUBEEN)
    assert timed_out is True
    assert reseller_line(caplog, MUBEEN, "10.000")
    # The adapter consume ran before the cap: the converted row was seeded as a candidate.
    assert calls.woo == [full], calls.woo
    seeded = [(c.get("raw_data") or {}).get("source_method") for c in svc._price_candidates.get(full, [])]
    assert "converted_usd" in seeded and "shopify_json" in seeded, seeded
    return svc, got, full


def test_r04_pnl3_converted_yield_never_replaces_the_genuine_park(monkeypatch, caplog):
    """R04 RED (PLAN 3.4 pin 6, PNL-3; SCS :8218-8231 at d2f49d8b): switch ON, a genuine Shopify
    park (10.000) and then a converted-only adapter yield: the cap miss returns the GENUINE
    park and the pair shows 10.000 BHD from the house page, never the converted row. Main
    overwrites the park (the local converted_fallback is None for Mubeen) and returns 11.250."""
    svc, got, full = _pnl3_run(monkeypatch, caplog, None)
    assert_house_hit(got, 10.0, MUBEEN_URL)
    assert svc._parked_price[full].get("source_method") == "shopify_json"
    for cap in (False, True):
        body = build_pair(MAHEEB, house_hit(MAHEEB), MUBEEN, got, cap=cap, cands=svc._price_candidates)
        w = ov(body)[1]
        assert shown(w) and w["amount"] == 10.0 and w.get("source_method") == "shopify_json", w
        assert 11.25 not in amounts_in(ov(body), []) + amounts_in(legacy(body), [])


def test_r04b_pnl3_priority_on_recovers_the_genuine_row(monkeypatch, caplog):
    """R04b PIN (the same order with ENABLE_GENUINE_PRICE_PRIORITY on, SCS :7394-7436): the race-
    miss recovery picks the seeded genuine Shopify row before the park, on main and after."""
    _svc, got, _full = _pnl3_run(monkeypatch, caplog, "true")
    assert_house_hit(got, 10.0, MUBEEN_URL)


@pytest.mark.parametrize("seeded_park", [pytest.param(False, id="as_live"), pytest.param(True, id="genuine_preset")])
def test_r05_pnl3_flag_off_identity(monkeypatch, caplog, seeded_park):
    """R05 PIN (flag-OFF identity, B1 recorder): switch OFF the converted-only yield is parked
    (the R5 terminal, SCS :8218-8231) and returned on the cap miss, also when a genuine park
    was PRESET on the request (no Shopify source then): the PC1 check is read only with the
    switch ON (an ungated GREEN keeps the preset park and fails this row)."""
    setflags(monkeypatch, pnl=None, prio=None)
    caplog.set_level(logging.INFO)
    svc = scs.StructuredComparisonService()
    install_cascade(monkeypatch, svc, tier1={}, catalog=None if seeded_park else house_catalog(),
                    gulf={MUBEEN: gulf_converted_row()})
    full = scs._shopping_cache_key("", MUBEEN, None)
    if seeded_park:
        svc._parked_price[full] = dict(house_hit(MUBEEN))
    got, timed_out, _ = run_price(svc, MUBEEN)
    assert timed_out is True
    assert isinstance(got, dict) and got.get("source_method") == "converted_usd", got
    assert got.get("amount") == 11.25 and got.get("retailer") == "store-kw.example.com", got


def test_r06_maheeb_converted_yield_after_the_tier1_park(monkeypatch, caplog):
    """R06 PIN (PNL-3's other half: Maheeb's local converted_fallback is set by the Tier-1 park,
    so the adapter yield never writes the park): switch ON the cap miss returns the house
    hit on main and after."""
    setflags(monkeypatch, pnl="true", prio=None)
    caplog.set_level(logging.INFO)
    svc = scs.StructuredComparisonService()
    calls = install_cascade(monkeypatch, svc, tier1={MAHEEB: maheeb_tier1_park()}, catalog=house_catalog(),
                            gulf={MAHEEB: dict(gulf_converted_row(), title="Maheeb Edp 200ML",
                                               url="https://store-kw.example.com/product/maheeb-edp-200ml")})
    got, timed_out, full = run_price(svc, MAHEEB)
    assert timed_out is True and calls.woo == [full]
    assert_house_hit(got, 29.9, MAHEEB_URL)


def test_r07_empty_park_converted_yield_is_still_parked(monkeypatch, caplog):
    """R07 PIN (the GREEN boundary): switch ON with NO genuine park (no Shopify source), the
    converted-only yield is still parked and returned on the cap miss (PC1 keeps a genuine
    park only; the R5 terminal stays)."""
    setflags(monkeypatch, pnl="true", prio=None)
    caplog.set_level(logging.INFO)
    svc = scs.StructuredComparisonService()
    install_cascade(monkeypatch, svc, tier1={}, catalog=None, gulf={MUBEEN: gulf_converted_row()})
    got, timed_out, _ = run_price(svc, MUBEEN)
    assert timed_out is True
    assert isinstance(got, dict) and got.get("source_method") == "converted_usd" and got.get("amount") == 11.25, got


def test_r07b_listing_url_park_is_still_replaced(monkeypatch, caplog):
    """R07b PIN (added at GREEN for the mutation table, rows added only; the G1 boundary of the
    listing-url clause): switch ON, a genuine-method park on a LISTING url preset on the request
    (no Shopify source): the converted-only yield still replaces it, as on main (PC1 keeps only a
    genuine park on a product page, the complement of _p2_park_reseller's replaceable test), so
    the cap miss returns the converted row."""
    setflags(monkeypatch, pnl="true", prio=None)
    caplog.set_level(logging.INFO)
    svc = scs.StructuredComparisonService()
    install_cascade(monkeypatch, svc, tier1={}, catalog=None, gulf={MUBEEN: gulf_converted_row()})
    full = scs._shopping_cache_key("", MUBEEN, None)
    svc._parked_price[full] = dict(house_hit(MUBEEN), retailer="store-g.example.com",
                                   url="https://store-g.example.com/search?q=mubeen+edp")
    got, timed_out, _ = run_price(svc, MUBEEN)
    assert timed_out is True
    assert isinstance(got, dict) and got.get("source_method") == "converted_usd", got
    assert got.get("amount") == 11.25 and got.get("retailer") == "store-kw.example.com", got


# =========================================================================== R08-R12 the display
@pytest.mark.parametrize("fix", FIXCELLS)
@pytest.mark.parametrize("cap", CAPCELLS)
def test_r08_pair_each_side_keeps_its_typed_size(monkeypatch, caplog, cap, fix):
    """R08 PIN (PLAN 3.4 pin 3; reconcile_pair_sizes_v2 PS :17769-17900, p2_wire_price
    :17947-17986): switch ON, Maheeb 29.900 at 200 ml and Mubeen 10.000 at 100 ml are BOTH
    shown with their own sizes in both capability cells (ORCH-P2-B rule 1), no offsize_listing;
    PRICE_OUTCOME names the house host for both slots."""
    setflags(monkeypatch, pnl="true", fix=fix)
    caplog.set_level(logging.INFO)
    a, b = house_hit(MAHEEB), house_hit(MUBEEN)
    assert a and b, (a, b)
    body = build_pair(MAHEEB, a, MUBEEN, b, cap=cap, cands={MAHEEB: [], MUBEEN: []})
    w = ov(body)
    assert shown(w[0]) and w[0]["amount"] == 29.9 and w[0].get("size_ml") == 200, w[0]
    assert w[0].get("per_ml") == round(29.9 / 200, 4), w[0]
    assert shown(w[1]) and w[1]["amount"] == 10.0 and w[1].get("size_ml") == 100, w[1]
    assert "offsize_listing" not in w[0] and "offsize_listing" not in w[1]
    assert [p.get("amount") for p in legacy(body)] == [29.9, 10.0]
    o = outcome(caplog)
    assert o[0]["shown"] == "yes" and o[0]["amount"] == "29.900" and o[0]["method"] == "shopify_json", o[0]
    assert o[0]["retailer"] == HOUSE_HOST and o[0]["marketplace"] == "0" and o[0]["size_ml"] == "200", o[0]
    assert o[1]["shown"] == "yes" and o[1]["amount"] == "10.000" and o[1]["size_ml"] == "100", o[1]


@pytest.mark.parametrize("pnl", [pytest.param(None, id="pnl0"), pytest.param("true", id="pnl1")])
def test_r09_replay_end_to_end(monkeypatch, caplog, pnl):
    """R09 PIN (PLAN 3.4 'replay with ENABLE_PRICE_NOT_LOST on and the cap firing'): both price
    tasks cut by the cap on ONE request, then the pair build. Switch ON: 29.900 and 10.000
    BHD shown from the house pages. Switch OFF: the two logged PRICE_OUTCOME lines (slot 0
    shown=no size_ml=200 pending_genuine non_pdp_url; slot 1 shown=no size_ml=none
    pending_genuine none)."""
    setflags(monkeypatch, pnl=pnl, prio=None)
    caplog.set_level(logging.INFO)
    svc = scs.StructuredComparisonService()
    install_cascade(monkeypatch, svc, tier1={MAHEEB: maheeb_tier1_park()}, catalog=house_catalog())
    p0, t0, _ = run_price(svc, MAHEEB)
    p1, t1, _ = run_price(svc, MUBEEN)
    assert t0 is True and t1 is True
    caplog.clear()
    body = build_pair(MAHEEB, p0, MUBEEN, p1, cap=False, cands=svc._price_candidates)
    w = ov(body)
    o = outcome(caplog)
    assert o[0]["product"] == "Maheeb_Edp_200ML" and o[1]["product"] == "Mubeen_Edp_100ml", o
    if pnl:
        assert shown(w[0]) and w[0]["amount"] == 29.9 and w[0].get("size_ml") == 200, w[0]
        assert shown(w[1]) and w[1]["amount"] == 10.0 and w[1].get("size_ml") == 100, w[1]
        assert o[0]["host"] == HOUSE_HOST and o[1]["host"] == HOUSE_HOST, o
    else:
        assert pending(w[0], "pending_genuine") and pending(w[1], "pending_genuine"), w
        assert (o[0]["shown"], o[0]["size_ml"], o[0]["pend_reason"], o[0]["display_rule"]) == (
            "no", "200", "pending_genuine", "non_pdp_url"), o[0]
        assert (o[1]["shown"], o[1]["size_ml"], o[1]["pend_reason"], o[1]["display_rule"]) == (
            "no", "none", "pending_genuine", "none"), o[1]
    assert 59.41 not in amounts_in(ov(body), []) + amounts_in(legacy(body), [])


@pytest.mark.parametrize("cap", CAPCELLS)
@pytest.mark.parametrize("pnl", [pytest.param(None, id="pnl0"), pytest.param("true", id="pnl1")])
def test_r10_the_5941_row_is_never_shown(monkeypatch, caplog, pnl, cap):
    """R10 PIN (PLAN 3.4 pin 4; the chokepoint PS :1963-1966, the wire's restore check
    :17966-17972): the parked 59.41 row (a search link) as Maheeb's price is never shown, with
    the switch OFF or ON, with or without the capability token; no price field of the body
    carries 59.41 (no offsize_listing either)."""
    setflags(monkeypatch, pnl=pnl)
    caplog.set_level(logging.INFO)
    mub = house_hit(MUBEEN) if pnl else None
    body = build_pair(MAHEEB, maheeb_tier1_park(), MUBEEN, mub, cap=cap)
    w = ov(body)
    assert not shown(w[0]), w[0]
    assert 59.41 not in amounts_in(ov(body), []) + amounts_in(legacy(body), [])
    assert outcome(caplog)[0]["shown"] == "no"


@pytest.mark.parametrize("cap", CAPCELLS)
def test_r11_house_hit_out_of_stock_is_never_shown(monkeypatch, caplog, cap):
    """R11 PIN (the stock flag was not read on 18 Nov, PNL-1/2/3; PS :15791, :1952-1954): switch
    ON, a house hit whose variant is not available is never shown as a price."""
    setflags(monkeypatch, pnl="true")
    caplog.set_level(logging.INFO)
    out = house_hit(MUBEEN, available=False)
    assert out is not None and out.get("in_stock") is False, out
    body = build_pair(MAHEEB, house_hit(MAHEEB), MUBEEN, out, cap=cap)
    assert not shown(ov(body)[1]), ov(body)[1]
    assert shown(ov(body)[0]) and ov(body)[0]["amount"] == 29.9


@pytest.mark.parametrize("pnl", [pytest.param(None, id="pnl0"), pytest.param("true", id="pnl1")])
def test_r12_park_reseller_over_the_logged_park(monkeypatch, pnl):
    """R12 PIN (SCS :9805-9827 with the logged values): switch ON the house hit replaces the
    parked 59.41 converted search-link row and is what the race miss returns; switch OFF the
    park is unchanged and nothing is seeded."""
    setflags(monkeypatch, pnl=pnl)
    svc = scs.StructuredComparisonService()
    svc._parked_price[MAHEEB] = maheeb_tier1_park()
    hit = house_hit(MAHEEB)
    svc._p2_park_reseller(MAHEEB, dict(hit), [dict(hit)], "BHD")
    got = svc._price_fallback_on_miss("price", MAHEEB, FRAG)
    if pnl:
        assert_house_hit(svc._parked_price[MAHEEB], 29.9, MAHEEB_URL)
        assert_house_hit(got, 29.9, MAHEEB_URL)
    else:
        assert svc._parked_price[MAHEEB] == maheeb_tier1_park()
        assert svc._price_candidates.get(MAHEEB, []) == []
        assert got.get("amount") == 59.41


# =========================================================================== R13-R14 side effects
YSL_Y = "Yves Saint Laurent Y Eau de Parfum"   # the logged typed name (44.150 BHD, a marketplace)


def ysl_row(seller, link, price="BHD 44.150"):
    return {"title": "Yves Saint Laurent Y Eau de Parfum 100ml", "price": price, "source": seller,
            "link": link}


def test_r13_ysl_y_marketplace_seller_is_or_is_not_skipped(monkeypatch):
    """R13 PIN (PLAN 3.4 pin 5; PS :17445-17481, :10601-10605): the 18 Nov seller of the YSL Y
    price is not in the records, so both answers are pinned. Under the switch an auction /
    peer seller is skipped (never the Tier-1 pick, never a converted park); a marketplace
    that is not on the list (noon, Amazon) keeps its price. Switch OFF nothing is skipped."""
    fn = ps.is_auction_marketplace_seller
    for r, u in (("noon", "https://www.noon.com/bahrain-en/p/x"), ("Amazon.ae", "https://www.amazon.ae/dp/x"),
                 ("store-m.example.com", "https://store-m.example.com/p/y")):
        assert fn(r, u) is False, (r, u)
    for r, u in (("Whatnot", "https://www.whatnot.com/listing/x"), ("eBay - seller", None)):
        assert fn(r, u) is True, (r, u)
    rows = [{"retailer": "noon", "url": "https://www.noon.com/bahrain-en/p/x", "amount": 44.15},
            {"retailer": "Whatnot", "url": "https://www.whatnot.com/listing/x", "amount": 40.0}]
    setflags(monkeypatch, pnl="true")
    assert [r["amount"] for r in ps.p2_filter_marketplace_rows(rows)] == [44.15]
    auction_only = [ysl_row("Whatnot", "https://www.whatnot.com/listing/x")]
    assert ps.extract_price_from_shopping(YSL_Y, auction_only, "BHD", category=FRAG) is None
    setflags(monkeypatch, pnl=None)
    assert ps.p2_filter_marketplace_rows(rows) is rows
    pick = ps.extract_price_from_shopping(YSL_Y, auction_only, "BHD", category=FRAG)
    assert pick is not None and pick.get("retailer") == "Whatnot", pick


@pytest.mark.parametrize("lmg", [pytest.param(None, id="lmg0"), pytest.param("true", id="lmg1")])
@pytest.mark.parametrize("pnl", [pytest.param(None, id="pnl0"), pytest.param("true", id="pnl1")])
def test_r14_rasasi_hawas_row_only_with_the_listing_guard(monkeypatch, pnl, lmg):
    """R14 PIN (PLAN 3.4 pin 5b; PS :7859-7880, :18018-18020; the INC-P2 G1 / G2 shapes): a
    gender-free 'Rasasi Hawas' query refuses a 'for Her' listing ONLY with both the listing
    guard and the switch on; a 'for Him' listing passes in every cell."""
    setflags(monkeypatch, pnl=pnl, lmg=lmg, axes="true")
    sel = lambda t: ps._selection_match("Rasasi Hawas", t, FRAG, candidate_brand="Rasasi")  # noqa: E731
    assert sel("Rasasi Hawas for Him Eau de Parfum 100ml") is True
    assert sel("Rasasi Hawas for Her Eau de Parfum 100ml") is (not (pnl and lmg))


# =========================================================================== R15-R19 the size fix
def lumen_hit(typed, variants, title="Lumen Edp 100ml"):
    return ps._match_shopify_product(lumen_catalog(variants, title), typed, "BHD", LUMEN_HOST, FRAG)


def count_binder(monkeypatch):
    seen = []
    real = ps._select_shopify_variant

    def _spy(*a, **k):
        seen.append(a[1] if len(a) > 1 else k.get("product_name"))
        return real(*a, **k)
    monkeypatch.setattr(ps, "_select_shopify_variant", _spy)
    return seen


def test_r15_first_variant_not_the_typed_size_flag_on(monkeypatch):
    """R15 RED (PLAN 3.4 pin 7, the size fix; PS :15723-15734, :15762-15763): switch ON, VG off
    (as on web): a house product titled at the typed size whose FIRST variant is 30 ml is
    priced at its 100 ml variant (10.000) and labelled 100ml. Main prices variants[0]
    (4.500) under the 100ml label (the string sort of {'100', '30'})."""
    setflags(monkeypatch, pnl="true", vg=None)
    out = lumen_hit(LUMEN_TYPED, LUMEN_FIRST_30)
    assert out is not None and out["amount"] == 10.0 and out["size"] == "100ml", out


def test_r15b_typed_size_not_offered_gives_no_hit(monkeypatch):
    """R15b RED (the size fix, the binder's refusal branch): switch ON, VG off: a product titled
    at the typed size with no variant of that size gives no hit. Main returns variants[0]
    (4.500) labelled 100ml."""
    setflags(monkeypatch, pnl="true", vg=None)
    assert lumen_hit(LUMEN_TYPED, LUMEN_NO_100) is None


def test_r16_numeric_size_label(monkeypatch):
    """R16 RED (the size fix, 'sort sizes as numbers'; PS :15762-15763): switch ON, VG off, an
    UNTYPED query keeps variants[0] (4.500, no binding without a typed size) and its label is
    the smallest size by number (30ml). Main labels it 100ml (string sort)."""
    setflags(monkeypatch, pnl="true", vg=None)
    out = lumen_hit("Lumen Edp", LUMEN_FIRST_30)
    assert out is not None and out["amount"] == 4.5, out
    assert out["size"] == "30ml", out


LUMEN_OZ = [v("1 oz", "4.500"), v("3.4 oz", "10.000")]  # fl oz only: 1 oz is 30 ml, 3.4 oz is 100 ml


def test_r15c_typed_oz_size_binds_and_labels_the_typed_size(monkeypatch):
    """R15c RED (added at GREEN for the mutation table, rows added only; the size fix, J1 and the
    J2 label of a bound variant): switch ON, VG off: a query typed in fl oz ("3.4 oz", the 100 ml
    bottle) on a product sized in fl oz only binds the 3.4 oz variant (10.000, never the 1 oz
    4.500) and its label is the typed size, 100ml. Main prices variants[0] (4.500) with no size
    label (no ml token in the title or the variant title)."""
    setflags(monkeypatch, pnl="true", vg=None)
    out = lumen_hit("Lumen Edp 3.4 oz", LUMEN_OZ, title="Lumen Edp 3.4 oz")
    assert out is not None and out["amount"] == 10.0 and out["size"] == "100ml", out


@pytest.mark.parametrize("pnl", [pytest.param(None, id="pnl0"), pytest.param("true", id="pnl1")])
def test_r17_vg_on_path_unchanged(monkeypatch, pnl):
    """R17 PIN (the existing ENABLE_VARIANT_MIN_PRICE_GUARD path, PS :15726-15731,
    _select_shopify_variant :15489-15535; the shapes of tests/test_variant_min_price_guard.py):
    VG ON binds the typed size (10.000, 100ml), refuses a typed size not offered (None), and
    prefers the 100 ml flagship for an untyped fragrance (10.000), with the switch off or on."""
    setflags(monkeypatch, pnl=pnl, vg="true")
    out = lumen_hit(LUMEN_TYPED, LUMEN_FIRST_30)
    assert out is not None and out["amount"] == 10.0 and out["size"] == "100ml", out
    assert lumen_hit(LUMEN_TYPED, LUMEN_NO_100) is None
    out = lumen_hit("Lumen Edp", LUMEN_FIRST_30)
    assert out is not None and out["amount"] == 10.0 and out["size"] == "100ml", out


@pytest.mark.parametrize("pnl", [pytest.param(None, id="pnl0"), pytest.param("true", id="pnl1")])
def test_r17b_vg_on_keeps_its_own_label(monkeypatch, pnl):
    """R17b PIN (added at GREEN for the mutation table, rows added only): VG ON, the switch off or
    on: the size fix leaves VG's path whole, its label included. An fl-oz typed query binds the
    3.4 oz variant with VG's own label (None: no ml token in the title or the variant title), and
    an untyped query on a title that states 30 ml keeps VG's flagship 100 ml variant with VG's
    string-sorted label 100ml (a numeric sort would say 30ml)."""
    setflags(monkeypatch, pnl=pnl, vg="true")
    out = lumen_hit("Lumen Edp 3.4 oz", LUMEN_OZ, title="Lumen Edp 3.4 oz")
    assert out is not None and out["amount"] == 10.0 and out["size"] is None, out
    out = lumen_hit("Lumen Edp", [v("30ml", "4.500"), v("100ml", "10.000")], title="Lumen Edp 30ml")
    assert out is not None and out["amount"] == 10.0 and out["size"] == "100ml", out


def test_r18_size_fix_flag_off_identity(monkeypatch):
    """R18 PIN (flag-OFF identity, B1 recorder): switch OFF and VG off, the matcher is main's
    (variants[0], the string-sorted label) and the binder is never called."""
    setflags(monkeypatch, pnl=None, vg=None)
    seen = count_binder(monkeypatch)
    out = lumen_hit(LUMEN_TYPED, LUMEN_FIRST_30)
    assert out is not None and out["amount"] == 4.5 and out["size"] == "100ml", out
    out = lumen_hit("Lumen Edp", LUMEN_FIRST_30)
    assert out is not None and out["amount"] == 4.5 and out["size"] == "100ml", out
    out = house_hit(MAHEEB)
    assert out is not None and out["amount"] == 29.9 and out["size"] == "200ml", out
    assert seen == [], seen


@pytest.mark.parametrize("vg", [pytest.param(None, id="vg0"), pytest.param("true", id="vg1")])
@pytest.mark.parametrize("pnl", [pytest.param(None, id="pnl0"), pytest.param("true", id="pnl1")])
def test_r18b_single_variant_house_products_unchanged(monkeypatch, pnl, vg):
    """R18b PIN (the page-read shape: one variant, the size in the title): every switch cell
    prices Maheeb 29.900 (200ml) and Mubeen 10.000 (100ml) from the house pages."""
    setflags(monkeypatch, pnl=pnl, vg=vg)
    a, b = house_hit(MAHEEB), house_hit(MUBEEN)
    assert a is not None and a["amount"] == 29.9 and a["size"] == "200ml" and a["url"] == MAHEEB_URL, a
    assert b is not None and b["amount"] == 10.0 and b["size"] == "100ml" and b["url"] == MUBEEN_URL, b


@pytest.mark.parametrize("cap", CAPCELLS)
@pytest.mark.parametrize("shape", [pytest.param("first_30", id="first_30"), pytest.param("no_100", id="no_100")])
def test_r19_never_shown_at_the_typed_size_with_another_variants_price(monkeypatch, caplog, shape, cap):
    """R19 RED (PLAN 3.4 pin 7 at the display): switch ON, VG off, the pair 'Lumen Edp 100ml vs
    Mubeen Edp 100ml': the Lumen side is never shown at 100 ml with the 30 ml variant's 4.500;
    it shows its 100 ml price (first_30) or stays pending (no_100). Main shows 4.500 at
    100 ml in both shapes and both capability cells."""
    setflags(monkeypatch, pnl="true", vg=None)
    caplog.set_level(logging.INFO)
    variants = LUMEN_FIRST_30 if shape == "first_30" else LUMEN_NO_100
    lum = lumen_hit(LUMEN_TYPED, variants)
    body = build_pair(LUMEN_TYPED, lum, MUBEEN, house_hit(MUBEEN), cap=cap)
    w = ov(body)[0]
    assert not (shown(w) and w["amount"] == 4.5), w
    if shape == "first_30":
        assert shown(w) and w["amount"] == 10.0 and w.get("size_ml") == 100, w
    else:
        assert not shown(w), w
    assert shown(ov(body)[1]) and ov(body)[1]["amount"] == 10.0


# =========================================================================== PC1b the unit-less variant guard
# PC1b UNITLESS-VARIANT GUARD (S98-FIX; spec PC1b_SPEC.md section 3; it closes PC1's stated limit
# L10). Rows APPENDED only: no line above this block changed. RED rows (W1 x6, W2 x8, W3 x2) FAIL
# at base 7e2e317c (PC1 merged) on an AssertionError; PIN rows (M5a x2, M5b x2, P1) pass at base
# and must keep passing.
# The defect (F1 / L10): a Shopify variant title with no ml / oz token (a bare "30", "Small",
# "Travel Size", "30 cc", "30 millilitres", the Arabic unit word) makes the binder
# (_select_shopify_variant) read every variant's size from the PRODUCT title, so PC1's J1 binds
# variants[0] and another bottle's price is shown at the typed size, as on main.
# The GREEN rule (spec section 2.2): in J1 only, right after the binder, a bound variant whose OWN
# title states no size, on a product whose variants carry more than one distinct price, gives no
# hit from that product: a lost price, never another bottle's price.
# Source rows: W1-W3 of PC1's wrong-price adversary, adapted to this file's helpers; W3 is rebuilt
# WITHOUT that row's reseller-line precondition (a row artefact: under the guard there is no
# reseller hit to log). Synthetic hosts and products only; nothing reaches a shop or the network.
PC1B_AR_ML = chr(0x0645) + chr(0x0644)  # the Arabic unit word for ml, built at run time (ASCII file)

# Two-price products titled at the typed size whose variant titles state NO ml / oz size: the
# 30-unit bottle (4.500) first, the 100-unit bottle (10.000) second.
PC1B_UNITLESS = {
    "bare_numbers": (("30", "4.500"), ("100", "10.000")),
    "small_large": (("Small", "4.500"), ("Large", "10.000")),
    "travel_full": (("Travel Size", "4.500"), ("Full Size", "10.000")),
    "arabic_unit": (("30 " + PC1B_AR_ML, "4.500"), ("100 " + PC1B_AR_ML, "10.000")),
    "cc": (("30 cc", "4.500"), ("100 cc", "10.000")),
    "millilitres": (("30 millilitres", "4.500"), ("100 millilitres", "10.000")),
}
PC1B_SHAPES = list(PC1B_UNITLESS)
PC1B_LMGCELLS = [pytest.param(None, id="lmg0"), pytest.param("true", id="lmg1")]


def pc1b_variants(shape):
    """Fresh variant dicts of one unit-less shape (the file's `v` shape)."""
    return [v(size, price) for size, price in PC1B_UNITLESS[shape]]


@pytest.mark.parametrize("shape", PC1B_SHAPES)
def test_pc1b_w1_unitless_variant_titles_give_no_hit(monkeypatch, shape):
    """PC1b W1 RED, FAIL at base 7e2e317c (spec section 3, the matcher): switch ON, VG off, the
    exact gate on: the product 'Lumen Edp 100ml' (typed 'Lumen Edp 100ml') whose two variant
    titles state no ml / oz size (the cell's shape, 4.500 and 10.000) gives NO hit from that
    product: _match_shopify_product returns None (the specified no-hit, not merely 'not 4.500').
    Base: the binder reads both variants as 100 ml from the product title, J1 binds variants[0]
    and the matcher returns 4.500 labelled 100ml."""
    setflags(monkeypatch, pnl="true", vg=None)
    out = lumen_hit(LUMEN_TYPED, pc1b_variants(shape))
    assert out is None, out


@pytest.mark.parametrize("cap", CAPCELLS)
@pytest.mark.parametrize("shape", ["bare_numbers", "arabic_unit"])
@pytest.mark.parametrize("lmg", PC1B_LMGCELLS)
def test_pc1b_w2_unitless_pair_never_shows_the_30_unit_price(monkeypatch, caplog, lmg, shape, cap):
    """PC1b W2 RED, FAIL at base 7e2e317c (spec section 3, the wire; R19's pair with unit-less
    variant titles): switch ON, VG off, ENABLE_LISTING_MATCH_GUARD unset or on (it is ON on web):
    in the pair 'Lumen Edp 100ml vs Mubeen Edp 100ml' the Lumen side is never SHOWN at the
    30-unit bottle's 4.500, in both capability cells. Base: the matcher's 4.500 labelled 100ml
    is shown."""
    setflags(monkeypatch, pnl="true", vg=None, lmg=lmg)
    caplog.set_level(logging.INFO)
    lum = lumen_hit(LUMEN_TYPED, pc1b_variants(shape))
    body = build_pair(LUMEN_TYPED, lum, MUBEEN, house_hit(MUBEEN), cap=cap)
    w = ov(body)[0]
    assert not (shown(w) and w.get("amount") == 4.5), w


@pytest.mark.parametrize("prio", PRIOCELLS)
def test_pc1b_w3_race_miss_never_returns_the_30_unit_price(monkeypatch, caplog, prio):
    """PC1b W3 RED, FAIL at base 7e2e317c (spec section 3, the race miss; the adversary's row
    rebuilt WITHOUT its reseller-line precondition): switch ON, VG off, both values of
    ENABLE_GENUINE_PRICE_PRIORITY: the PNL-3 order on the bare_numbers product of the synthetic
    house host (the Shopify block, then a converted-only 100 ml adapter yield of 11.250), the cap
    fires: the race-miss price is never the 30-unit bottle's 4.500 from shopify_json. Base: J1
    binds variants[0] (4.500), PC1 keeps that genuine park against the converted yield, and the
    race miss returns it (prio1: the seeded genuine row)."""
    setflags(monkeypatch, pnl="true", vg=None, prio=prio)
    caplog.set_level(logging.INFO)
    svc = scs.StructuredComparisonService()
    gulf = dict(gulf_converted_row(), title=LUMEN_TYPED,
                url="https://store-kw.example.com/product/lumen-edp-100ml")
    install_cascade(monkeypatch, svc, tier1={}, catalog=lumen_catalog(pc1b_variants("bare_numbers")),
                    gulf={LUMEN_TYPED: gulf})
    monkeypatch.setattr(scs, "get_shopify_sources_for_category", lambda c: [SimpleNamespace(domain=LUMEN_HOST)])
    got, timed_out, _ = run_price(svc, LUMEN_TYPED)
    assert timed_out is True
    assert not (isinstance(got, dict) and got.get("amount") == 4.5
                and got.get("source_method") == "shopify_json"), got


@pytest.mark.parametrize("pnl_value", [pytest.param("false", id="pnl_false"),
                                       pytest.param(" Off ", id="pnl_padded_off")])
def test_pc1b_m5a_switch_false_or_padded_off_keeps_the_park_write(monkeypatch, caplog, pnl_value):
    """PC1b M5a PIN, passes at base 7e2e317c (spec section 3, PC1 coverage): R05's genuine_preset
    cell with ENABLE_PRICE_NOT_LOST set explicitly to 'false' and to ' Off ' (the house reader
    strips and lowers) gives exactly R05's switch-unset outcome: the preset genuine park is still
    overwritten by the converted-only yield, and the cap miss returns the converted 11.250 row.
    Kills a raw-env-truthiness read of the switch."""
    setflags(monkeypatch, pnl=pnl_value, prio=None)
    caplog.set_level(logging.INFO)
    svc = scs.StructuredComparisonService()
    install_cascade(monkeypatch, svc, tier1={}, catalog=None, gulf={MUBEEN: gulf_converted_row()})
    full = scs._shopping_cache_key("", MUBEEN, None)
    svc._parked_price[full] = dict(house_hit(MUBEEN))
    got, timed_out, _ = run_price(svc, MUBEEN)
    assert timed_out is True
    assert isinstance(got, dict) and got.get("source_method") == "converted_usd", got
    assert got.get("amount") == 11.25 and got.get("retailer") == "store-kw.example.com", got
    assert svc._parked_price[full].get("source_method") == "converted_usd", svc._parked_price[full]


@pytest.mark.parametrize("typed", [pytest.param(LUMEN_TYPED, id="r15_typed_100"),
                                   pytest.param("Lumen Edp", id="r16_untyped")])
def test_pc1b_m5b_exact_gate_off_keeps_mains_matcher(monkeypatch, typed):
    """PC1b M5b PIN, passes at base 7e2e317c (spec section 3, PC1 coverage): R15's shape (typed
    100 ml, the first variant 30 ml) and R16's numeric-label shape (untyped), with the switch ON
    and ENABLE_EXACT_PRICE_GATE='false': main's answer, variants[0] (4.500) with the
    string-sorted label 100ml, the same dict as with the switch off. Kills a J1 / J2 that ignores
    the exact gate."""
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "false")
    setflags(monkeypatch, pnl=None, vg=None)
    off = lumen_hit(typed, LUMEN_FIRST_30)
    setflags(monkeypatch, pnl="true", vg=None)
    on = lumen_hit(typed, LUMEN_FIRST_30)
    assert on is not None and on["amount"] == 4.5 and on["size"] == "100ml", on
    assert on == off, (on, off)


def test_pc1b_p1_unitless_titles_at_one_price_still_bind(monkeypatch):
    """PC1b P1 PIN, passes at base 7e2e317c (spec section 3, the guard boundary): unit-less
    variant titles at ONE price (Small 10.000, Large 10.000), typed and titled 100 ml, switch ON,
    VG off: J1 binds (the binder is called once) and the product prices 10.000 labelled 100ml.
    Pins the distinct-price condition of the guard: with one price no other bottle's price can be
    shown, so the product keeps its hit."""
    setflags(monkeypatch, pnl="true", vg=None)
    seen = count_binder(monkeypatch)
    out = lumen_hit(LUMEN_TYPED, [v("Small", "10.000"), v("Large", "10.000")])
    assert seen == [LUMEN_TYPED], seen
    assert out is not None and out["amount"] == 10.0 and out["size"] == "100ml", out


# PC1b VG PIN (gate condition (b), a RED amendment, rows added only): base's answer on VG's own
# path for every unit-less shape, the literal measured at base 7e2e317c (the code of C1 e120439c).
PC1B_VG_BASE = {
    "amount": 4.5, "currency": "BHD", "original_currency": "BHD", "retailer": LUMEN_HOST,
    "url": "https://house-b.example.com/products/lumen-edp", "in_stock": True, "confidence": 1.0,
    "estimated": False, "source_method": "shopify_json", "concentration": "EDP", "size": "100ml",
    "title": LUMEN_TYPED, "match_score": 1.0,
}


def test_pc1b_vg_pin_the_guard_stays_off_the_vg_path(monkeypatch):
    """PC1b VG PIN, passes at base 7e2e317c (gate condition (b), a RED amendment): VG ON
    (ENABLE_VARIANT_MIN_PRICE_GUARD, its own path), the switch unset or on, every unit-less shape
    of this block, typed 'Lumen Edp 100ml' and untyped 'Lumen Edp': the matcher returns exactly
    base's answer, PC1B_VG_BASE (the 30-unit variant's 4.500 labelled 100ml: VG's binder reads
    the product title; the gap PC1b leaves on VG's path is a stated limit). Kills a guard that
    also runs on VG's path (R17 and R17b use unit-bearing variant titles only)."""
    for pnl in (None, "true"):
        for shape in PC1B_SHAPES:
            for typed in (LUMEN_TYPED, "Lumen Edp"):
                setflags(monkeypatch, pnl=pnl, vg="true")
                out = lumen_hit(typed, pc1b_variants(shape))
                assert out == PC1B_VG_BASE, (pnl, shape, typed, out)


# PC1b AR rows (ruling ORCH-PC1B-A, a RED amendment, rows added only): the PC1b adversary's AR1 to
# AR3, adapted to this file's helpers. AR1 pins the switch-OFF answer on the guard's own shapes (a
# guard leaking into main's variants[0] branch fails it); AR2 and AR3 pin a unit-less bound variant
# that is NOT variants[0] (a guard reading the first variant's title fails them).
PC1B_MAINS_ANSWER = {"amount": 4.5, "size": "100ml", "source_method": "shopify_json"}
PC1B_AR2_VARIANTS = (("30ml", "4.500"), ("Small", "6.500"), ("Large", "10.000"))


def pc1b_ar2_variants():
    """Fresh variant dicts of the AR2 product (30ml first, then two unit-less titles)."""
    return [v(size, price) for size, price in PC1B_AR2_VARIANTS]


@pytest.mark.parametrize("lmg", PC1B_LMGCELLS)
@pytest.mark.parametrize("pnl", [pytest.param(None, id="pnl_unset"), pytest.param("false", id="pnl_false"),
                                 pytest.param(" Off ", id="pnl_padded_off")])
def test_pc1b_ar1_switch_off_unitless_shapes_keep_mains_answer(monkeypatch, pnl, lmg):
    """PC1b AR1 PIN (ORCH-PC1B-A; switch-OFF identity on the guard's own shapes): ENABLE_PRICE_NOT_LOST
    unset, 'false' or ' Off ', VG off, the exact gate on, ENABLE_LISTING_MATCH_GUARD unset or on:
    every unit-less shape of the PC1b block, typed and untyped, prices main's variants[0] (4.500,
    '100ml', shopify_json) and the binder is never called. Kills a guard placed where the switch
    does not reach (main's variants[0] branch)."""
    setflags(monkeypatch, pnl=pnl, vg=None, lmg=lmg)
    seen = count_binder(monkeypatch)
    for shape in PC1B_SHAPES:
        for typed in (LUMEN_TYPED, "Lumen Edp"):
            out = lumen_hit(typed, pc1b_variants(shape))
            got = None if out is None else {k: out.get(k) for k in PC1B_MAINS_ANSWER}
            assert got == PC1B_MAINS_ANSWER, (shape, typed, out)
    assert seen == [], seen


def test_pc1b_ar2_unitless_bound_variant_that_is_not_the_first_gives_no_hit(monkeypatch):
    """PC1b AR2 (ORCH-PC1B-A; switch ON, VG off): 'Lumen Edp 100ml' with variants [30ml 4.500,
    Small 6.500, Large 10.000], typed 100 ml: the binder skips the unit-bearing 30ml and binds
    'Small' through the product title; the product gives no hit (never 6.500 at the typed 100 ml).
    Main binds 'Small'. Kills a guard that reads the first variant's title instead of the bound
    variant's own title."""
    setflags(monkeypatch, pnl="true", vg=None)
    out = lumen_hit(LUMEN_TYPED, pc1b_ar2_variants())
    assert out is None, out


@pytest.mark.parametrize("cap", CAPCELLS)
def test_pc1b_ar3_unitless_bound_variant_not_first_never_shown_on_the_wire(monkeypatch, caplog, cap):
    """PC1b AR3 (ORCH-PC1B-A; switch ON, VG off, ENABLE_LISTING_MATCH_GUARD on as on web): the pair
    'Lumen Edp 100ml vs Mubeen Edp 100ml' with the AR2 product: the Lumen side is never SHOWN at
    6.500."""
    setflags(monkeypatch, pnl="true", vg=None, lmg="true")
    caplog.set_level(logging.INFO)
    lum = lumen_hit(LUMEN_TYPED, pc1b_ar2_variants())
    body = build_pair(LUMEN_TYPED, lum, MUBEEN, house_hit(MUBEEN), cap=cap)
    w = ov(body)[0]
    assert not (shown(w) and w.get("amount") == 6.5), w
