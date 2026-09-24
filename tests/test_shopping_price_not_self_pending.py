"""W4-2 (PO-RECORDED-MEASURED-03) — the Serper-shopping rung must not put a
SEARCH link in ``price["url"]``.

Flag ``ENABLE_SHOPPING_DISCOVERY_URL_SPLIT`` (default OFF, read PER CALL),
COUPLED in code to W4-1's ``ENABLE_SHOPPING_CURRENCY_TRUTH`` (Fable ruling R1:
the split is on only when BOTH are on). With the pair ON, a search link — a
Serper ``link`` that ``_is_listing_url`` flags, or the ``build_retailer_url``
search fallback synthesized when there is no link — is carried in the PRIVATE
key ``_discovery_url`` (ruling R4) and ``url`` is absent/None, so the display
backstop in ``is_price_showable`` stops pending the rung's own output while
``should_cache_price`` / ``select_best`` keep refusing a url-less row (the unit
buys DISPLAY only). A real merchant PDP link is untouched in every state.

Numbering follows the spec's "Red tests" section as amended by the FABLE
REVIEW RULINGS (2026-09-23): the Tier-1 park edit is dropped (R2), tests 8/9
drive the real ``_get_price`` (R3), the key is ``_discovery_url`` (R4), test
6's live half is unconditional (R7), test 12 is parametrised on the exact gate
ON only (R7), and test 11 is a Preserve pin (R7).

Every test here is offline: the network is blocked by an autouse socket guard
and every I/O seam of ``_get_price`` is stubbed.
"""

import logging
import os
import socket

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

from unittest.mock import AsyncMock, MagicMock  # noqa: E402

import pytest  # noqa: E402

from app.services import price_service as ps  # noqa: E402
from app.services import structured_comparison_service as scs  # noqa: E402

Q = "Creed Aventus 100ml"
GOOGLE = "https://www.google.com/search?ibp=oshop&q=Creed+Aventus&prds=catalogid:1234567890"
PDP = "https://bahrain.sharafdg.com/product/creed-aventus-100ml"
UNKNOWN = "Totally Unknown Store XYZ"
KEY = "_discovery_url"      # R4 — the private key
PUBLIC_KEY = "discovery_url"  # R4 — must never appear
SPLIT = "ENABLE_SHOPPING_DISCOVERY_URL_SPLIT"
TRUTH = "ENABLE_SHOPPING_CURRENCY_TRUTH"
LOG_TAG = "[SHOPPING_DISCOVERY_URL]"

# Flags whose defaults every test here relies on; cleared so a developer's
# shell cannot change what a pin means.
_DEFAULTED_FLAGS = (
    SPLIT, TRUTH,
    "ENABLE_EXACT_PRICE_GATE",           # default ON
    "ENABLE_PARK_LISTING_URL_TIER1",     # default ON
    "ENABLE_SHOPPING_STRICT_CURRENCY",   # default OFF
    "ENABLE_SHOWABLE_NAME_IDENTITY",     # default OFF
    "ENABLE_EXTENDED_FALLBACK_RATES",    # default OFF
    "ENABLE_GENUINE_PRICE_PRIORITY",
    "ENABLE_NEGCACHE_GENUINE_INVALIDATION",
    "ENABLE_ASYNC_REDIS_OFFLOAD",
    "PRICE_CACHE_BUST",
)


@pytest.fixture(autouse=True)
def _offline_and_default_flags(monkeypatch):
    for name in _DEFAULTED_FLAGS:
        monkeypatch.delenv(name, raising=False)

    real_connect = socket.socket.connect
    real_connect_ex = socket.socket.connect_ex

    def _is_loopback(addr):
        # asyncio's Windows proactor loop builds its self-pipe with a loopback
        # socketpair(); that is the only connect this file may make.
        host = addr[0] if isinstance(addr, tuple) and addr else addr
        return host in ("127.0.0.1", "::1", "localhost")

    def _connect(self, addr):
        if _is_loopback(addr):
            return real_connect(self, addr)
        raise AssertionError(f"W4-2 tests are offline: connect to {addr!r} attempted")

    def _connect_ex(self, addr):
        if _is_loopback(addr):
            return real_connect_ex(self, addr)
        raise AssertionError(f"W4-2 tests are offline: connect_ex to {addr!r} attempted")

    monkeypatch.setattr(socket.socket, "connect", _connect)
    monkeypatch.setattr(socket.socket, "connect_ex", _connect_ex)


def _set_flags(monkeypatch, split, truth):
    """``None`` = unset; any string is exported verbatim."""
    for name, value in ((SPLIT, split), (TRUTH, truth)):
        if value is None:
            monkeypatch.delenv(name, raising=False)
        else:
            monkeypatch.setenv(name, value)


def _split_on(monkeypatch):
    _set_flags(monkeypatch, "true", "true")


def _item(source, link=None):
    it = {"title": Q, "price": "259.44", "source": source}
    if link is not None:
        it["link"] = link
    return it


def _extract(items):
    return ps.extract_price_from_shopping(
        Q, items, "BHD", shopping_region="bahrain", category="fragrance",
    )


def _showable(price):
    """(verdict, guard_rejected) on a COPY — the chokepoint stamps its input."""
    probe = dict(price)
    verdict = ps.is_price_showable(Q, probe, "fragrance", enforce_correctness=True)
    return verdict, probe.get("guard_rejected")


def _split_records(caplog):
    return [r for r in caplog.records if LOG_TAG in r.getMessage()]


# ---------------------------------------------------------------------------
# 1. RED — the finding's exact assertion (front door, google-linked item)
# ---------------------------------------------------------------------------

def test_1_google_link_goes_to_private_discovery_key_and_row_displays(monkeypatch):
    _split_on(monkeypatch)
    price = _extract([_item("Best Buy", GOOGLE)])
    assert price is not None
    assert price.get("url") is None
    assert price.get(KEY) == GOOGLE
    assert PUBLIC_KEY not in price
    # R1 composition: the row W4-2 un-pends is never genuine.
    assert price["source_method"] == "converted_usd"
    verdict, guard = _showable(price)
    assert verdict is True
    assert guard is None


# ---------------------------------------------------------------------------
# 2. PIN — flag OFF (and the R1 decoupled state) is byte-identical to HEAD
# ---------------------------------------------------------------------------

_OFF_STATES = [
    pytest.param(None, None, id="split-unset_truth-unset"),
    pytest.param("false", None, id="split-false_truth-unset"),
    pytest.param("true", None, id="R1-split-true_truth-unset"),
    pytest.param("TRUE", "false", id="R1-split-TRUE_truth-false"),
    pytest.param(None, "true", id="split-unset_truth-true"),
    pytest.param("false", "true", id="split-false_truth-true"),
    pytest.param("0", "true", id="split-0_truth-true"),
]


@pytest.mark.parametrize("split,truth", _OFF_STATES)
def test_2_split_off_states_are_byte_identical_to_head(monkeypatch, caplog, split, truth):
    caplog.set_level(logging.INFO)
    items = [_item("Best Buy", GOOGLE)]
    _set_flags(monkeypatch, None, truth)
    reference = _extract(items)
    _set_flags(monkeypatch, split, truth)
    caplog.clear()
    price = _extract(items)
    assert price == reference                      # same dict, same key set
    assert price["url"] == GOOGLE
    assert KEY not in price and PUBLIC_KEY not in price
    verdict, guard = _showable(price)
    assert verdict is False
    assert guard == "non_pdp_url"
    assert _split_records(caplog) == []            # R1: no log line either


# ---------------------------------------------------------------------------
# 3. RED — the synthesized no-link fallback never enters `url`
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("source", [
    pytest.param("Best Buy", id="listing-caught-template"),
    pytest.param("Amazon", id="NOT-listing-caught-template"),
])
def test_3_synthesized_search_url_goes_to_discovery_key(monkeypatch, source):
    expected = ps.build_retailer_url(source, Q)
    assert expected  # the fixture only means something if a template exists
    _split_on(monkeypatch)
    price = _extract([_item(source)])
    assert price is not None
    assert price.get("url") is None
    assert price.get(KEY) == expected
    assert PUBLIC_KEY not in price
    assert price["source_method"] == "converted_usd"
    verdict, guard = _showable(price)
    assert verdict is True
    assert guard is None


# ---------------------------------------------------------------------------
# 4. PIN — an unknown retailer with no link invents nothing
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("split,truth", [("true", "true"), (None, None), (None, "true")])
def test_4_unknown_retailer_no_link_invents_no_url_or_discovery(monkeypatch, split, truth):
    assert ps.build_retailer_url(UNKNOWN, Q) is None
    _set_flags(monkeypatch, split, truth)
    price = _extract([_item(UNKNOWN)])
    assert price is not None
    assert price["url"] is None
    assert KEY not in price
    assert PUBLIC_KEY not in price


# ---------------------------------------------------------------------------
# 5. PIN — a real merchant PDP is untouched in every flag state
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("split,truth", [
    ("true", "true"), (None, None), ("true", None), (None, "true"),
])
def test_5_real_pdp_link_untouched(monkeypatch, split, truth):
    _set_flags(monkeypatch, split, truth)
    price = _extract([_item("Sharaf DG", PDP)])
    assert price is not None
    assert price["url"] == PDP
    assert KEY not in price and PUBLIC_KEY not in price
    assert price["source_method"] == "local_bhd"
    verdict, guard = _showable(price)
    assert verdict is True
    assert guard is None


# ---------------------------------------------------------------------------
# 6. PIN + RED — showable-not-genuine, never genuine
# ---------------------------------------------------------------------------

_DISCOVERY_ONLY_ROW = {
    "amount": 259.44, "currency": "BHD", "retailer": "Best Buy", "in_stock": True,
    "source_method": "converted_usd", "title": Q, KEY: GOOGLE,
}


def test_6a_pin_discovery_only_row_is_showable_but_not_genuine():
    """PIN (pure predicates the unit does not own; green at HEAD)."""
    row = dict(_DISCOVERY_ONLY_ROW)
    verdict, guard = _showable(row)
    assert verdict is True and guard is None
    assert ps.is_genuine_source_method("converted_usd") is False
    assert ps.price_cache_ttl(row) == 86400
    assert ps.should_cache_price(Q, row, "fragrance") is False


def test_6b_live_both_flags_google_row_is_converted_urlless_showable(monkeypatch):
    """RED — R7: unconditional now that W4-1 is merged."""
    assert hasattr(ps, "shopping_currency_truth_enabled")
    _split_on(monkeypatch)
    price = _extract([_item("Best Buy", GOOGLE)])
    assert price["source_method"] == "converted_usd"
    assert price.get("url") is None
    assert _showable(price) == (True, None)
    assert ps.price_cache_ttl(price) == 86400
    assert ps.should_cache_price(Q, price, "fragrance") is False


# ---------------------------------------------------------------------------
# 6c. RED — the canary line (spec §9, ruling R6(e): once for `best`)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("items,reason", [
    pytest.param([_item("Best Buy", GOOGLE)], "listing_url", id="listing"),
    pytest.param([_item("Best Buy")], "synthesized", id="synthesized"),
    pytest.param([_item("Best Buy", GOOGLE),
                  _item("Walmart", GOOGLE + "&x=2")], "listing_url", id="two-split-candidates"),
])
def test_6c_split_logs_one_canary_line_for_best(monkeypatch, caplog, items, reason):
    caplog.set_level(logging.INFO)
    _split_on(monkeypatch)
    price = _extract(items)
    assert price is not None and price.get("url") is None
    recs = _split_records(caplog)
    assert len(recs) == 1
    assert f"reason={reason}" in recs[0].getMessage()


def test_6d_no_canary_line_for_a_real_pdp(monkeypatch, caplog):
    caplog.set_level(logging.INFO)
    _split_on(monkeypatch)
    _extract([_item("Sharaf DG", PDP)])
    assert _split_records(caplog) == []


# ---------------------------------------------------------------------------
# 7. RED — the stash mirror (_seed_shortcircuit_candidates) agrees
# ---------------------------------------------------------------------------

def _seeded_raw(item):
    svc = scs.get_comparison_service()
    svc._shopping_items_cache[Q] = [item]
    svc._seed_shortcircuit_candidates(
        Q, kind="tier1_shopping", currency="BHD", shopping_region="bahrain",
    )
    cands = svc._price_candidates.get(Q) or []
    assert len(cands) == 1, "the fixture item must be seeded in every state"
    return cands[0]["raw_data"]


@pytest.mark.parametrize("source,link,expected_discovery", [
    pytest.param("Best Buy", GOOGLE, GOOGLE, id="google-link"),
    pytest.param("Amazon", None, "https://www.amazon.com/s?k=Creed+Aventus+100ml",
                 id="no-link-synthesized"),
])
def test_7_stash_mirror_splits_like_the_front_door(monkeypatch, source, link, expected_discovery):
    assert ps.build_retailer_url("Amazon", Q) == "https://www.amazon.com/s?k=Creed+Aventus+100ml"
    _split_on(monkeypatch)
    raw = _seeded_raw(_item(source, link))
    assert raw.get("url") is None
    assert raw.get(KEY) == expected_discovery
    assert PUBLIC_KEY not in raw
    assert raw["source_method"] == "converted_usd"


@pytest.mark.parametrize("split,truth", _OFF_STATES)
def test_7_off_stash_mirror_is_byte_identical_to_head(monkeypatch, split, truth):
    item = _item("Best Buy", GOOGLE)
    _set_flags(monkeypatch, None, truth)
    reference = _seeded_raw(item)
    _set_flags(monkeypatch, split, truth)
    raw = _seeded_raw(item)
    assert raw == reference
    assert raw["url"] == GOOGLE
    assert KEY not in raw and PUBLIC_KEY not in raw


# ---------------------------------------------------------------------------
# 8 / 9 — the REAL _get_price (ruling R3), on the test_converted_* harness
# ---------------------------------------------------------------------------

class _Harness:
    """Drives ``StructuredComparisonService._get_price`` for Q with every I/O
    seam stubbed: Tier-1 shopping returns ``items``; the Tier-1.5 discovery,
    fan-out, Tier-2 organic and every direct adapter miss; Tier-3 would be a
    290 BHD estimate. Records the seed kinds, the L1 writes, the L2 writes,
    and whether the Tier-1.5 cascade ran."""

    def __init__(self, monkeypatch, items, after_tier1=None):
        self.mp = monkeypatch
        self.items = items
        self.after_tier1 = after_tier1
        self.seed_kinds = []
        self.cache_writes = []
        self.fan_out_calls = 0
        self.search_web_calls = 0
        self.save_db = None

    def install(self):
        mp = self.mp
        mp.setattr(scs, "get_cached", lambda *a, **k: None)
        mp.setattr(scs, "set_cached", lambda *a, **k: None)
        mp.setattr(scs, "set_negative_cache", MagicMock())
        mp.setattr(scs, "_cache_get_async", AsyncMock(return_value=None))

        async def _cache_set(key, value, ttl):
            self.cache_writes.append((key, dict(value) if isinstance(value, dict) else value, ttl))

        mp.setattr(scs, "_cache_set_async", _cache_set)
        mp.setattr("app.services.product_data_service.get_cached_price",
                   AsyncMock(return_value=None))
        for fn in (
            "get_algolia_sources_for_category", "get_unbxd_sources_for_category",
            "get_shopify_sources_for_category", "get_noon_sources_for_category",
            "get_woo_sources_for_category", "get_salla_sources_for_category",
            "get_occ_sources_for_category", "get_magento_gql_sources_for_category",
            "get_restjson_sources_for_category", "get_jsonapi_sources_for_category",
            "get_gcc_shopify_pagescrape_sources_for_category",
            "get_curl_pagescrape_sources_for_category", "get_sitemap_sources_for_category",
        ):
            if hasattr(scs, fn):
                mp.setattr(scs, fn, lambda *a, **k: [])
        mp.setattr(scs, "get_official_domain", lambda *a, **k: None)
        mp.setattr(scs, "fetch_shopify_price", AsyncMock(return_value=None))
        mp.setattr(scs, "fetch_nasser_price", AsyncMock(return_value=None))
        mp.setattr(scs, "search_product_prices", AsyncMock(return_value={
            "shopping": list(self.items), "organic": [], "shopping_region": "bahrain",
        }))

        async def _search_web(*a, **k):
            self.search_web_calls += 1
            return {"organic": []}

        async def _fan_out(*a, **k):
            self.fan_out_calls += 1
            return {"best": None}

        mp.setattr(scs, "search_web", _search_web)
        mp.setattr(scs, "fan_out_price_lookup", _fan_out)
        mp.setattr(scs, "search_price_organic",
                   AsyncMock(return_value={"organic": [], "knowledge_graph": None}))
        mp.setattr(scs, "extract_price", AsyncMock(return_value=(None, {})))
        mp.setattr(scs, "extract_price_from_training_data",
                   AsyncMock(return_value=({"amount": 290.0, "currency": "BHD"}, {})))

        real_seed = scs.StructuredComparisonService._seed_shortcircuit_candidates

        def _seed_spy(svc, full_name, **kw):
            self.seed_kinds.append(kw.get("kind"))
            return real_seed(svc, full_name, **kw)

        mp.setattr(scs.StructuredComparisonService, "_seed_shortcircuit_candidates", _seed_spy)

        if self.after_tier1 is not None:
            real_extract = scs.extract_price_from_shopping
            hook = self.after_tier1

            def _extract_then(*a, **k):
                out = real_extract(*a, **k)
                hook()
                return out

            mp.setattr(scs, "extract_price_from_shopping", _extract_then)
        return self

    async def run(self):
        svc = scs.get_comparison_service()
        svc._save_price_to_db = MagicMock()
        result = await svc._get_price(
            brand="Creed", name="Aventus", variant="100ml", region="bahrain",
            search_query="Creed Aventus 100ml price", nocache=True, category="fragrance",
        )
        self.save_db = svc._save_price_to_db
        return result

    def price_writes(self):
        """L1 writes of a resolved price dict (the price key, not a sentinel)."""
        return [w for w in self.cache_writes
                if isinstance(w[1], dict) and w[1].get("amount") == pytest.approx(259.44)]


def _observables(h, result):
    return {
        "result": dict(result),
        "seed_kinds": list(h.seed_kinds),
        "save_db_calls": [c.args for c in h.save_db.call_args_list],
        "cache_writes": list(h.cache_writes),
        "fan_out": h.fan_out_calls,
        "search_web": h.search_web_calls,
    }


@pytest.mark.asyncio
async def test_8_tier1_google_row_parks_and_returns_url_less_after_cascade(monkeypatch):
    """RED — R3 rewrite of the spec's test 8 (the park edit is DROPPED, R2):
    with W4-1 on, the split google row is converted_usd, so it PARKS (never the
    genuine Tier-1 short-circuit — no tier1_shopping seed, the Tier-1.5 cascade
    runs), reaches tier-7 and returns with no url and the private discovery
    key, and nothing is written to L1 or L2."""
    _split_on(monkeypatch)
    h = _Harness(monkeypatch, [_item("Best Buy", GOOGLE)]).install()
    result = await h.run()
    assert "tier1_shopping" not in h.seed_kinds
    assert h.search_web_calls + h.fan_out_calls >= 1   # the cascade was not skipped
    assert result.get("estimated") is not True
    assert result["source_method"] == "converted_usd"
    assert result["amount"] == pytest.approx(259.44)
    assert result.get("url") is None
    assert result.get(KEY) == GOOGLE
    assert PUBLIC_KEY not in result
    assert h.save_db.call_count == 0
    assert h.price_writes() == []


@pytest.mark.parametrize("source", [
    pytest.param("Best Buy", id="bestbuy-listing-template"),
    pytest.param("Amazon", id="amazon-NOT-listing-template"),
])
@pytest.mark.asyncio
async def test_9_tier7_backfill_does_not_remint_the_search_url(monkeypatch, source):
    """RED — R3 rewrite of the spec's test 9: the parked no-link row reaches
    the tier-7 ``converted_fallback`` backfill; with the split ON it must not
    re-stamp ``build_retailer_url`` into ``url``, and (the Amazon shape) must
    not be cached for 24 h or written as an L2 row on a fabricated url."""
    expected = ps.build_retailer_url(source, Q)
    _split_on(monkeypatch)
    h = _Harness(monkeypatch, [_item(source)]).install()
    result = await h.run()
    assert "tier1_shopping" not in h.seed_kinds
    assert result.get("estimated") is not True
    assert result["source_method"] == "converted_usd"
    assert result.get("url") is None
    assert result.get(KEY) == expected
    assert PUBLIC_KEY not in result
    assert h.save_db.call_count == 0
    assert h.price_writes() == []


@pytest.mark.asyncio
async def test_9b_mid_request_rollback_does_not_remint_the_search_url(monkeypatch):
    """RED — R3: ``_discovery_url_of`` reads the key UNCONDITIONALLY. The split
    flag is rolled back between the Tier-1 extraction and the tier-7 backfill;
    the row already carries the private key, so the backfill must still not
    re-mint the search url (a flag read inside the guard would)."""
    _split_on(monkeypatch)
    h = _Harness(monkeypatch, [_item("Amazon")],
                 after_tier1=lambda: monkeypatch.delenv(SPLIT, raising=False)).install()
    result = await h.run()
    assert os.getenv(SPLIT) is None                    # the rollback happened
    assert result.get("url") is None
    assert result.get(KEY) == ps.build_retailer_url("Amazon", Q)
    assert h.save_db.call_count == 0


@pytest.mark.parametrize("source,link", [
    pytest.param("Best Buy", GOOGLE, id="google-link"),
    pytest.param("Amazon", None, id="amazon-no-link"),
    pytest.param("Best Buy", None, id="bestbuy-no-link"),
])
@pytest.mark.parametrize("split,truth", [
    pytest.param("true", None, id="R1-split-true_truth-unset"),
    pytest.param("false", "true", id="split-false_truth-true"),
])
@pytest.mark.asyncio
async def test_8_9_off_get_price_observables_byte_identical_to_head(monkeypatch, source, link, split, truth):
    """PIN — R1: split=true with TRUTH unset (and split off with TRUTH on) is
    byte-identical to HEAD at the _get_price level: the returned dict, the seed
    calls, the L1 writes, the L2 writes and the cascade reach."""
    _set_flags(monkeypatch, None, truth)
    h0 = _Harness(monkeypatch, [_item(source, link)]).install()
    reference = _observables(h0, await h0.run())
    _set_flags(monkeypatch, split, truth)
    h1 = _Harness(monkeypatch, [_item(source, link)]).install()
    observed = _observables(h1, await h1.run())
    assert observed == reference
    assert KEY not in observed["result"] and PUBLIC_KEY not in observed["result"]


def test_8_helper_discovery_url_of_reads_the_key_unconditionally(monkeypatch):
    """RED — R3 names the helper: it reads the private key with NO flag read."""
    helper = getattr(scs, "_discovery_url_of")
    _set_flags(monkeypatch, None, None)
    assert helper({KEY: GOOGLE}) == GOOGLE
    assert helper({"url": PDP}) == ""
    assert helper({KEY: None}) == ""
    assert helper(None) == ""
    assert helper("not a dict") == ""
    _split_on(monkeypatch)
    assert helper({KEY: GOOGLE}) == GOOGLE


# ---------------------------------------------------------------------------
# 10. PIN/RED — the flag reader (per-call, coupled to W4-1: ruling R1)
# ---------------------------------------------------------------------------

_READER_TABLE = [
    (None, None, False),
    (None, "true", False),
    ("true", None, False),          # R1 — coupling: TRUTH unset
    ("true", "false", False),       # R1
    ("1", "0", False),              # R1
    ("on", "off", False),           # R1
    ("true", "true", True),
    ("1", "true", True),
    ("yes", "1", True),
    ("on", "yes", True),
    ("TRUE", "true", True),         # .strip().lower() on the split flag
    (" true ", "true", True),
    ("On", "on", True),
    ("true", "TRUE", True),         # ... and on the W4-1 flag
    ("true", " on ", True),
    ("false", "true", False),
    ("0", "true", False),
    ("no", "true", False),
    ("off", "true", False),
    ("", "true", False),
    ("maybe", "true", False),
]


def test_10_flag_reader_truth_table(monkeypatch):
    """ONE test over the whole table, so a do-nothing reader (always False)
    and an UNCOUPLED reader (R1 conjunct missing) both redden on an assertion,
    not only on the missing attribute. Mismatching rows are listed."""
    reader = getattr(ps, "shopping_discovery_url_split_enabled")
    wrong = []
    for split, truth, expected in _READER_TABLE:
        _set_flags(monkeypatch, split, truth)
        got = reader()
        if got is not expected:
            wrong.append((split, truth, expected, got))
    assert wrong == []


def test_10_flag_reader_is_read_per_call(monkeypatch):
    reader = getattr(ps, "shopping_discovery_url_split_enabled")
    _set_flags(monkeypatch, None, None)
    assert reader() is False
    _split_on(monkeypatch)
    assert reader() is True
    monkeypatch.delenv(TRUTH)            # a W4-1 rollback turns the split off
    assert reader() is False
    monkeypatch.setenv(TRUTH, "true")
    assert reader() is True
    monkeypatch.setenv(SPLIT, "off")
    assert reader() is False


# ---------------------------------------------------------------------------
# 11. PRESERVE PIN — the wire projection, asserted not assumed (R4, R7)
# ---------------------------------------------------------------------------

def test_11_pin_public_price_view_strips_the_private_key_gate_on():
    view = ps.public_price_view(dict(_DISCOVERY_ONLY_ROW, _cached=False,
                                     guard_rejected="non_pdp_url"))
    assert KEY not in view
    assert "_cached" not in view and "guard_rejected" not in view
    assert view["amount"] == 259.44 and "url" not in view


def test_11_pin_public_price_view_gate_off_returns_input_unchanged(monkeypatch):
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "false")
    row = dict(_DISCOVERY_ONLY_ROW, _cached=False)
    view = ps.public_price_view(row)
    assert view is row
    assert view[KEY] == GOOGLE                     # the stated gate-off rollback shape


# ---------------------------------------------------------------------------
# 12. PIN — nothing new becomes selectable or cacheable (exact gate ON only, R7)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("gate", [None, "true"], ids=["gate-default-on", "gate-explicit-on"])
@pytest.mark.parametrize("split,truth", [("true", "true"), (None, None)])
def test_12_pin_discovery_only_row_not_selectable_not_cacheable(monkeypatch, gate, split, truth):
    if gate is None:
        monkeypatch.delenv("ENABLE_EXACT_PRICE_GATE", raising=False)
    else:
        monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", gate)
    assert ps.exact_gate_enabled() is True
    _set_flags(monkeypatch, split, truth)
    row = dict(_DISCOVERY_ONLY_ROW)
    assert ps.select_best([dict(row)], Q, "fragrance") is None
    assert ps.should_cache_price(Q, row, "fragrance") is False


# ---------------------------------------------------------------------------
# 12b. GREEN-PHASE PIN (Fable red-gate ruling 4) — the ENABLE_EXACT_PRICE_GATE
# =false consequence, pinned as CURRENT behaviour and stated in the PR body:
# with the exact gate rolled back, a discovery-only row IS cacheable and
# selectable (the gate is what refuses it). Not a fix; a disclosure.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("split,truth", [("true", "true"), (None, None)])
def test_12b_green_pin_gate_off_discovery_only_row_is_cacheable_and_selectable(
    monkeypatch, split, truth,
):
    """GREEN-PHASE PIN (ruling 4): gate OFF -> should_cache_price True and
    select_best returns the url-less row with its private key inside."""
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "false")
    assert ps.exact_gate_enabled() is False
    _set_flags(monkeypatch, split, truth)
    row = dict(_DISCOVERY_ONLY_ROW)
    assert ps.should_cache_price(Q, row, "fragrance") is True
    picked = ps.select_best([dict(row)], Q, "fragrance")
    assert picked is not None
    assert picked.get("url") is None
    assert picked.get(KEY) == GOOGLE


@pytest.mark.asyncio
async def test_12c_green_pin_gate_off_split_row_is_l1_and_l2_written(monkeypatch):
    """GREEN-PHASE PIN (ruling 4, R7 rollback shape) on the REAL _get_price:
    split + W4-1 ON but ENABLE_EXACT_PRICE_GATE=false -> the url-less Amazon
    row returns with ``_discovery_url``, is L1-cached WITH the private key
    inside and handed to the L2 writer with no url. Current behaviour of the
    gate-off rollback state, stated in the PR body — not something this unit
    changes (the tier-7 guard still keeps the search url out of ``url``)."""
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "false")
    _split_on(monkeypatch)
    expected = ps.build_retailer_url("Amazon", Q)
    h = _Harness(monkeypatch, [_item("Amazon")]).install()
    result = await h.run()
    assert result.get("url") is None
    assert result.get(KEY) == expected
    writes = h.price_writes()
    assert len(writes) == 1
    assert writes[0][1].get(KEY) == expected and writes[0][1].get("url") is None
    assert h.save_db.call_count == 1
    l2_price = h.save_db.call_args.args[-1]
    assert l2_price.get("url") is None and l2_price.get(KEY) == expected


# ===========================================================================
# GREEN-PHASE PINS added by the W4-2 FIXER (adversary defects D1-D3 and the
# tests_that_prove_nothing entries). Each is labelled with the mutation it was
# checked against. The OFF-state pins below compare against LITERAL values
# (measured at base 6ab9d7ea, where these node ids pass unchanged), never
# against a second run of the modified code — the self-reference the
# adversary flagged in test_8_9_off / test_7_off.
# ===========================================================================

AMAZON_SEARCH = "https://www.amazon.com/s?k=Creed+Aventus+100ml"
BESTBUY_SEARCH = "https://www.bestbuy.com/site/searchpage.jsp?st=Creed+Aventus+100ml"
NOON_SEARCH = "https://www.noon.com/search?q=Creed+Aventus+100ml"
_SEVEN_DAYS, _ONE_DAY = 604800, 86400

# Every split-OFF state: unset, explicit false, and the R1 decoupled state
# (split=true with W4-1 unset) — each with W4-1 off and on where it applies.
_OFF_GET_PRICE_STATES = [
    pytest.param(None, None, id="split-unset_truth-unset"),
    pytest.param("true", None, id="R1-split-true_truth-unset"),
    pytest.param("false", "true", id="split-false_truth-true"),
    pytest.param(None, "true", id="split-unset_truth-true"),
]


def _base_literal(source, link, truth_on):
    """The 6ab9d7ea observables of the real _get_price for Q (measured there).
    W4-1 off: the row is local_bhd — the Amazon template (not a listing url)
    is a genuine Tier-1 short-circuit (seeded, 7 d L1 + L2); the google link
    and the Best Buy template park, reach tier-7, and write nothing. W4-1 on:
    every shape is converted_usd and parks; only the Amazon template is
    cacheable (24 h L1 + L2)."""
    url = link or {"Amazon": AMAZON_SEARCH, "Best Buy": BESTBUY_SEARCH}[source]
    amazon = source == "Amazon" and link is None
    return {
        "url": url,
        "source_method": "converted_usd" if truth_on else "local_bhd",
        "seed_kinds": ["tier1_shopping"] if (amazon and not truth_on) else [],
        "save_db_urls": [url] if amazon else [],
        "price_writes": [(_ONE_DAY if truth_on else _SEVEN_DAYS, url)] if amazon else [],
    }


@pytest.mark.parametrize("source,link", [
    pytest.param("Best Buy", GOOGLE, id="google-link"),
    pytest.param("Amazon", None, id="amazon-no-link"),
    pytest.param("Best Buy", None, id="bestbuy-no-link"),
])
@pytest.mark.parametrize("split,truth", _OFF_GET_PRICE_STATES)
@pytest.mark.asyncio
async def test_13_green_pin_off_get_price_matches_base_literals(monkeypatch, split, truth, source, link):
    """GREEN-PHASE PIN (fixer, D2): the real _get_price in every split-OFF
    state against LITERAL base values — url, label, seed calls, L1 and L2
    writes. Mutation-checked: the stash OFF branch dropping the no-link
    template (N4) and the front-door OFF branch dropping it both redden."""
    _set_flags(monkeypatch, split, truth)
    h = _Harness(monkeypatch, [_item(source, link)]).install()
    result = await h.run()
    expected = _base_literal(source, link, truth == "true")
    assert result.get("url") == expected["url"]
    assert result["source_method"] == expected["source_method"]
    assert result["amount"] == pytest.approx(259.44)
    assert KEY not in result and PUBLIC_KEY not in result
    assert h.seed_kinds == expected["seed_kinds"]
    assert [c.args[-1].get("url") for c in h.save_db.call_args_list] == expected["save_db_urls"]
    assert [(w[2], w[1].get("url")) for w in h.price_writes()] == expected["price_writes"]


_KEYLESS_URLLESS_CONVERTED_ROW = {
    "amount": 259.44, "currency": "BHD", "retailer": "Amazon", "in_stock": True,
    "source_method": "converted_usd", "confidence": 0.9, "retailer_score": 0.5,
    "title": Q, "url": None,
}


@pytest.mark.parametrize("split,truth", _OFF_GET_PRICE_STATES + [
    pytest.param("true", "true", id="split-ON_truth-true"),
])
@pytest.mark.asyncio
async def test_14_green_pin_tier7_legacy_backfill_still_mints_for_a_keyless_row(monkeypatch, split, truth):
    """GREEN-PHASE PIN (fixer, D2 / N3): the tier-7 ``converted_fallback`` url
    backfill is TODAY's behaviour for a parked row with no url and NO private
    key (a producer that is not the split). It must still mint the retailer
    url in every state — the W4-2 guard only blocks a row that carries
    ``_discovery_url``. Mutation-checked: deleting the backfill (N3) reddens
    every param; a guard that blocked on the flag instead of the key would
    redden the split-ON param."""
    _set_flags(monkeypatch, split, truth)
    h = _Harness(monkeypatch, [_item("Amazon")]).install()
    monkeypatch.setattr(scs, "extract_price_from_shopping",
                        lambda *a, **k: dict(_KEYLESS_URLLESS_CONVERTED_ROW))
    result = await h.run()
    assert "tier1_shopping" not in h.seed_kinds
    assert result["source_method"] == "converted_usd"
    assert result.get("url") == AMAZON_SEARCH
    assert KEY not in result
    assert [c.args[-1].get("url") for c in h.save_db.call_args_list] == [AMAZON_SEARCH]
    assert [(w[2], w[1].get("url")) for w in h.price_writes()] == [(_ONE_DAY, AMAZON_SEARCH)]


@pytest.mark.parametrize("source,link,expected_url", [
    pytest.param("Best Buy", GOOGLE, GOOGLE, id="google-link"),
    pytest.param("Amazon", None, AMAZON_SEARCH, id="amazon-no-link"),
    pytest.param("Best Buy", None, BESTBUY_SEARCH, id="bestbuy-no-link"),
    pytest.param("noon", NOON_SEARCH, NOON_SEARCH, id="noon-search-link"),
    pytest.param("Sharaf DG", PDP, PDP, id="pdp-link"),
])
@pytest.mark.parametrize("split,truth", _OFF_STATES)
def test_15_green_pin_off_stash_raw_matches_base_literals(monkeypatch, split, truth, source, link, expected_url):
    """GREEN-PHASE PIN (fixer, D2 / N4): the stash mirror's raw_data in every
    split-OFF state against LITERAL base urls, including the synthesized
    no-link template the OFF branch must still stamp. Mutation-checked: an
    OFF branch that drops the ``build_retailer_url`` fallback (N4) reddens."""
    _set_flags(monkeypatch, split, truth)
    raw = _seeded_raw(_item(source, link))
    assert raw.get("url") == expected_url
    assert KEY not in raw and PUBLIC_KEY not in raw


def test_16_green_pin_rung1_applies_to_a_non_google_listing_link(monkeypatch, caplog):
    """GREEN-PHASE PIN (fixer, D3 / N6): rung 1 is ``_is_listing_url``, not
    "a google host" — a noon /search link is split at the front door AND in
    the stash, and the canary names its host. Mutation-checked: a splitter
    that only splits google hosts (N6) reddens."""
    assert ps._is_listing_url(NOON_SEARCH) is True
    caplog.set_level(logging.INFO)
    _split_on(monkeypatch)
    price = _extract([_item("noon", NOON_SEARCH)])
    assert price.get("url") is None
    assert price.get(KEY) == NOON_SEARCH
    assert _showable(price) == (True, None)
    msgs = [r.getMessage() for r in _split_records(caplog)]
    assert msgs == [f"{LOG_TAG} split url->_discovery_url host=noon.com reason=listing_url for {Q}"]
    raw = _seeded_raw(_item("noon", NOON_SEARCH))
    assert raw.get("url") is None
    assert raw.get(KEY) == NOON_SEARCH


def test_17_green_pin_no_canary_when_best_is_a_pdp_but_a_sibling_split(monkeypatch, caplog):
    """GREEN-PHASE PIN (fixer, D3 / N2 — ruling R6e "once, for best"): the
    google sibling IS split, but ``best`` is the real PDP, so no canary line.
    Mutation-checked: logging whenever ANY candidate split (N2) reddens."""
    caplog.set_level(logging.INFO)
    _split_on(monkeypatch)
    price = _extract([_item("Sharaf DG", PDP), _item("Best Buy", GOOGLE)])
    assert price["url"] == PDP
    assert price["source_method"] == "local_bhd"
    assert KEY not in price
    assert _split_records(caplog) == []


@pytest.mark.parametrize("items,message", [
    pytest.param([_item("Best Buy", GOOGLE)],
                 f"{LOG_TAG} split url->_discovery_url host=google.com reason=listing_url for {Q}",
                 id="listing-google"),
    pytest.param([_item("Best Buy")],
                 f"{LOG_TAG} split url->_discovery_url host=bestbuy.com reason=synthesized for {Q}",
                 id="synthesized-bestbuy"),
    pytest.param([_item("Amazon")],
                 f"{LOG_TAG} split url->_discovery_url host=amazon.com reason=synthesized for {Q}",
                 id="synthesized-amazon"),
])
def test_18_green_pin_canary_line_exact_text_and_host(monkeypatch, caplog, items, message):
    """GREEN-PHASE PIN (fixer, D3 / N1): the exact canary text ops will grep in
    Railway logs — host of the SPLIT url (www-stripped), reason, product.
    Mutation-checked: a wrong ``host=`` (N1) reddens."""
    caplog.set_level(logging.INFO)
    _split_on(monkeypatch)
    _extract(items)
    assert [r.getMessage() for r in _split_records(caplog)] == [message]


def _regional_harness(monkeypatch, row):
    handed = []

    async def _fake_get_price(self, *a, **k):
        out = dict(row)
        handed.append(out)
        return out

    monkeypatch.setattr(scs.StructuredComparisonService, "_get_price", _fake_get_price)
    return handed


@pytest.mark.asyncio
async def test_19_green_pin_regional_prices_strips_private_key_under_gate(monkeypatch):
    """GREEN-PHASE PIN (fixer, D1): GET /api/v1/text/prices ships the raw
    ``get_regional_prices`` dicts (no public_price_view). A showable split row
    must NOT carry ``_discovery_url`` there while the exact gate is on (R4),
    and the cascade's own dict is not mutated. Mutation-checked: removing the
    strip reddens; an in-place pop reddens the no-mutation assertion."""
    _split_on(monkeypatch)
    handed = _regional_harness(monkeypatch, _DISCOVERY_ONLY_ROW)
    out = await scs.get_regional_prices("Creed", "Aventus", "100ml", Q)
    regional = out["regional_prices"]
    assert regional and len(regional) == len(handed)
    for region, price in regional.items():
        assert price["amount"] == 259.44, region
        assert KEY not in price and PUBLIC_KEY not in price, region
        assert price.get("url") is None, region
    assert all(h.get(KEY) == GOOGLE for h in handed)   # a copy was stripped


@pytest.mark.asyncio
async def test_19b_green_pin_regional_prices_gate_off_and_keyless_rows_untouched(monkeypatch):
    """GREEN-PHASE PIN (fixer, D1): the strip is scoped like public_price_view
    — gate OFF returns the row as-is (the stated rollback shape), and a row
    WITHOUT the key (every flag-OFF row) is returned as the very same object
    (the base behaviour). Mutation-checked: a strip that ignores the gate
    reddens the gate-off half."""
    _split_on(monkeypatch)
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "false")
    handed = _regional_harness(monkeypatch, _DISCOVERY_ONLY_ROW)
    out = await scs.get_regional_prices("Creed", "Aventus", "100ml", Q)
    for region, price in out["regional_prices"].items():
        assert price.get(KEY) == GOOGLE, region
    monkeypatch.delenv("ENABLE_EXACT_PRICE_GATE")
    _set_flags(monkeypatch, None, None)
    keyless = {k: v for k, v in _DISCOVERY_ONLY_ROW.items() if k != KEY}
    keyless["url"] = PDP
    handed = _regional_harness(monkeypatch, keyless)
    out = await scs.get_regional_prices("Creed", "Aventus", "100ml", Q)
    for (region, price), original in zip(out["regional_prices"].items(), handed):
        assert price is original, region


@pytest.mark.asyncio
async def test_19c_green_pin_regional_prices_strip_removes_only_the_private_key(monkeypatch):
    """GREEN-PHASE PIN (polish, r1 adversary minor 1): the /text/prices strip
    drops ONLY ``_discovery_url``. Every other underscore-prefixed key a raw
    ``_get_price`` dict carries (``_cached``, ``_seed``) ships exactly as base
    ships it — this route's ``_cached`` leak is a recorded follow-up, not this
    unit's to widen. Mutation-checked: X15 (strip every ``_``-prefixed key)
    reddens this; removing the strip entirely reddens test_19."""
    _split_on(monkeypatch)
    row = dict(_DISCOVERY_ONLY_ROW, _cached=True, _seed="tier1_shopping")
    handed = _regional_harness(monkeypatch, row)
    out = await scs.get_regional_prices("Creed", "Aventus", "100ml", Q)
    regional = out["regional_prices"]
    assert regional and len(regional) == len(handed)
    expected = {k: v for k, v in row.items() if k != KEY}
    for region, price in regional.items():
        assert KEY not in price, region
        assert price["_cached"] is True and price["_seed"] == "tier1_shopping", region
        assert price == expected, region
    assert all(h.get(KEY) == GOOGLE for h in handed)   # a copy was stripped
