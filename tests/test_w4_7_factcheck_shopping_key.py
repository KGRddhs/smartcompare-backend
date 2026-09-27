"""W4-7 Part C -- the fact-check reads the shopping rows `_get_price` wrote.

New defect found by the W4-7 measurer (spec Part C) and widened by its
ADVERSARIAL SPEC REVIEW (four wrong-key readers). Bound by the FABLE RULINGS
(R1, R6, R7; 2026-09-26, session 68).

`_get_price` writes `self._shopping_items_cache[full_name]` with its OWN key
(`f"{brand} {name}"` when the variant is already in the name, else
`f"{brand} {name} {variant or ''}"`, stripped). `_fetch_product_data` reads the
cache with the DEDUP'D display identity (`_product_display_identity`) at FOUR
sites: the spec cross-validation (`cross_validate_specs_with_shopping`), the
retailer ratings (`collect_retailer_ratings` -> the sentiment verdict), the
verified-rating cache LOOKUP (`_get_verified_rating`; `full_name` stays the rating
query string) and the price cross-check (`verify_price`). On every
brand-repeating / variant-in-name / brand-casing / vision+variant shape the keys
differ, the fact-check sees ZERO rows and certifies the price (`price_verified
True, deviation None`), and #106 is inert there.

Flag ENABLE_FACTCHECK_SHOPPING_KEY (default OFF, read PER CALL). Reader
`scoring_service.factcheck_shopping_key_enabled()`. Under the flag all four
readers use `_shopping_cache_key(brand, name, variant)`, a module helper in
structured_comparison_service that `_get_price` itself calls (UNFLAGGED refactor,
byte-identical string -- pinned over the 13 measured shapes). The
`_price_fallback_on_miss` key drift on the PRICE path is OUT of scope (follow-up
W4-7d, R6).

Test kinds: RED fails at HEAD 15e1fb89 on an assertion naming the absent
behaviour; PIN green at HEAD; KILL = the named killer of a mutation. New symbols
are resolved INSIDE test bodies.
"""
from __future__ import annotations

import inspect
import ipaddress
import socket
from unittest.mock import AsyncMock, patch

import pytest

FLAG = "ENABLE_FACTCHECK_SHOPPING_KEY"
CURRENCY = "ENABLE_FACTCHECK_CURRENCY_NORMALIZATION"
HONEST = "ENABLE_FACTCHECK_HONEST_ABSENCE"

_CLEARED_ENV = (
    "ENABLE_RELIABILITY_UNCHECKED_ABSENCE", "ENABLE_CONFIDENCE_SINGLE_COMPUTATION",
    "ENABLE_FACTCHECK_SHOPPING_KEY", "ENABLE_CONFIDENCE_FACTCHECK_WIRING",
    "ENABLE_FACTCHECK_CURRENCY_NORMALIZATION", "ENABLE_FACTCHECK_HONEST_ABSENCE",
    "ENABLE_SPEC_CONFIDENCE_CACHE", "ENABLE_CITATION_RUBRIC_V2", "ENABLE_BUNDLE_C_SCORING",
    "ENABLE_MISSING_DIM_RENORM", "ENABLE_SPEC_FIELD_NORM", "ENABLE_PRESCORING_SHOWABLE_GUARD",
    "ENABLE_REGION_CURRENCY_GUARD", "ENABLE_HONEST_PARTIAL_SCORING",
)


# ---------------------------------------------------------------------------
# autouse: zero network (socket + curl_cffi.requests.get) + flag reset
# ---------------------------------------------------------------------------
_REAL_CONNECT = socket.socket.connect
_REAL_CONNECT_EX = socket.socket.connect_ex
_REAL_GETADDRINFO = socket.getaddrinfo


def _is_loopback_host(host):
    if isinstance(host, bytes):
        host = host.decode("ascii", "replace")
    if host in (None, "", "localhost"):
        return True
    try:
        return ipaddress.ip_address(str(host).split("%")[0]).is_loopback
    except ValueError:
        return False


@pytest.fixture(autouse=True)
def _zero_network(monkeypatch):
    """Every test here is FREE: block any non-loopback connect / getaddrinfo and
    any curl_cffi GET; fail the node on an attempt even if swallowed."""
    attempts = []

    def _blocked(kind, target):
        attempts.append((kind, repr(target)))
        return OSError("zero-network guard: %s %r blocked" % (kind, target))

    def guarded_connect(self, address):
        if isinstance(address, tuple) and not _is_loopback_host(address[0]):
            raise _blocked("connect", address)
        return _REAL_CONNECT(self, address)

    def guarded_connect_ex(self, address):
        if isinstance(address, tuple) and not _is_loopback_host(address[0]):
            raise _blocked("connect_ex", address)
        return _REAL_CONNECT_EX(self, address)

    def guarded_getaddrinfo(host, *args, **kwargs):
        if not _is_loopback_host(host):
            raise _blocked("getaddrinfo", host)
        return _REAL_GETADDRINFO(host, *args, **kwargs)

    def guarded_curl_get(url, *args, **kwargs):
        raise _blocked("curl_cffi.requests.get", url)

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", guarded_connect_ex)
    monkeypatch.setattr(socket, "getaddrinfo", guarded_getaddrinfo)
    try:
        import curl_cffi.requests as _curl_requests
    except ImportError:  # pragma: no cover
        _curl_requests = None
    if _curl_requests is not None:
        monkeypatch.setattr(_curl_requests, "get", guarded_curl_get)
    yield
    assert not attempts, "zero-network guard: network attempted: %r" % (attempts,)


@pytest.fixture(autouse=True)
def _env_default_off(monkeypatch):
    """Every fact-check / confidence flag unset; the exact gate at its shipped ON."""
    for name in _CLEARED_ENV:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "true")
    yield


# ---------------------------------------------------------------------------
# the 13 measured name shapes (brand, name, variant, vision) -> (get_price key,
# today's _product_display_identity full_name)
# ---------------------------------------------------------------------------
SHAPES13 = [
    (("Tom Ford", "Oud Wood", "100ml", False), "Tom Ford Oud Wood 100ml", "Tom Ford Oud Wood 100ml"),
    (("Apple", "iPhone 15", None, False), "Apple iPhone 15", "Apple iPhone 15"),
    (("Tom Ford", "Tom Ford Oud Wood", "100ml", False), "Tom Ford Tom Ford Oud Wood 100ml",
     "Tom Ford Oud Wood 100ml"),
    (("Samsung", "Galaxy S24 Ultra", "Ultra", False), "Samsung Galaxy S24 Ultra",
     "Samsung Galaxy S24 Ultra Ultra"),
    (("Apple", "Apple iPhone 15", None, False), "Apple Apple iPhone 15", "Apple iPhone 15"),
    (("NOW Foods", "NOW Foods Vitamin D3 5000 IU", None, False),
     "NOW Foods NOW Foods Vitamin D3 5000 IU", "NOW Foods Vitamin D3 5000 IU"),
    (("Sony", "Sony WH-1000XM5", None, True), "Sony Sony WH-1000XM5", "Sony WH-1000XM5"),
    (("Sony", "WH-1000XM5", None, True), "Sony WH-1000XM5", "Sony WH-1000XM5"),
    (("Sony", "WH-1000XM5", "Black", True), "Sony WH-1000XM5 Black", "Sony WH-1000XM5"),
    (("TOM FORD", "Tom Ford Oud Wood", "100ml", False), "TOM FORD Tom Ford Oud Wood 100ml",
     "Tom Ford Oud Wood 100ml"),
    (("Apple", "iPhone 15", "128GB", False), "Apple iPhone 15 128GB", "Apple iPhone 15 128GB"),
    (("", "iPhone 15", None, False), "iPhone 15", "iPhone 15"),
    (("Samsung", "Galaxy S24 Ultra", "ultra", False), "Samsung Galaxy S24 Ultra",
     "Samsung Galaxy S24 Ultra ultra"),
]
_IDS13 = ["%s|%s|%s|%s" % s[0] for s in SHAPES13]

MISMATCH = [
    ("Tom Ford", "Tom Ford Oud Wood", "100ml", False),
    ("Samsung", "Galaxy S24 Ultra", "Ultra", False),
    ("Apple", "Apple iPhone 15", None, False),
    ("NOW Foods", "NOW Foods Vitamin D3 5000 IU", None, False),
    ("Sony", "Sony WH-1000XM5", None, True),
]
MATCH = [("Tom Ford", "Oud Wood", "100ml", False), ("Apple", "iPhone 15", None, False)]
_IDS_MIS = ["%s|%s|%s|%s" % s for s in MISMATCH]
_IDS_MAT = ["%s|%s|%s|%s" % s for s in MATCH]

# 3 contradicting rows (999 BHD vs a shown 350 BHD -> deviation 65.0), each with
# a retailer rating so collect_retailer_ratings / the sentiment verdict see them.
ROWS = [{"price": "BHD 999.000", "source": "ShopA", "rating": 4.0, "ratingCount": 50, "title": "x"},
        {"price": "BHD 999.000", "source": "ShopB", "rating": 4.1, "ratingCount": 60, "title": "x"},
        {"price": "BHD 999.000", "source": "ShopC", "rating": 4.2, "ratingCount": 70, "title": "x"}]


def _getprice_key(brand, name, variant):
    """Verbatim replica of the `_get_price` cache-key assembly."""
    if variant and variant.lower() in name.lower():
        return f"{brand} {name}".strip()
    return f"{brand} {name} {variant or ''}".strip()


async def _run_fetch(brand, name, variant, vision, *, spy_rating=False):
    """Drive the real `_fetch_product_data` (tiers mocked as in
    tests/test_comparison_response_image_url.py::TestOrchestratorWiring) with the
    cache seeded under the `_get_price` key; spy on the spec cross-validation,
    the retailer ratings and (optionally) the verified-rating cache lookup."""
    import app.services.structured_comparison_service as scs
    service = scs.get_comparison_service()
    try:
        service._shopping_items_cache = {_getprice_key(brand, name, variant): list(ROWS)}
    except (AttributeError, TypeError):  # malformed identity (C10): _get_price never wrote
        service._shopping_items_cache = {}
    cap = {}
    real_cv = scs.cross_validate_specs_with_shopping
    real_cr = scs.collect_retailer_ratings

    def spy_cv(specs, items, *a, **k):
        cap["cv_items"] = len(items or [])
        cap["cv_identity"] = a[0] if a else k.get("product_name")
        return real_cv(specs, items, *a, **k)

    def spy_cr(full_name, cache):
        out = real_cr(full_name, cache)
        cap["cr_len"] = len(out or [])
        return out

    async def spy_gvr(full_name, cache, *a, **k):
        cap["gvr_query"] = full_name
        cap["gvr_rows"] = len((cache or {}).get(full_name, []) or [])
        return {"rating": 4.6, "review_count": 100, "rating_verified": True,
                "rating_source": {"name": "t", "url": None}}

    info = {"brand": brand, "name": name, "variant": variant, "category": "electronics",
            "search_query": (f"{brand} {name}" if vision else f"{brand} {name} {variant or ''}")}
    if vision:
        info["_vision"] = True
    patches = [
        patch.object(service, "_get_specs", AsyncMock(return_value={"display": "6.1",
                                                                    "_search_snippets": []})),
        patch.object(service, "_get_price", AsyncMock(return_value={
            "amount": 350.0, "currency": "BHD", "retailer": "X", "source_method": "local_bhd",
            "estimated": False})),
        patch.object(service, "_get_reviews", AsyncMock(return_value={
            "review_summary": {"overall_sentiment": "positive"}, "average_rating": 4.5})),
        patch.object(scs, "search_web", AsyncMock(return_value={"organic": []})),
        patch.object(scs, "get_product_image_url", AsyncMock(return_value=None)),
        patch.object(scs, "tier2_fill_non_negotiables", AsyncMock(return_value={})),
        patch.object(scs, "tier3_synthesize_non_negotiables", AsyncMock(return_value={})),
        patch.object(scs, "cross_validate_specs_with_shopping", spy_cv),
        patch.object(scs, "collect_retailer_ratings", spy_cr),
    ]
    if spy_rating:
        patches.append(patch.object(scs, "get_verified_rating", spy_gvr))
    else:
        patches.append(patch.object(service, "_get_verified_rating", AsyncMock(return_value={
            "rating": 4.6, "review_count": 100, "rating_verified": True,
            "rating_source": {"name": "t", "url": None}})))
    try:
        for p in patches:
            p.start()
        res = await service._fetch_product_data(info, region="bahrain", include_specs=True,
                                                include_reviews=True, nocache=True)
    finally:
        for p in reversed(patches):
            p.stop()
        service._shopping_items_cache = {}
    fc = res.get("fact_check") or {}
    cap.update(pv=fc.get("price_verified"), dev=fc.get("price_deviation_pct"),
               rsc=fc.get("review_sentiment_consistent"), full_name=res.get("full_name"),
               listing_count=res.get("_shopping_listing_count", "<absent>"))
    return cap


# ---------------------------------------------------------------------------
# C1 / C2 / C3 -- the price cross-check
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
@pytest.mark.parametrize("brand,name,variant,vision", MISMATCH, ids=_IDS_MIS)
async def test_c1_fact_check_reads_the_key_get_price_wrote(monkeypatch, brand, name, variant, vision):
    """RED -- flag ON, mismatching shapes (brand-repeating / variant-in-name /
    vision brand-repeating): the price cross-check sees the 3 contradicting rows ->
    price_verified False, price_deviation_pct 65.0. HEAD: True, None (zero rows ->
    the fabricated certification). Kills M-C2 (helper drops the variant-in-name
    branch: the Samsung row)."""
    monkeypatch.setenv(FLAG, "true")
    c = await _run_fetch(brand, name, variant, vision)
    assert (c["pv"], c["dev"]) == (False, 65.0), (
        "ABSENT BEHAVIOUR: the fact-check still reads a key _get_price never wrote "
        "for %s / %s / %s: price_verified %r, deviation %r" % (brand, name, variant, c["pv"], c["dev"]))


@pytest.mark.asyncio
@pytest.mark.parametrize("state", ["unset", "on"])
@pytest.mark.parametrize("brand,name,variant,vision", MATCH, ids=_IDS_MAT)
async def test_c2_matching_shapes_unchanged(monkeypatch, brand, name, variant, vision, state):
    """PIN -- shapes whose keys already agree: price_verified False, deviation 65.0,
    sentiment True, the spec cross-validation sees 3 rows; flag unset and ON."""
    if state == "on":
        monkeypatch.setenv(FLAG, "true")
    c = await _run_fetch(brand, name, variant, vision)
    assert (c["pv"], c["dev"], c["rsc"], c["cv_items"], c["cr_len"]) == (False, 65.0, True, 3, 3)


@pytest.mark.asyncio
@pytest.mark.parametrize("honest", [False, True])
@pytest.mark.parametrize("brand,name,variant,vision", MISMATCH, ids=_IDS_MIS)
async def test_c3_flag_off_keeps_todays_read(monkeypatch, brand, name, variant, vision, honest):
    """PIN / KILL -- flag unset, mismatching shapes: today's read -> True, None;
    with ENABLE_FACTCHECK_HONEST_ABSENCE -> None, None. Kills M-C3 (reader forced
    True)."""
    if honest:
        monkeypatch.setenv(HONEST, "true")
    c = await _run_fetch(brand, name, variant, vision)
    assert (c["pv"], c["dev"]) == ((None, None) if honest else (True, None))


@pytest.mark.asyncio
@pytest.mark.parametrize("brand,name,variant,vision", MISMATCH[:3], ids=_IDS_MIS[:3])
async def test_c1b_composes_with_currency_normalization(monkeypatch, brand, name, variant, vision):
    """RED -- flag ON + #106 ON: the BHD rows are now visible to the currency-aware
    median -> price_verified False, deviation 65.0. HEAD (#106 ON alone is inert on
    these shapes): True, None."""
    monkeypatch.setenv(FLAG, "true")
    monkeypatch.setenv(CURRENCY, "true")
    c = await _run_fetch(brand, name, variant, vision)
    assert (c["pv"], c["dev"]) == (False, 65.0), (
        "ABSENT BEHAVIOUR: #106 still inert on %s / %s: %r" % (brand, name, (c["pv"], c["dev"])))


# ---------------------------------------------------------------------------
# C4 -- the helper IS the _get_price key (13 shapes) + _get_price calls it
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("shape,key,display", SHAPES13, ids=_IDS13)
def test_c4_cache_key_helper_is_the_get_price_key(shape, key, display):
    """RED -- `structured_comparison_service._shopping_cache_key(brand, name,
    variant)` returns the byte-identical `_get_price` key on all 13 measured
    shapes (incl. vision+variant, brand casing, lower-case variant in name).
    HEAD: the helper does not exist. Kills M-C2 (drop the variant-in-name branch)."""
    import app.services.structured_comparison_service as scs
    fn = getattr(scs, "_shopping_cache_key", None)
    assert fn is not None, "ABSENT BEHAVIOUR: _shopping_cache_key() does not exist"
    brand, name, variant, _vision = shape
    assert fn(brand, name, variant) == key == _getprice_key(brand, name, variant)


def test_c4b_get_price_builds_its_key_through_the_helper():
    """RED -- the UNFLAGGED C.1 refactor: `_get_price` assembles its cache key by
    calling `_shopping_cache_key(brand, name, variant)` (one expression, never a
    second copy). HEAD: the inline `if variant and variant.lower() in
    name.lower():` assembly."""
    import app.services.structured_comparison_service as scs
    src = inspect.getsource(scs.StructuredComparisonService._get_price)
    assert "full_name = _shopping_cache_key(brand, name, variant)" in src, (
        "ABSENT BEHAVIOUR: _get_price does not build its cache key via _shopping_cache_key")
    assert "if variant and variant.lower() in name.lower():" not in src


_PAD_SHAPES = [
    (("", "Galaxy S24 Ultra", "Ultra"), "Galaxy S24 Ultra"),
    (("Samsung", "Galaxy S24 Ultra ", "Ultra"), "Samsung Galaxy S24 Ultra"),
    (("", "iPhone 15 ", None), "iPhone 15"),
]


@pytest.mark.parametrize("shape,key", _PAD_SHAPES, ids=["%s|%s|%s" % s[0] for s in _PAD_SHAPES])
def test_c4d_cache_key_helper_strips_both_branches(shape, key):
    """PIN / KILL (FIXER) -- the helper strips on BOTH branches exactly like the
    15e1fb89 inline assembly: an empty brand or a padded name with the variant
    already in the name keys without the stray space. Kills N10 (the first
    branch's `.strip()` dropped -> " Galaxy S24 Ultra")."""
    import app.services.structured_comparison_service as scs
    assert scs._shopping_cache_key(*shape) == key == _getprice_key(*shape)


@pytest.mark.parametrize("shape,key,display", SHAPES13, ids=_IDS13)
def test_c4c_display_identity_drift_table(shape, key, display):
    """PIN -- today's `_product_display_identity` full_name on the 13 shapes (8
    disagree with the `_get_price` key). Part C must NOT touch the display identity
    or `result["full_name"]`."""
    from app.services.structured_comparison_service import _product_display_identity
    brand, name, variant, vision = shape
    sq = f"{brand} {name}" if vision else f"{brand} {name} {variant or ''}"
    full, _ = _product_display_identity(brand, name, variant, sq, vision)
    assert full == display
    assert (full == key) == (display == key)


# ---------------------------------------------------------------------------
# C5 -- the spec cross-validation reads the same key
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
@pytest.mark.parametrize("brand,name,variant,vision", MISMATCH, ids=_IDS_MIS)
async def test_c5_spec_cross_validation_reads_the_same_key(monkeypatch, brand, name, variant, vision):
    """RED -- flag ON: `cross_validate_specs_with_shopping` receives the 3 seeded
    rows and its identity argument is still the result full_name (unchanged).
    HEAD: 0 rows. Kills M-C1 (only the price reader switched)."""
    monkeypatch.setenv(FLAG, "true")
    c = await _run_fetch(brand, name, variant, vision)
    assert c["cv_items"] == 3 and c["cv_identity"] == c["full_name"], (
        "ABSENT BEHAVIOUR: the spec cross-validation sees %r rows (identity %r, full_name %r)"
        % (c["cv_items"], c["cv_identity"], c["full_name"]))


@pytest.mark.asyncio
@pytest.mark.parametrize("brand,name,variant,vision", MISMATCH, ids=_IDS_MIS)
async def test_c5b_flag_off_spec_cross_validation_today(brand, name, variant, vision):
    """PIN / KILL -- flag unset: today's read, 0 rows, identity = full_name.
    Kills M-C3."""
    c = await _run_fetch(brand, name, variant, vision)
    assert (c["cv_items"], c["cv_identity"]) == (0, c["full_name"])


# ---------------------------------------------------------------------------
# C6 -- reader
# ---------------------------------------------------------------------------
def test_c6_reader_truth_table_and_per_call(monkeypatch):
    """RED -- true/TRUE/" true "/1/yes/on -> True; false/""/0/no/unset -> False;
    flip between two calls honoured."""
    from app.services import scoring_service
    fn = getattr(scoring_service, "factcheck_shopping_key_enabled", None)
    assert fn is not None, (
        "ABSENT BEHAVIOUR: scoring_service.factcheck_shopping_key_enabled() does not exist")
    for v in ("true", "TRUE", " true ", "1", "yes", "on"):
        monkeypatch.setenv(FLAG, v)
        assert fn() is True, v
    for v in ("false", "", "0", "no"):
        monkeypatch.setenv(FLAG, v)
        assert fn() is False, v
    monkeypatch.delenv(FLAG, raising=False)
    assert fn() is False
    monkeypatch.setenv(FLAG, "true")
    assert fn() is True


# ---------------------------------------------------------------------------
# C7 -- the retailer ratings / sentiment verdict (R6)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
@pytest.mark.parametrize("brand,name,variant,vision", MISMATCH, ids=_IDS_MIS)
async def test_c7_sentiment_reads_the_get_price_key(monkeypatch, brand, name, variant, vision):
    """RED -- flag ON: `collect_retailer_ratings` sees the 3 rated rows and
    `fact_check.review_sentiment_consistent` is True (as on the matching shapes).
    HEAD: 0 rows, None -- which also starves Part A's +0.05 / -0.1 modifier.
    Kills M-C4 (the price + spec readers switched but not collect_retailer_ratings)."""
    monkeypatch.setenv(FLAG, "true")
    c = await _run_fetch(brand, name, variant, vision)
    assert (c["cr_len"], c["rsc"]) == (3, True), (
        "ABSENT BEHAVIOUR: retailer ratings read the wrong key for %s / %s: rows %r, "
        "sentiment %r" % (brand, name, c["cr_len"], c["rsc"]))


@pytest.mark.asyncio
@pytest.mark.parametrize("brand,name,variant,vision", MISMATCH, ids=_IDS_MIS)
async def test_c7b_flag_off_sentiment_today(brand, name, variant, vision):
    """PIN / KILL -- flag unset: 0 retailer-rating rows, sentiment None. Kills M-C3."""
    c = await _run_fetch(brand, name, variant, vision)
    assert (c["cr_len"], c["rsc"]) == (0, None)


# ---------------------------------------------------------------------------
# C8 -- the verified-rating cache LOOKUP (R6: full_name stays the query string)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
@pytest.mark.parametrize("brand,name,variant,vision", MISMATCH, ids=_IDS_MIS)
async def test_c8_verified_rating_lookup_reads_the_get_price_key(monkeypatch, brand, name, variant, vision):
    """RED -- flag ON: `get_verified_rating` (via `_get_verified_rating`) finds the 3
    seeded rows under the rating query string, and that query string is still the
    result full_name. HEAD: 0 rows. Kills M-C5 (the :5557 lookup left on
    full_name)."""
    monkeypatch.setenv(FLAG, "true")
    c = await _run_fetch(brand, name, variant, vision, spy_rating=True)
    assert c.get("gvr_rows") == 3 and c.get("gvr_query") == c["full_name"], (
        "ABSENT BEHAVIOUR: the verified-rating lookup sees %r rows (query %r, full_name %r)"
        % (c.get("gvr_rows"), c.get("gvr_query"), c["full_name"]))


@pytest.mark.asyncio
@pytest.mark.parametrize("brand,name,variant,vision", MISMATCH[:2] + MATCH, ids=_IDS_MIS[:2] + _IDS_MAT)
async def test_c8b_flag_off_verified_rating_today(brand, name, variant, vision):
    """PIN -- flag unset: the lookup reads `full_name` (0 rows on mismatching shapes,
    3 on matching ones), query string = full_name."""
    c = await _run_fetch(brand, name, variant, vision, spy_rating=True)
    want = 3 if (brand, name, variant, vision) in MATCH else 0
    assert (c.get("gvr_rows"), c.get("gvr_query")) == (want, c["full_name"])


# ---------------------------------------------------------------------------
# C9 -- the R15 cache-view kwarg: the flag-OFF call shape and the kwarg default
# (added by the GREEN phase, red-gate ruling R15; kills M-R15a / M-R15b)
# ---------------------------------------------------------------------------
def _record_verified_rating_calls(monkeypatch):
    """Wrap the real `StructuredComparisonService._get_verified_rating` (the
    spy_rating harness leaves the method itself unpatched) and record the exact
    positional/keyword shape of every call."""
    import app.services.structured_comparison_service as scs
    real = scs.StructuredComparisonService._get_verified_rating
    calls = []

    async def recorder(self, *args, **kwargs):
        calls.append((args, dict(kwargs)))
        return await real(self, *args, **kwargs)

    monkeypatch.setattr(scs.StructuredComparisonService, "_get_verified_rating", recorder)
    return calls


@pytest.mark.asyncio
@pytest.mark.parametrize("brand,name,variant,vision", MISMATCH[:2] + MATCH, ids=_IDS_MIS[:2] + _IDS_MAT)
async def test_c9_flag_off_verified_rating_call_shape_is_todays(monkeypatch, brand, name, variant, vision):
    """PIN / KILL (R15) -- flag unset: `_get_verified_rating` is called exactly as at
    15e1fb89, `(full_name,)` positional and NO keyword (never a cache_view=)."""
    calls = _record_verified_rating_calls(monkeypatch)
    c = await _run_fetch(brand, name, variant, vision, spy_rating=True)
    assert calls == [((c["full_name"],), {})], calls


@pytest.mark.asyncio
@pytest.mark.parametrize("brand,name,variant,vision", MISMATCH[:2], ids=_IDS_MIS[:2])
async def test_c9_flag_on_passes_the_get_price_key_view(monkeypatch, brand, name, variant, vision):
    """RED at 15e1fb89 (R15) -- flag ON: the call keeps full_name as the query string and passes
    `cache_view={full_name: <the rows under the _get_price key>}`."""
    monkeypatch.setenv(FLAG, "true")
    calls = _record_verified_rating_calls(monkeypatch)
    c = await _run_fetch(brand, name, variant, vision, spy_rating=True)
    assert len(calls) == 1
    args, kwargs = calls[0]
    assert args == (c["full_name"],)
    assert set(kwargs) == {"cache_view"}
    assert list(kwargs["cache_view"]) == [c["full_name"]]
    assert len(kwargs["cache_view"][c["full_name"]]) == 3


def test_c9_cache_view_kwarg_defaults_to_none():
    """RED at 15e1fb89 / KILL (R15) -- `_get_verified_rating(self, full_name, cache_view=None)`: the
    default is None (= today's `self._shopping_items_cache`)."""
    import app.services.structured_comparison_service as scs
    sig = inspect.signature(scs.StructuredComparisonService._get_verified_rating)
    assert list(sig.parameters) == ["self", "full_name", "cache_view"]
    assert sig.parameters["cache_view"].default is None


@pytest.mark.asyncio
@pytest.mark.parametrize("view", ["none", "empty", "rows"])
async def test_c9b_cache_view_none_means_todays_cache_any_dict_is_the_view(monkeypatch, view):
    """PIN / KILL (R15 semantics, fix round 2) -- `cache_view=None` reads today's
    `self._shopping_items_cache`; ANY dict, the empty one included, is the lookup
    passed to rating_service (an empty view means 'no rows under the _get_price key',
    never a fall-back to the whole cache). Kills X19 (`cache_view or cache`)."""
    import app.services.structured_comparison_service as scs
    seen = []

    async def _spy(full_name, cache, **_k):
        seen.append(cache)
        return {"rating": None}

    monkeypatch.setattr(scs, "get_verified_rating", _spy)
    service = scs.get_comparison_service()
    service._shopping_items_cache = {"Tom Ford Oud Wood 100ml": [{"title": "t"}]}
    arg = {"none": None, "empty": {}, "rows": {"X": [{"title": "r"}]}}[view]
    try:
        if arg is None:
            await service._get_verified_rating("X")
        else:
            await service._get_verified_rating("X", cache_view=arg)
        want = service._shopping_items_cache if arg is None else arg
        assert len(seen) == 1 and seen[0] is want, (view, seen)
    finally:
        service._shopping_items_cache = {}


# ---------------------------------------------------------------------------
# C10 -- a malformed identity never newly raises under the flags (FIXER;
# adversary defect: the `_get_price` key expression ran OUTSIDE the Phase-1
# gather's return_exceptions containment)
# ---------------------------------------------------------------------------
_MALFORMED = [("Apple", "iPhone 15", 256, False), ("Samsung", None, "Ultra", False)]


@pytest.mark.asyncio
@pytest.mark.parametrize("flags", ["off", "B", "C", "B+C"])
@pytest.mark.parametrize("brand,name,variant,vision", _MALFORMED,
                         ids=["int-variant", "none-name"])
async def test_c10_malformed_identity_degrades_like_flag_off(monkeypatch, brand, name, variant,
                                                             vision, flags):
    """PIN / KILL -- a truthy non-str variant / a None name with a variant: flag
    OFF `_fetch_product_data` returns a result; under Part B and/or Part C it
    returns the SAME fact-check verdict (the flagged readers fall back to today's
    `full_name` key) and Part B stashes None (R25, fix round 3: `_get_price` raises
    for such an identity, so no pool is captured and the count is unknown, not
    0), never an AttributeError. Kills the raw `_shopping_cache_key(...)` call at
    any flagged site."""
    if "B" in flags:
        monkeypatch.setenv("ENABLE_CONFIDENCE_SINGLE_COMPUTATION", "true")
    if "C" in flags:
        monkeypatch.setenv(FLAG, "true")
    c = await _run_fetch(brand, name, variant, vision)
    assert (c["pv"], c["dev"], c["cv_items"], c["cr_len"]) == (True, None, 0, 0), c
    assert c["listing_count"] == (None if "B" in flags else "<absent>")
