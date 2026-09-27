"""W4-7 Part B -- the pills read ONE computation of the price the user sees.

Findings PO-FACTCHECK-CONFIDENCE-02 (P1) + -06 (P2, the fabricated listing
count). Spec `.qa-s68/specs/W4_7_UNIT_SPEC.md` as corrected by its ADVERSARIAL
SPEC REVIEW and bound by the FABLE RULINGS (R1, R3, R4, R5, R7; 2026-09-26).

Flag ENABLE_CONFIDENCE_SINGLE_COMPUTATION (default OFF, read PER CALL). Reader
`scoring_service.confidence_single_computation_enabled()`.

Ruled design:
  * ONE computation in `build_comparison_response`, AFTER the price-pending
    chokepoint, `compute_confidence` fed per-product COPIES carrying
    `shopping_count = _shopping_listing_count`, `cached =` the REAL cache hit
    (`_compute_cache_observability(...)["cache_hit"]`, R3 -- not `from_cache`);
    emitted verbatim on BOTH surfaces (`overview.confidence` and
    `scoring_v2.confidence_legs` / `confidence_details`).
  * R4 count semantics: `_shopping_listing_count` = the shopping rows under the
    `_get_price` key that survive identity matching for this product (a row the
    real `extract_price_from_shopping` accepts), NOT the raw Serper row count and
    NOT `len(self._shopping_items_cache)` (the product-key count). Stashed in
    `_fetch_product_data` next to the fact-check pass.
  * R4 cap: when any product's SHOWN price is pending (`unavailable` / amount
    None), the price leg is capped at `weak` regardless of the count.
  * R5: `_shopping_listing_count` is popped from every product dict in the
    builder before `result["products"] = product_data` (unconditional pop), so the
    key never reaches the wire.
  * R25: when NO pool was captured for a product this request (a real price-cache
    hit, a partial) the stash is None (UNKNOWN, never 0) and that product enters
    the single computation exactly as the flag-OFF path passes it; 0 is stashed
    only for a captured pool with no identity match.
  * R31a (supersedes R28's "an empty return included"): a pool is CAPTURED iff
    the shopping list returned this request is NON-EMPTY. Every EMPTY pool -- a
    real empty search, a failed / timed-out search (production returns the empty
    `us_fallback` dict, it never raises), the no-key / budget-out `error` shape,
    the supplements synthetic `[]`, the Tier-1 clamp-timeout substitution, a
    cache hit, a partial -- stashes None and the leg equals the flag-OFF leg; a
    count of 0 means rows exist and none matched. Stubs use PRODUCTION shapes
    (`shopping_region: 'us_fallback'` for the GCC region code).
  * R29 / R31b: the check is per product key, never "the cache is empty" (B17),
    and keyed by `_lc_key` (the `_get_price` key), never the display identity
    (B18, a brand-repeating name whose two keys differ).

Test kinds: RED fails at HEAD 15e1fb89 on an assertion naming the absent
behaviour; PIN green at HEAD; KILL = a PIN/RED that is the named killer of a
mutation. New symbols are resolved INSIDE test bodies.
"""
from __future__ import annotations

import copy
import ipaddress
import json
import socket
from unittest.mock import AsyncMock, patch

import pytest

FLAG = "ENABLE_CONFIDENCE_SINGLE_COMPUTATION"
WIRING = "ENABLE_CONFIDENCE_FACTCHECK_WIRING"
W44 = "ENABLE_HONEST_PARTIAL_SCORING"

_CLEARED_ENV = (
    "ENABLE_RELIABILITY_UNCHECKED_ABSENCE", "ENABLE_CONFIDENCE_SINGLE_COMPUTATION",
    "ENABLE_FACTCHECK_SHOPPING_KEY", "ENABLE_CONFIDENCE_FACTCHECK_WIRING",
    "ENABLE_FACTCHECK_CURRENCY_NORMALIZATION", "ENABLE_FACTCHECK_HONEST_ABSENCE",
    "ENABLE_SPEC_CONFIDENCE_CACHE", "ENABLE_CITATION_RUBRIC_V2", "ENABLE_BUNDLE_C_SCORING",
    "ENABLE_MISSING_DIM_RENORM", "ENABLE_SPEC_FIELD_NORM", "ENABLE_PRESCORING_SHOWABLE_GUARD",
    "ENABLE_REGION_CURRENCY_GUARD", "ENABLE_HONEST_PARTIAL_SCORING",
    "ENABLE_SINGLE_VERDICT_MARGIN", "ENABLE_SMART_PICK_VERDICT_CAPTION",
    "ENABLE_VALUE_DIM_PARTIAL_SIGNAL", "ENABLE_TIE_IS_NOT_MISSING",
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
    """Every flag the confidence / scoring / builder surface reads is unset, the
    exact gate at its shipped ON, and the process-cached bundle-C flag reset."""
    for name in _CLEARED_ENV:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "true")
    from app.services import scoring_service
    monkeypatch.setattr(scoring_service, "_BUNDLE_C_SCORING_FLAG", None, raising=False)
    yield


# ---------------------------------------------------------------------------
# builder fixtures (the Sony/Bose shapes of test_prescoring_showable_guard.py)
# ---------------------------------------------------------------------------
GOOG0 = "https://www.google.com/search?ibp=oshop&q=Sony+WH-1000XM5"
GOOG1 = "https://www.google.com/search?ibp=oshop&q=Bose+QC+Ultra"
PDP0 = "https://bolo.bh/products/sony-wh-1000xm5"
PDP1 = "https://bolo.bh/products/bose-qc-ultra"
E0 = {"battery_life": "30 hours", "ram": "8 GB", "storage": "256 GB",
      "screen_size": "6.1 inch", "weight": "250 g"}
E1 = {"battery_life": "24 hours", "ram": "6 GB", "storage": "128 GB",
      "screen_size": "6.1 inch", "weight": "254 g"}
SONY = "Sony WH-1000XM5"
BOSE = "Bose QuietComfort Ultra"


def _fc(u=8, pv=False, dev=None):
    return {"specs_verified": 0, "specs_likely": 0, "specs_unverified": u,
            "specs_flagged": 0, "price_verified": pv, "price_deviation_pct": dev,
            "review_sentiment_consistent": None, "review_rating_deviation": None}


def _mk(name, brand, amount, url, specs, method="local_bhd", count=None, fc=None):
    p = {"name": name, "full_name": name, "brand": brand, "category": "electronics",
         "price": {"amount": amount, "currency": "BHD", "source_method": method,
                   "url": url, "title": name, "in_stock": True, "retailer": "Best Buy"},
         "best_price": amount, "retailer": "Best Buy", "specs": specs,
         "rating": 4.5, "review_count": 1000, "fact_check": dict(fc or _fc())}
    if count is not None:
        p["_shopping_listing_count"] = count
    return p


def _shape(name, counts=(None, None), fc=None):
    c0, c1 = counts
    if name == "pdp_local_bhd":
        return [_mk(SONY, "Sony", 100.0, PDP0, E0, count=c0, fc=fc),
                _mk(BOSE, "Bose", 200.0, PDP1, E1, count=c1, fc=fc)]
    if name == "pdp_converted_usd":
        return [_mk(SONY, "Sony", 100.0, PDP0, E0, "converted_usd", c0, fc),
                _mk(BOSE, "Bose", 200.0, PDP1, E1, "converted_usd", c1, fc)]
    if name == "pdp_estimated":
        return [_mk(SONY, "Sony", 100.0, PDP0, E0, "estimated", c0, fc),
                _mk(BOSE, "Bose", 200.0, PDP1, E1, "estimated", c1, fc)]
    if name == "google_local_bhd":
        return [_mk(SONY, "Sony", 100.0, GOOG0, E0, count=c0, fc=fc),
                _mk(BOSE, "Bose", 200.0, GOOG1, E1, count=c1, fc=fc)]
    if name == "pdp_and_google_local_bhd":
        return [_mk(SONY, "Sony", 100.0, PDP0, E0, count=c0, fc=fc),
                _mk(BOSE, "Bose", 200.0, GOOG1, E1, count=c1, fc=fc)]
    raise KeyError(name)


SHAPES = ("pdp_converted_usd", "pdp_estimated", "google_local_bhd", "pdp_local_bhd",
          "pdp_and_google_local_bhd")
COUNTS = ((0, 0), (1, 1), (2, 2), (3, 0))

# R4 expected price leg under the flag, per shape and product-0 count.
_NON_TRUST_SHOWN = {0: "weak", 1: "weak", 2: "acceptable", 3: "strong"}
_EXPECTED_ON = {
    "pdp_converted_usd": lambda c: _NON_TRUST_SHOWN[c],
    "pdp_estimated": lambda c: "weak",             # pended (estimate) -> capped
    "google_local_bhd": lambda c: "weak",          # both pended -> capped
    "pdp_local_bhd": lambda c: "strong",           # trust method, shown
    "pdp_and_google_local_bhd": lambda c: "weak",  # one pended -> capped
}
# HEAD scoring_v2 price leg (builder recompute, no counts, cached=False).
_HEAD_V2_PRICE = {"pdp_converted_usd": "weak", "pdp_estimated": "weak",
                  "google_local_bhd": "weak", "pdp_local_bhd": "strong",
                  "pdp_and_google_local_bhd": "strong"}


def _build(pd, *, confidence="caller", from_cache=True, metadata=None, scoring_result="auto"):
    from app.services.response_builder import build_comparison_response
    from app.services.scoring_service import ScoringService
    sr = ScoringService().compute_scores(copy.deepcopy(pd)) if scoring_result == "auto" \
        else scoring_result
    if confidence == "caller":
        confidence = ScoringService().compute_confidence(copy.deepcopy(pd), shopping_count=2,
                                                         cached=True)
    kwargs = dict(product_data=pd, comparison={}, scoring_result=sr, confidence=confidence,
                  from_cache=from_cache, query="q", category_used="electronics",
                  product_names=[SONY, BOSE])
    if metadata is not None:
        kwargs["metadata"] = metadata
    return build_comparison_response(**kwargs), confidence


def _surfaces(resp):
    ov = resp["overview"]["confidence"] or {}
    v2 = resp.get("scoring_v2") or {}
    det = (v2.get("confidence_details") or {}).get("price") or {}
    return {
        "ov_legs": ov.get("legs"), "v2_legs": v2.get("confidence_legs"),
        "ov_count": (ov.get("price") or {}).get("source_count"), "v2_count": det.get("sources_count"),
        "ov_fresh": (ov.get("price") or {}).get("freshness"), "v2_fresh": det.get("freshness"),
    }


# ---------------------------------------------------------------------------
# B1 / B2 / B3 / B3b / B4 -- the builder
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("counts", COUNTS, ids=["%d-%d" % c for c in COUNTS])
@pytest.mark.parametrize("shape", SHAPES)
def test_b1_one_computation_on_both_surfaces(monkeypatch, shape, counts):
    """RED -- flag ON: scoring_v2.confidence_legs == overview.confidence.legs, and
    the price detail's count and freshness agree. HEAD: every row differs in
    source_count (2 vs 0) and freshness (cached vs live); converted_usd /
    estimated / google x2 also differ in the leg (acceptable/acceptable/strong vs
    weak). Kills M-B1 (recompute in _build_scoring_v2 instead of precomputed)."""
    monkeypatch.setenv(FLAG, "true")
    resp, _ = _build(_shape(shape, counts))
    s = _surfaces(resp)
    assert s["ov_legs"] == s["v2_legs"] and s["ov_count"] == s["v2_count"] \
        and s["ov_fresh"] == s["v2_fresh"], (
            "ABSENT BEHAVIOUR: two confidence computations still ship on %s %s: %r"
            % (shape, counts, s))


def test_b2_price_leg_reads_the_shown_price(monkeypatch):
    """RED -- google x2 local_bhd (both prices pended by the chokepoint), counts
    (0, 0), flag ON: BOTH surfaces price == "weak". HEAD: overview "strong" (the
    orchestrator dict saw the pre-pend price). Kills M-B2 (thread the
    orchestrator's dict) and M-B3 (compute BEFORE the chokepoint)."""
    monkeypatch.setenv(FLAG, "true")
    resp, _ = _build(_shape("google_local_bhd", (0, 0)))
    s = _surfaces(resp)
    assert s["ov_legs"]["price"] == "weak" and s["v2_legs"]["price"] == "weak", (
        "ABSENT BEHAVIOUR: the price pill does not read the SHOWN (pending) price: %r" % (s,))


@pytest.mark.parametrize("counts", COUNTS, ids=["%d-%d" % c for c in COUNTS])
@pytest.mark.parametrize("shape", SHAPES)
def test_b3_real_listing_counts_drive_the_leg(monkeypatch, shape, counts):
    """RED -- flag ON, per-product `_shopping_listing_count`: converted_usd (shown)
    (0,0)->weak/0, (1,1)->weak/1, (2,2)->acceptable/2, (3,0)->strong/3; local_bhd PDP
    strong at every count; every shape with a pending shown price (estimated,
    google x2, PDP+google) capped at weak at every count (R4); sources_count =
    product 0's count on both surfaces. HEAD scoring_v2: weak/0 (non-trust) and
    strong/0 (trust), overview source_count 2."""
    monkeypatch.setenv(FLAG, "true")
    resp, _ = _build(_shape(shape, counts))
    s = _surfaces(resp)
    want = _EXPECTED_ON[shape](counts[0])
    assert (s["ov_legs"]["price"], s["v2_legs"]["price"], s["ov_count"], s["v2_count"]) == (
        want, want, counts[0], counts[0]), (
            "ABSENT BEHAVIOUR: the price leg is not driven by the real listing count "
            "(want %s/%d on both surfaces): %r" % (want, counts[0], s))


@pytest.mark.parametrize("shape", ["google_local_bhd", "pdp_and_google_local_bhd", "pdp_estimated"])
def test_b3b_pending_shown_price_caps_the_leg_at_weak(monkeypatch, shape):
    """RED / KILL -- R4 cap: with >= 3 identity-matched listings per product
    (3, 3) the price leg is still `weak` on both surfaces whenever a SHOWN price is
    pending. HEAD: overview strong / acceptable (orchestrator dict). Kills M-B9
    (no pending cap: the section-5a rule makes it strong at >= 3)."""
    monkeypatch.setenv(FLAG, "true")
    resp, _ = _build(_shape(shape, (3, 3)))
    s = _surfaces(resp)
    assert s["ov_legs"]["price"] == "weak" and s["v2_legs"]["price"] == "weak", (
        "ABSENT BEHAVIOUR: price pill reads above Low beside a pending price: %r" % (s,))


def test_b3c_any_pending_side_caps_the_converted_shape(monkeypatch):
    """RED at 15e1fb89 / KILL (red-gate ruling R12, both directions; added by the
    GREEN phase) --
    flag ON, the converted_usd shape at counts (2, 2): with BOTH prices shown the
    leg reads `acceptable` on both surfaces; the same shape with ONE side's price
    pending (product 1 on a google search link, pended by the chokepoint) reads
    `weak` on both surfaces -- the cap fires when ANY shown price is pending, not
    only when every one is. Kills M-R12 (cap only when ALL prices are pending)."""
    monkeypatch.setenv(FLAG, "true")
    both_shown, _ = _build(_shape("pdp_converted_usd", (2, 2)))
    s_shown = _surfaces(both_shown)
    assert (s_shown["ov_legs"]["price"], s_shown["v2_legs"]["price"]) == ("acceptable", "acceptable")
    mixed = [_mk(SONY, "Sony", 100.0, PDP0, E0, "converted_usd", 2),
             _mk(BOSE, "Bose", 200.0, GOOG1, E1, "converted_usd", 2)]
    resp, _ = _build(mixed)
    assert resp["products"][0]["price"].get("amount") == 100.0
    assert resp["products"][1]["price"].get("amount") is None  # the pended side
    s = _surfaces(resp)
    assert (s["ov_legs"]["price"], s["v2_legs"]["price"]) == ("weak", "weak"), s


@pytest.mark.parametrize("shape", ["pdp_and_google_local_bhd", "google_local_bhd"])
def test_b3d_cap_recomputes_overall_from_the_capped_legs(monkeypatch, shape):
    """PIN / KILL (red-gate ruling R12, added by the FIXER) -- when the R4 cap
    demotes the price leg, `overall` (persisted as overview.confidence.overall) is
    recomputed from the CAPPED legs with compute_confidence's own thresholds:
    {weak, strong, strong} -> "medium" (the uncapped legs read "high"). Kills N1
    (no overall recompute: "high" beside a pending price)."""
    monkeypatch.setenv(FLAG, "true")
    resp, _ = _build(_shape(shape, (3, 3)))
    ov = resp["overview"]["confidence"]
    assert ov["legs"] == {"price": "weak", "reviews": "strong", "specs": "strong"}, ov
    assert ov["overall"] == "medium", ov


def test_b3d_cap_overall_single_strong_leg_reads_low(monkeypatch):
    """PIN / KILL (R12, FIXER) -- the same cap with the specs leg weak (no fact-check
    fields: citation_count 0): the capped legs {weak, strong, weak} carry ONE strong
    leg -> overall "low". Kills N17 (the "medium" threshold `>= 2` -> `>= 1`) and N1
    (uncapped {strong, strong, weak} -> "medium")."""
    monkeypatch.setenv(FLAG, "true")
    resp, _ = _build(_shape("pdp_and_google_local_bhd", (3, 3), fc=_fc(u=0)))
    ov = resp["overview"]["confidence"]
    assert ov["legs"] == {"price": "weak", "reviews": "strong", "specs": "weak"}, ov
    assert ov["overall"] == "low", ov


def test_b3e_amount_none_price_caps_when_the_chokepoint_degrades(monkeypatch):
    """PIN / KILL (R4/R12, FIXER) -- the cap reads a price dict with `amount None`
    as pending even when it carries no `unavailable` marker: with the price-pending
    chokepoint degraded (its region lookup raises -> the whole pass is skipped and
    logged), product 1 ships `{amount: None, local_bhd}` un-pended and the price
    leg is still `weak` on both surfaces. Kills N2 (drop the `amount is None`
    clause: the trust method makes it `strong` beside a price-less row)."""
    from app.services import exchange_rate_service
    from app.services.response_builder import build_comparison_response
    from app.services.scoring_service import ScoringService
    monkeypatch.setenv(FLAG, "true")
    pd = _shape("pdp_local_bhd", (3, 3))
    pd[1]["price"]["amount"] = None
    pd[1]["best_price"] = None
    sr = ScoringService().compute_scores(copy.deepcopy(pd))
    caller = ScoringService().compute_confidence(copy.deepcopy(pd), shopping_count=2, cached=True)

    def _boom(*_a, **_k):
        raise RuntimeError("chokepoint degraded (test)")

    monkeypatch.setattr(exchange_rate_service, "get_region_currency", _boom)
    resp = build_comparison_response(
        product_data=pd, comparison={}, scoring_result=sr, confidence=caller,
        from_cache=True, query="q", category_used="electronics", product_names=[SONY, BOSE])
    p1 = resp["products"][1]["price"]
    assert p1.get("amount") is None and not p1.get("unavailable"), p1  # un-pended
    s = _surfaces(resp)
    assert (s["ov_legs"]["price"], s["v2_legs"]["price"]) == ("weak", "weak"), s


@pytest.mark.parametrize("caller_conf", ["caller", None])
def test_b11_failed_single_computation_degrades_to_the_flag_off_shape(monkeypatch, caller_conf):
    """PIN / KILL (FIXER; adversary defect 'Part B except branch') -- when the single
    computation raises, flag ON degrades to the FLAG-OFF shape: overview ships the
    caller's dict (then {} when there is none) and scoring_v2 recomputes on the
    SHOWN prices itself -- the caller's pre-pend dict is never threaded into the
    pills. google x2 (both prices pended) with compute_confidence forced to raise:
    scoring_v2 legs equal the flag-OFF legs under the same raise (all weak), never
    the caller's {strong, strong, strong}. Kills N4 (fallback -> {}: overview loses
    the caller's dict) and the pre-fix fallback (caller dict threaded)."""
    from app.services import response_builder

    def _raise(*_a, **_k):
        raise RuntimeError("compute_confidence failed (test)")

    def _run(flag_on):
        if flag_on:
            monkeypatch.setenv(FLAG, "true")
        else:
            monkeypatch.delenv(FLAG, raising=False)
        from app.services.scoring_service import ScoringService
        pd = _shape("google_local_bhd", (3, 3))
        sr = ScoringService().compute_scores(copy.deepcopy(pd))
        caller = (ScoringService().compute_confidence(copy.deepcopy(pd), shopping_count=2,
                                                      cached=True)
                  if caller_conf == "caller" else None)
        with patch.object(response_builder, "compute_confidence", _raise):
            resp = response_builder.build_comparison_response(
                product_data=pd, comparison={}, scoring_result=sr, confidence=caller,
                from_cache=True, query="q", category_used="electronics",
                product_names=[SONY, BOSE])
        return resp, caller

    on, caller = _run(True)
    off, _ = _run(False)
    assert on["overview"]["confidence"] == (caller if caller is not None else {})
    if caller is not None:
        assert caller["legs"] == {"price": "strong", "reviews": "strong", "specs": "strong"}
    assert on["scoring_v2"]["confidence_legs"] == off["scoring_v2"]["confidence_legs"] == {
        "price": "weak", "reviews": "weak", "specs": "weak"}
    assert on["scoring_v2"]["confidence_details"] == off["scoring_v2"]["confidence_details"]


@pytest.mark.parametrize("shape", ["pdp_local_bhd", "pdp_converted_usd"])
@pytest.mark.parametrize("cached", [True, False])
def test_b4_freshness_is_the_real_cache_hit(monkeypatch, cached, shape):
    """RED -- flag ON (R3): a shown price carrying `_cached: True` -> both surfaces
    freshness "cached"; no `_cached` -> "live" even with from_cache=True
    (from_cache means 'cache allowed'). HEAD: scoring_v2 "live" in both, overview
    "cached" in both. Kills M-B4 (cached=from_cache). The converted_usd rows
    (FIXER) kill N14 (`["genuine_from_cache"]`: a cached CONVERTED price is a cache
    hit but not a genuine one, so the mutant reads it `live`)."""
    monkeypatch.setenv(FLAG, "true")
    pd = _shape(shape, (1, 1))
    if cached:
        pd[0]["price"]["_cached"] = True
    resp, _ = _build(pd, from_cache=True)
    s = _surfaces(resp)
    want = "cached" if cached else "live"
    assert s["ov_fresh"] == want and s["v2_fresh"] == want, (
        "ABSENT BEHAVIOUR: freshness is not the real cache hit (want %s): %r" % (want, s))


# ---------------------------------------------------------------------------
# B6 -- flag OFF identical
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("counts", COUNTS, ids=["%d-%d" % c for c in COUNTS])
@pytest.mark.parametrize("shape", SHAPES)
def test_b6_flag_off_identical(shape, counts):
    """PIN / KILL -- flag unset: overview.confidence IS the caller's dict (equal),
    scoring_v2 legs {price <HEAD>, reviews strong, specs strong}, sources_count 0,
    freshness live -- the HEAD values for all 20 shape x count rows. Kills M-B7
    (reader forced True)."""
    resp, caller = _build(_shape(shape, counts))
    s = _surfaces(resp)
    assert resp["overview"]["confidence"] == caller
    assert s["v2_legs"] == {"price": _HEAD_V2_PRICE[shape], "reviews": "strong", "specs": "strong"}
    assert (s["v2_count"], s["v2_fresh"]) == (0, "live")


# ---------------------------------------------------------------------------
# B7 -- the stash never reaches the wire (R5)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("state", ["on", "unset"])
def test_b7_listing_count_never_serialised(monkeypatch, state):
    """RED -- R5: product dicts carrying `_shopping_listing_count` through the real
    builder: `result["products"]`, `overview.products` and the full json.dumps
    carry no `_shopping_listing_count` and no `shopping_count`, flag ON and unset
    (the pop is unconditional). HEAD: `result["products"] = product_data` ships the
    raw dicts -> the key is on the wire. Kills M-B8 (no pop)."""
    if state == "on":
        monkeypatch.setenv(FLAG, "true")
    resp, _ = _build(_shape("pdp_local_bhd", (3, 2)))
    blob = json.dumps(resp, default=str)
    leaked = [i for i, p in enumerate(resp.get("products") or [])
              if "_shopping_listing_count" in p or "shopping_count" in p]
    leaked_ov = [i for i, p in enumerate(resp["overview"].get("products") or [])
                 if "_shopping_listing_count" in p or "shopping_count" in p]
    assert "_shopping_listing_count" not in blob and not leaked and not leaked_ov, (
        "ABSENT BEHAVIOUR: _shopping_listing_count reaches the wire (products %r, "
        "overview.products %r, in json: %s)" % (leaked, leaked_ov, "_shopping_listing_count" in blob))


# ---------------------------------------------------------------------------
# B8 -- reader
# ---------------------------------------------------------------------------
def test_b8_reader_truth_table_and_per_call(monkeypatch):
    """RED -- true/TRUE/" true "/1/yes/on -> True; false/""/0/no/unset -> False;
    flip between two calls honoured. Kills a reader without .strip().lower()."""
    from app.services import scoring_service
    fn = getattr(scoring_service, "confidence_single_computation_enabled", None)
    assert fn is not None, (
        "ABSENT BEHAVIOUR: scoring_service.confidence_single_computation_enabled() does not exist")
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
# B9 -- partial build (split PIN / RED halves per R7)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("w44", [None, "true"])
def test_b9_partial_build_never_raises(monkeypatch, w44):
    """PIN -- flag ON, metadata={"partial": True}, confidence={}, scoring_result={},
    W4-4's flag unset and "true": the builder never raises."""
    monkeypatch.setenv(FLAG, "true")
    if w44:
        monkeypatch.setenv(W44, w44)
    resp, _ = _build(_shape("pdp_local_bhd"), confidence={}, metadata={"partial": True},
                     scoring_result={})
    assert isinstance(resp, dict) and "overview" in resp


@pytest.mark.parametrize("w44", [None, "true"])
def test_b9_partial_build_ships_three_legs(monkeypatch, w44):
    """RED -- the same partial build: overview.confidence["legs"] carries price /
    reviews / specs (the builder's single computation replaces the caller's {}).
    HEAD: overview.confidence == {} (the caller's dict verbatim). A partial never
    reaches the orchestrator stash -> count 0 under the flag (stated in the PR)."""
    monkeypatch.setenv(FLAG, "true")
    if w44:
        monkeypatch.setenv(W44, w44)
    resp, _ = _build(_shape("pdp_local_bhd"), confidence={}, metadata={"partial": True},
                     scoring_result={})
    legs = (resp["overview"]["confidence"] or {}).get("legs")
    assert isinstance(legs, dict) and set(legs) == {"price", "reviews", "specs"}, (
        "ABSENT BEHAVIOUR: partial build ships overview.confidence %r"
        % (resp["overview"]["confidence"],))


# ---------------------------------------------------------------------------
# B10 -- composition with #109
# ---------------------------------------------------------------------------
def test_b10_composes_with_factcheck_wiring(monkeypatch):
    """PIN -- flag ON + #109 ON, warm shape (0/0/8, pv False, deviation 89.8), PDP
    local_bhd, counts (2, 2): both surfaces {price acceptable, reviews strong,
    specs weak} (the #109 demotion), equal. Green at HEAD too."""
    monkeypatch.setenv(FLAG, "true")
    monkeypatch.setenv(WIRING, "true")
    resp, _ = _build(_shape("pdp_local_bhd", (2, 2), fc=_fc(pv=False, dev=89.8)))
    s = _surfaces(resp)
    want = {"price": "acceptable", "reviews": "strong", "specs": "weak"}
    assert s["ov_legs"] == want and s["v2_legs"] == want


# ---------------------------------------------------------------------------
# B5 / B6b -- the orchestrator stash (_fetch_product_data harness)
# ---------------------------------------------------------------------------
# Identity-matched rows for "Tom Ford Oud Wood 100ml" (the real
# extract_price_from_shopping accepts each one alone) and rows it rejects.
MATCHED = [
    {"price": "BHD 999.000", "title": "Tom Ford Oud Wood Eau de Parfum 100ml", "source": "ShopA"},
    {"price": "BHD 989.000", "title": "Tom Ford Oud Wood EDP 100ml Spray", "source": "ShopB"},
    {"price": "BHD 979.000", "title": "Tom Ford Oud Wood Eau de Parfum 100ml Spray", "source": "ShopC"},
]
UNMATCHED = [
    {"price": "BHD 999.000", "title": "Silicone phone case for Galaxy", "source": "ShopD"},
    {"price": "BHD 199.000", "title": "Tom Ford Oud Wood Eau de Parfum 30ml", "source": "ShopE"},
    {"title": "Tom Ford Oud Wood 100ml", "source": "iHerb", "rating": 4.5},
]


def _getprice_key(brand, name, variant):
    """Verbatim replica of the `_get_price` cache-key assembly."""
    if variant and variant.lower() in name.lower():
        return f"{brand} {name}".strip()
    return f"{brand} {name} {variant or ''}".strip()


async def _fetch_on(service, brand, name, variant, category="fragrances", get_price=None,
                    get_price_with_service=None):
    """The real `_fetch_product_data` on `service` (its shopping cache left as
    the caller set it), the sibling tiers mocked."""
    import app.services.structured_comparison_service as scs
    if get_price_with_service is not None:
        async def get_price(*a, **k):
            return await get_price_with_service(service, *a, **k)
    info = {"brand": brand, "name": name, "variant": variant, "category": category,
            "search_query": f"{brand} {name} {variant or ''}"}
    price_mock = (AsyncMock(side_effect=get_price) if get_price is not None else
                  AsyncMock(return_value={"amount": 350.0, "currency": "BHD", "retailer": "X",
                                          "source_method": "local_bhd", "estimated": False}))
    with patch.object(service, "_get_specs", AsyncMock(return_value={"size": "100ml"})), \
         patch.object(service, "_get_price", price_mock), \
         patch.object(service, "_get_reviews", AsyncMock(return_value={"review_summary": {}})), \
         patch.object(service, "_get_verified_rating", AsyncMock(return_value={
             "rating": 4.6, "review_count": 100, "rating_verified": True,
             "rating_source": {"name": "t", "url": None}})), \
         patch.object(scs, "search_web", AsyncMock(return_value={"organic": []})), \
         patch.object(scs, "get_product_image_url", AsyncMock(return_value=None)), \
         patch.object(scs, "tier2_fill_non_negotiables", AsyncMock(return_value={})), \
         patch.object(scs, "tier3_synthesize_non_negotiables", AsyncMock(return_value={})):
        return await service._fetch_product_data(info, region="bahrain", include_specs=True,
                                                 include_reviews=True, nocache=True)


async def _run_fetch(brand, name, variant, rows, category="fragrances", get_price=None,
                     get_price_with_service=None):
    import app.services.structured_comparison_service as scs
    service = scs.get_comparison_service()
    # rows None = no pool in the cache before the fetch (a real price-cache hit
    # writes none; a real `_get_price` run through `get_price_with_service` writes
    # its own)
    service._shopping_items_cache = ({} if rows is None else
                                     {_getprice_key(brand, name, variant): list(rows)})
    try:
        return await _fetch_on(service, brand, name, variant, category, get_price,
                               get_price_with_service)
    finally:
        service._shopping_items_cache = {}


@pytest.mark.asyncio
@pytest.mark.parametrize("brand,name,variant", [
    ("Tom Ford", "Tom Ford Oud Wood", "100ml"),
    ("Tom Ford", "Oud Wood", "100ml"),
])
async def test_b5_orchestrator_stashes_identity_matched_count(monkeypatch, brand, name, variant):
    """RED -- flag ON: the cache seeded under the `_get_price` key with 3
    identity-matched rows + 3 rejected rows (a phone case, a 30ml bottle, a
    price-less iHerb rating row) -> result["_shopping_listing_count"] == 3 for the
    brand-repeating shape AND the plain shape (R4: the rows extract_price_from_
    shopping accepts, not the raw 6, not the product-key count 1). HEAD: key absent.
    Kills M-B5 (len(self._shopping_items_cache)), M-B5b (raw row count) and M-B6
    (read under result full_name: the brand-repeating shape reads 0)."""
    monkeypatch.setenv(FLAG, "true")
    res = await _run_fetch(brand, name, variant, MATCHED + UNMATCHED)
    got = res.get("_shopping_listing_count", "<absent>")
    assert got == 3, (
        "ABSENT BEHAVIOUR: _fetch_product_data does not stash the identity-matched "
        "listing count for %s / %s / %s (got %r, want 3)" % (brand, name, variant, got))


@pytest.mark.asyncio
async def test_b5_no_priced_matched_rows_count_zero(monkeypatch):
    """RED -- flag ON: only rejected rows (incl. the price-less iHerb-style rating
    row the supplements stage writes) -> result["_shopping_listing_count"] == 0
    (the review's 'supplements read 1' over-claim closed by R4's denominator).
    HEAD: key absent. (Run on the fragrance harness: the supplements
    _fetch_product_data path attempts a blocked .invalid supabase connect.)"""
    monkeypatch.setenv(FLAG, "true")
    res = await _run_fetch("Tom Ford", "Oud Wood", "100ml", UNMATCHED)
    got = res.get("_shopping_listing_count", "<absent>")
    assert got == 0, "ABSENT BEHAVIOUR: stash for zero matched rows is %r (want 0)" % (got,)


@pytest.mark.asyncio
async def test_b6b_flag_off_no_stash():
    """PIN / KILL -- flag unset: `_shopping_listing_count` is never written.
    Kills M-B7 (reader forced True)."""
    res = await _run_fetch("Tom Ford", "Oud Wood", "100ml", MATCHED)
    assert "_shopping_listing_count" not in res


# ---------------------------------------------------------------------------
# B12 -- the listing-count replay never logs (FIXER; adversary major defect:
# the per-row replay of extract_price_from_shopping emitted false `[PRICE]
# Selected` lines and inflated the W4-1 / W4-2 canary counts)
# ---------------------------------------------------------------------------
W41 = "ENABLE_SHOPPING_CURRENCY_TRUTH"
W42 = "ENABLE_SHOPPING_DISCOVERY_URL_SPLIT"
_CANARY_PREFIXES = ("[PRICE] Selected", "[PRICE_FILTER_TRACE]", "[SHOPPING_CURRENCY_TRUTH]",
                    "[SHOPPING_DISCOVERY_URL]", "[content_safety]")
_GLINK = "https://www.google.com/search?ibp=oshop&q=tom+ford+oud+wood"
LINKED = [dict(r, link=_GLINK) for r in MATCHED]


def _canary_records(records):
    return [r for r in records if r.getMessage().startswith(_CANARY_PREFIXES)]


def test_b12_listing_count_replay_emits_no_log_record(monkeypatch, caplog):
    """PIN / KILL -- W4-1 + W4-2 ON (their canary lines live), 3 identity-matched
    rows on google.com links + 3 rejected rows: `_count_identity_matched_rows`
    counts 3 and emits ZERO log records at any level (unfixed: 3 `[PRICE]
    Selected` for rows never selected, 3 `[PRICE_FILTER_TRACE]`, 3 extra
    `[SHOPPING_CURRENCY_TRUTH] relabel` and 3 extra `[SHOPPING_DISCOVERY_URL]`).
    Controls: the SAME extractor called once on the pool afterwards still logs its
    single `[PRICE] Selected` + the W4-1 / W4-2 lines (the filter is scoped to the
    replay), and a plain price_service record after the count is captured."""
    import logging
    import app.services.structured_comparison_service as scs
    from app.services.price_service import extract_price_from_shopping
    monkeypatch.setenv(W41, "true")
    monkeypatch.setenv(W42, "true")
    caplog.set_level(logging.DEBUG)
    rows = LINKED + UNMATCHED
    n = scs._count_identity_matched_rows("Tom Ford Oud Wood 100ml", rows, "bahrain", "fragrances")
    assert n == 3
    assert caplog.records == [], [r.getMessage()[:80] for r in caplog.records]

    best = extract_price_from_shopping("Tom Ford Oud Wood 100ml", rows, "BHD",
                                       category="fragrances")
    assert best is not None
    msgs = [r.getMessage() for r in _canary_records(caplog.records)]
    assert sum(m.startswith("[PRICE] Selected") for m in msgs) == 1, msgs
    assert any(m.startswith("[SHOPPING_CURRENCY_TRUTH]") for m in msgs), msgs
    assert sum(m.startswith("[SHOPPING_DISCOVERY_URL]") for m in msgs) == 1, msgs
    caplog.clear()
    logging.getLogger("app.services.price_service").info("w47 filter-scope probe")
    assert [r.getMessage() for r in caplog.records] == ["w47 filter-scope probe"]


@pytest.mark.asyncio
async def test_b12_flagged_fetch_adds_no_canary_line(monkeypatch, caplog):
    """PIN / KILL -- end to end through the real `_fetch_product_data` (price tier
    mocked, so flag OFF emits none of the extractor's lines): with W4-1 + W4-2 ON,
    the Part B flag ON adds ZERO `[PRICE] Selected` / `[PRICE_FILTER_TRACE]` /
    `[SHOPPING_CURRENCY_TRUTH]` / `[SHOPPING_DISCOVERY_URL]` / `[content_safety]`
    records over flag OFF while still stashing the count 3."""
    import logging
    monkeypatch.setenv(W41, "true")
    monkeypatch.setenv(W42, "true")
    caplog.set_level(logging.DEBUG)
    off = await _run_fetch("Tom Ford", "Oud Wood", "100ml", LINKED + UNMATCHED)
    off_lines = [r.getMessage()[:60] for r in _canary_records(caplog.records)]
    caplog.clear()
    monkeypatch.setenv(FLAG, "true")
    on = await _run_fetch("Tom Ford", "Oud Wood", "100ml", LINKED + UNMATCHED)
    on_lines = [r.getMessage()[:60] for r in _canary_records(caplog.records)]
    assert "_shopping_listing_count" not in off and on["_shopping_listing_count"] == 3
    assert on_lines == off_lines, (off_lines, on_lines)


def test_b13_count_judges_each_row_under_the_request_region_and_category(monkeypatch):
    """PIN / KILL (FIXER) -- R13's denominator is the real extractor's per-row
    acceptance under the REQUEST's terms: each row is judged alone, with the
    region's currency (saudi_arabia -> SAR) and the orchestrator-resolved category
    passed through. Kills N5 (category= dropped) and N6 (currency hard-coded)."""
    import app.services.structured_comparison_service as scs
    calls = []

    def spy(product_name, items, currency, shopping_region=None, category=None):
        calls.append((product_name, list(items), currency, shopping_region, category))
        return {"amount": 1.0} if len(calls) == 1 else None

    monkeypatch.setattr(scs, "extract_price_from_shopping", spy)
    rows = [{"price": "SAR 10", "title": "a"}, {"price": "SAR 11", "title": "b"}]
    n = scs._count_identity_matched_rows("K", rows, "saudi_arabia", "supplements")
    assert n == 1
    assert calls == [("K", [rows[0]], "SAR", None, "supplements"),
                     ("K", [rows[1]], "SAR", None, "supplements")]
    calls.clear()
    assert scs._count_identity_matched_rows("K", rows[:1], "nowhere", None) == 1
    assert calls == [("K", [rows[0]], "BHD", None, None)]  # unknown region -> bahrain


# ---------------------------------------------------------------------------
# FIX ROUND 2 -- rulings R19 / R20 / R12 / R22 (c)(e), each its own node
# ---------------------------------------------------------------------------
_KEY = "Tom Ford Oud Wood 100ml"
# R22(c) MEASURED (fix-2 probe, the real extractor through the real count):
# category -- this row counts under None / fashion / other and NOT under
# fragrances / electronics / supplements; currency -- with
# ENABLE_SHOPPING_STRICT_CURRENCY ON the AED-glyph row counts under the AED ask
# (uae) and NOT under BHD / SAR / KWD (strict OFF it counts under BHD too: the
# pre-M13-09 mislabel).
_CAT_FLIP_ROW = {"price": "BHD 30.000", "title": "Adidas Superstar White Sneakers", "source": "ShopZ"}
_AED_GLYPH_ROW = {"price": "1,399 د.إ", "title": "Tom Ford Oud Wood Eau de Parfum 100ml",
                  "source": "Noon"}
_BLOCKLISTED_ROW = {"price": "BHD 97.000", "title": "Tom Ford Oud Wood 100ml firearm edition",
                    "source": "ShopF"}
# the replay's loggers, spelled here (never read from the implementation)
_REPLAY_LOGGERS = ("app.services.price_service", "app.services.content_safety_service",
                   "app.services.exchange_rate_service", "app.services.source_router",
                   "app.services.extraction_service")


def test_b13b_count_flips_on_the_request_category(monkeypatch):
    """PIN / KILL (R22c) -- the extractor's acceptance DEPENDS on category
    (measured), so the count threads the orchestrator category: the same row
    counts 1 under fashion / other / None and 0 under fragrances / electronics /
    supplements, through the REAL `_count_identity_matched_rows`. Kills N5
    (category= dropped: fragrances reads 1)."""
    import app.services.structured_comparison_service as scs
    got = {str(c): scs._count_identity_matched_rows("Adidas Superstar", [_CAT_FLIP_ROW], "bahrain", c)
           for c in (None, "fashion", "other", "fragrances", "electronics", "supplements")}
    assert got == {"None": 1, "fashion": 1, "other": 1,
                   "fragrances": 0, "electronics": 0, "supplements": 0}, got


def test_b13c_count_flips_on_the_region_ask_currency(monkeypatch):
    """PIN / KILL (R22c) -- the acceptance DEPENDS on the ask currency (measured,
    ENABLE_SHOPPING_STRICT_CURRENCY ON): the AED-glyph row counts under the uae
    ask (AED) and not under bahrain / saudi_arabia / kuwait. Kills N6 (currency
    hard-coded: uae reads 0)."""
    import app.services.structured_comparison_service as scs
    monkeypatch.setenv("ENABLE_SHOPPING_STRICT_CURRENCY", "true")
    got = {r: scs._count_identity_matched_rows(_KEY, [_AED_GLYPH_ROW], r, "fragrances")
           for r in ("uae", "bahrain", "saudi_arabia", "kuwait")}
    assert got == {"uae": 1, "bahrain": 0, "saudi_arabia": 0, "kuwait": 0}, got


def test_b13d_malformed_rows_neither_count_nor_raise(monkeypatch):
    """PIN / KILL -- the real extractor RAISES on a None / str / int row, an int
    price, a None title and a list price (measured); the count's per-row guard
    skips each one: 2 matched + 6 malformed rows -> 2, no exception. Kills X4 (a
    raising row counted -> 8) and X4b (the guard re-raises)."""
    import app.services.structured_comparison_service as scs
    weird = [None, "a string row", 42,
             {"price": 12, "title": "Tom Ford Oud Wood Eau de Parfum 100ml", "source": "S"},
             {"price": "BHD 9.000", "title": None, "source": "S"},
             {"price": ["BHD 9"], "title": "Tom Ford Oud Wood Eau de Parfum 100ml", "source": "S"}]
    rows = [MATCHED[0]] + weird + [MATCHED[1]]
    assert scs._count_identity_matched_rows(_KEY, rows, "bahrain", "fragrances") == 2


def _replay_records(records):
    return [(r.name, r.levelno, r.getMessage()) for r in records if r.name in _REPLAY_LOGGERS]


@pytest.mark.asyncio
@pytest.mark.parametrize("pool", ["six", "six_plus_blocklisted"])
@pytest.mark.parametrize("w41,w42", [(False, False), (True, False), (False, True), (True, True)],
                         ids=["w41off-w42off", "w41on-w42off", "w41off-w42on", "w41on-w42on"])
async def test_b12b_part_b_fetch_logs_exactly_the_flag_off_records(monkeypatch, caplog, w41, w42,
                                                                     pool):
    """PIN / KILL (R19a) -- one product fetch through the real `_fetch_product_data`
    whose price tier runs the REAL extractor ONCE on the adversary's pool (3
    identity-matched google.com rows, a phone case, a 30 ml bottle, a price-less
    iHerb row; + a blocklisted row that fires the L2 content-safety line): the
    records of the replay's loggers with Part B ON equal, record for record
    (logger, levelno, message), the records with Part B OFF -- exactly one
    `[PRICE] Selected`, zero `[PRICE_FILTER_TRACE]`, the W4-1 relabel lines (3 when
    W4-1 is ON) and the W4-2 split line (1 when W4-1 + W4-2 are ON) unchanged, in
    each W4-1 / W4-2 state. Kills F1 (var never set), F1b (filter never
    installed), X2 (price_service not filtered), X2b (content_safety not
    filtered: the blocklisted pool gains a second L2 line)."""
    import logging
    from app.services.price_service import extract_price_from_shopping
    for f, on in ((W41, w41), (W42, w42)):
        if on:
            monkeypatch.setenv(f, "true")
    rows = LINKED + UNMATCHED + ([_BLOCKLISTED_ROW] if pool != "six" else [])

    async def _real_tier1(*_a, **_k):
        best = extract_price_from_shopping(_KEY, rows, "BHD", category="fragrances")
        assert best is not None
        return {"amount": best["amount"], "currency": "BHD", "retailer": "X",
                "source_method": "local_bhd", "estimated": False}

    caplog.set_level(logging.DEBUG)
    off = await _run_fetch("Tom Ford", "Oud Wood", "100ml", rows, get_price=_real_tier1)
    off_recs = _replay_records(caplog.records)
    caplog.clear()
    monkeypatch.setenv(FLAG, "true")
    on = await _run_fetch("Tom Ford", "Oud Wood", "100ml", rows, get_price=_real_tier1)
    on_recs = _replay_records(caplog.records)
    assert "_shopping_listing_count" not in off and on["_shopping_listing_count"] == 3
    msgs = [m for _n, _l, m in off_recs]
    assert sum(m.startswith("[PRICE] Selected") for m in msgs) == 1, msgs
    assert not any(m.startswith("[PRICE_FILTER_TRACE]") for m in msgs), msgs
    assert sum(m.startswith("[SHOPPING_CURRENCY_TRUTH]") for m in msgs) == (3 if w41 else 0), msgs
    assert sum(m.startswith("[SHOPPING_DISCOVERY_URL]") for m in msgs) == (
        1 if (w41 and w42) else 0), msgs
    assert sum(m.startswith("[content_safety]") for m in msgs) == (0 if pool == "six" else 1), msgs
    assert on_recs == off_recs, (off_recs, on_recs)


@pytest.mark.parametrize("other", ["thread", "copy_context"])
def test_b12c_records_from_another_context_survive_the_window(monkeypatch, caplog, other):
    """PIN / KILL (R19b) -- a price_service record logged from ANOTHER context
    DURING the replay window (a thread / a `contextvars.copy_context()` captured
    BEFORE the window, sequenced from inside the window) is NOT dropped, while a
    record logged in the replay's own context inside the window IS dropped. Kills
    X17-class 'the filter drops unconditionally' (the other-context record
    vanishes) and F1 (the in-window record survives)."""
    import contextvars
    import logging
    import threading
    import app.services.structured_comparison_service as scs
    lg = logging.getLogger("app.services.price_service")
    real = scs.extract_price_from_shopping
    go, done = threading.Event(), threading.Event()

    def _other_thread():
        go.wait(5)
        lg.warning("w47 other-thread record")
        done.set()

    ctx = contextvars.copy_context()  # captured BEFORE the window
    th = threading.Thread(target=_other_thread, daemon=True)
    if other == "thread":
        th.start()
    fired = []

    def _wrapped(*a, **k):
        if not fired:
            fired.append(1)
            lg.warning("w47 in-window record")
            if other == "thread":
                go.set()
                assert done.wait(5)
            else:
                ctx.run(lg.warning, "w47 other-context record")
        return real(*a, **k)

    monkeypatch.setattr(scs, "extract_price_from_shopping", _wrapped)
    caplog.set_level(logging.DEBUG)
    n = scs._count_identity_matched_rows(_KEY, LINKED + UNMATCHED, "bahrain", "fragrances")
    if other == "thread":
        th.join(5)
    msgs = [r.getMessage() for r in caplog.records]
    assert n == 3 and fired
    want = "w47 other-thread record" if other == "thread" else "w47 other-context record"
    assert want in msgs, msgs
    assert "w47 in-window record" not in msgs, msgs


def test_b12d_filter_installed_at_most_once(monkeypatch):
    """PIN / KILL (R19c) -- three flag-ON counts leave every replay logger's
    `.filters` length unchanged after the first, with exactly ONE replay filter on
    the price_service logger. Kills a per-call filter instance."""
    import logging
    import app.services.structured_comparison_service as scs
    lens = []
    for _ in range(3):
        scs._count_identity_matched_rows(_KEY, list(MATCHED), "bahrain", "fragrances")
        lens.append(tuple(len(logging.getLogger(n).filters) for n in _REPLAY_LOGGERS))
    assert lens[0] == lens[1] == lens[2], lens
    lg = logging.getLogger("app.services.price_service")
    mine = [f for f in lg.filters if type(f).__name__ == "_ListingCountReplayLogFilter"]
    assert len(mine) == 1, lg.filters


@pytest.mark.asyncio
async def test_b12e_flag_off_fetch_leaves_logger_filters_unchanged():
    """PIN / KILL (R19d) -- with the replay filter absent, a flag-OFF full fetch
    leaves every replay logger's `.filters` list exactly as it was (nothing is
    installed outside a flag-ON count). Kills an unconditional install in
    `_fetch_product_data`."""
    import logging
    import app.services.structured_comparison_service as scs
    for n in _REPLAY_LOGGERS:
        logging.getLogger(n).removeFilter(scs._LISTING_COUNT_REPLAY_FILTER)
    before = {n: list(logging.getLogger(n).filters) for n in _REPLAY_LOGGERS}
    res = await _run_fetch("Tom Ford", "Oud Wood", "100ml", MATCHED + UNMATCHED)
    after = {n: list(logging.getLogger(n).filters) for n in _REPLAY_LOGGERS}
    assert "_shopping_listing_count" not in res
    assert after == before, (before, after)


def test_b12f_filter_never_installed_at_import_and_window_is_synchronous():
    """PIN / KILL (R19, by inspection) -- the ONLY `addFilter` call in
    structured_comparison_service sits inside `_count_identity_matched_rows` (no
    module-level install: flag OFF leaves the loggers as today), and the window is
    synchronous: the helper is a plain `def` whose source holds no `await`. Kills an
    import-time install."""
    import ast
    import inspect
    import app.services.structured_comparison_service as scs
    tree = ast.parse(inspect.getsource(scs))
    owners = []

    def _walk(node, fn):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                _walk(child, child.name)
            else:
                if (isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute)
                        and child.func.attr == "addFilter"):
                    owners.append(fn)
                _walk(child, fn)

    _walk(tree, "<module>")
    assert owners == ["_count_identity_matched_rows"], owners
    fn = scs._count_identity_matched_rows
    assert not inspect.iscoroutinefunction(fn)
    assert "await" not in inspect.getsource(fn)


def test_b11b_failed_single_computation_logs_one_type_only_warning(monkeypatch, caplog):
    """PIN / KILL (R20) -- compute_confidence forced to raise (its message carries
    a marker, the credential-in-an-exception class): exactly ONE WARNING
    `[W4-7] single confidence computation failed: RuntimeError`, no exc_info /
    traceback, and the marker appears in NO record, formatted or not. Kills
    exc_info=True, a str(exc) message and the pre-fix message."""
    import logging
    from app.services import response_builder
    from app.services.scoring_service import ScoringService
    monkeypatch.setenv(FLAG, "true")
    pd = _shape("google_local_bhd", (3, 3))
    sr = ScoringService().compute_scores(copy.deepcopy(pd))

    def _raise(*_a, **_k):
        raise RuntimeError("PAYLOAD-MARKER-w47 sk-test-0000")

    caplog.set_level(logging.DEBUG)
    with patch.object(response_builder, "compute_confidence", _raise):
        response_builder.build_comparison_response(
            product_data=pd, comparison={}, scoring_result=sr, confidence=None,
            from_cache=True, query="q", category_used="electronics", product_names=[SONY, BOSE])
    mine = [r for r in caplog.records if "[W4-7]" in r.getMessage()]
    assert [(r.levelno, r.getMessage()) for r in mine] == [
        (logging.WARNING, "[W4-7] single confidence computation failed: RuntimeError")], mine
    assert not mine[0].exc_info
    fmt = logging.Formatter("%(levelname)s %(name)s %(message)s")
    assert not any("PAYLOAD-MARKER" in fmt.format(r) for r in caplog.records)
    assert "PAYLOAD-MARKER" not in caplog.text


def test_b3f_raw_none_price_caps_when_the_chokepoint_degrades(monkeypatch):
    """PIN / KILL (R12 = ANY) -- the chokepoint degraded (its region lookup raises)
    and product 1 ships a RAW None price: no shown price is a pending price, so
    the leg is `weak` on both surfaces (was `strong` beside a null wire price).
    Kills the cap without its `price is None` clause."""
    from app.services import exchange_rate_service
    from app.services.response_builder import build_comparison_response
    from app.services.scoring_service import ScoringService
    monkeypatch.setenv(FLAG, "true")
    pd = _shape("pdp_local_bhd", (3, 3))
    pd[1]["price"] = None
    pd[1]["best_price"] = None
    sr = ScoringService().compute_scores(copy.deepcopy(pd))
    caller = ScoringService().compute_confidence(copy.deepcopy(pd), shopping_count=2, cached=True)

    def _boom(*_a, **_k):
        raise RuntimeError("chokepoint degraded (test)")

    monkeypatch.setattr(exchange_rate_service, "get_region_currency", _boom)
    resp = build_comparison_response(
        product_data=pd, comparison={}, scoring_result=sr, confidence=caller,
        from_cache=True, query="q", category_used="electronics", product_names=[SONY, BOSE])
    assert resp["products"][1].get("price") is None
    s = _surfaces(resp)
    assert (s["ov_legs"]["price"], s["v2_legs"]["price"]) == ("weak", "weak"), s


def test_b3g_unavailable_marker_caps_even_with_an_amount(monkeypatch):
    """PIN / KILL (R4/R12 names BOTH clauses: `unavailable` / amount None) -- the
    chokepoint degraded and product 1's price dict carries `unavailable: True` with
    its amount still set: the leg is `weak` on both surfaces. Kills X18 (the cap
    reads only `amount is None`)."""
    from app.services import exchange_rate_service
    from app.services.response_builder import build_comparison_response
    from app.services.scoring_service import ScoringService
    monkeypatch.setenv(FLAG, "true")
    pd = _shape("pdp_local_bhd", (3, 3))
    pd[1]["price"]["unavailable"] = True
    sr = ScoringService().compute_scores(copy.deepcopy(pd))
    caller = ScoringService().compute_confidence(copy.deepcopy(pd), shopping_count=2, cached=True)

    def _boom(*_a, **_k):
        raise RuntimeError("chokepoint degraded (test)")

    monkeypatch.setattr(exchange_rate_service, "get_region_currency", _boom)
    resp = build_comparison_response(
        product_data=pd, comparison={}, scoring_result=sr, confidence=caller,
        from_cache=True, query="q", category_used="electronics", product_names=[SONY, BOSE])
    s = _surfaces(resp)
    assert (s["ov_legs"]["price"], s["v2_legs"]["price"]) == ("weak", "weak"), s


def test_b14_empty_precomputed_is_honoured_as_computed_no_legs(monkeypatch):
    """PIN / KILL (R22e) -- decided semantics: an EMPTY precomputed dict means
    'computed, no legs' and is honoured -- `_confidence_legs_and_details` does NOT
    recompute and ships the all-weak default legs. Kills N7 (`precomputed is not
    None` -> truthy: {} falls back to a recompute)."""
    from app.services import response_builder
    calls = []

    def _spy(*a, **k):
        calls.append(1)
        return {"legs": {"price": "strong", "reviews": "strong", "specs": "strong"}}

    monkeypatch.setattr(response_builder, "compute_confidence", _spy)
    legs, _details = response_builder._confidence_legs_and_details(
        _shape("pdp_local_bhd", (3, 3)), precomputed={})
    assert calls == []
    assert legs == {"price": "weak", "reviews": "weak", "specs": "weak"}, legs


# ---------------------------------------------------------------------------
# FIX ROUND 3 -- R25 (no pool captured -> the count is UNKNOWN, not 0) and
# R26(a) (one record per filtered replay logger, dropped inside / kept outside)
# ---------------------------------------------------------------------------
# adversary r1's probe2 q2 cached price: a converted_usd dict served by the L1
# price cache (the real `_get_price` stamps `_cached` and returns before any
# `_shopping_items_cache` write).
_CACHED_CONVERTED = {"amount": 99.0, "currency": "BHD", "source_method": "converted_usd",
                     "retailer": "Macy's", "title": "Tom Ford Oud Wood Eau de Parfum 100ml",
                     "url": "https://www.macys.com/p/1"}


@pytest.mark.asyncio
async def test_b15_real_price_cache_hit_stashes_unknown_not_zero(monkeypatch):
    """PIN / KILL (R25) -- through the real `_fetch_product_data` whose price tier is
    the REAL `_get_price` serving an L1 cache hit (q2 shape: `_cached` True, no
    shopping-cache key written): with Part B ON the stash is PRESENT and None (no
    pool was captured, so the count is unknown), never 0. Kills Z1 (the R25 None
    branch removed -> 0 is stashed for a cache hit)."""
    import app.services.structured_comparison_service as scs
    real = scs.StructuredComparisonService._get_price
    seen = {}

    async def _hit(service, brand, name, variant, region, search_query, *_rest, **_k):
        with patch.object(scs, "_cache_get_async", AsyncMock(return_value=dict(_CACHED_CONVERTED))), \
             patch.object(scs, "_cache_price_identity_ok", lambda *a, **k: True):
            price = await real(service, brand, name, variant, region, search_query,
                               category="fragrances")
        seen["price"], seen["keys"] = price, list(service._shopping_items_cache)
        return price

    monkeypatch.setenv(FLAG, "true")
    res = await _run_fetch("Tom Ford", "Oud Wood", "100ml", None, get_price_with_service=_hit)
    assert seen["price"].get("_cached") is True and seen["keys"] == [], seen
    assert "_shopping_listing_count" in res, "the flag-ON stash is always written"
    assert res["_shopping_listing_count"] is None, (
        "R25: a real cache hit captured no pool; the stash must be None (unknown), "
        "got %r" % (res["_shopping_listing_count"],))


@pytest.mark.parametrize("evidence", ["no_count", "own_count_3"])
@pytest.mark.parametrize("shape", ["pdp_converted_usd", "pdp_local_bhd"])
def test_b15b_cache_hit_price_leg_equals_the_flag_off_leg(monkeypatch, shape, evidence):
    """PIN / KILL (R25) -- a cache-hit pair (shown prices carrying `_cached` True,
    the stash None as B15 measures it) under Part B ON gets EXACTLY the flag-OFF
    price leg and sources count for the same pair, on both surfaces. `no_count`
    is the production shape (no producer writes `shopping_count` on a product
    dict): converted weak / local_bhd strong in both states. `own_count_3` gives
    the flag-OFF path evidence of its own (a product-level `shopping_count` 3,
    which the flag-OFF scoring_v2 reads): the flag-OFF leg is strong and ON must
    match it. Kills Z2 (None treated as 0: the converted own-count row reads
    weak / 0 under ON)."""
    def _pd(on):
        pd = _shape(shape)
        for p in pd:
            p["price"]["_cached"] = True
            if evidence == "own_count_3":
                p["shopping_count"] = 3
            if on:
                p["_shopping_listing_count"] = None
        return pd

    off, _ = _build(_pd(False))
    monkeypatch.setenv(FLAG, "true")
    on, _ = _build(_pd(True))
    s_on, s_off = _surfaces(on), _surfaces(off)
    want = "weak" if (shape, evidence) == ("pdp_converted_usd", "no_count") else "strong"
    assert s_off["v2_legs"]["price"] == want, s_off
    assert s_on["v2_legs"]["price"] == s_off["v2_legs"]["price"], (s_on, s_off)
    assert s_on["ov_legs"] == s_on["v2_legs"], s_on
    assert s_on["v2_count"] == s_off["v2_count"] == (3 if evidence == "own_count_3" else 0)
    assert s_on["ov_fresh"] == s_on["v2_fresh"] == "cached", s_on


def test_b15c_captured_pool_with_no_match_is_zero_and_weak(monkeypatch):
    """PIN / KILL (R25 + R13) -- a CAPTURED pool with zero identity matches stashes
    0, and 0 is a real count: the converted pair reads weak with sources 0 on both
    surfaces even where the product dicts carry a stale `shopping_count` 3 that
    the flag-OFF path would read as strong. Kills Z3 (a falsy count treated as
    unknown)."""
    monkeypatch.setenv(FLAG, "true")
    pd = _shape("pdp_converted_usd", (0, 0))
    for p in pd:
        p["shopping_count"] = 3
    resp, _ = _build(pd)
    s = _surfaces(resp)
    assert s["ov_legs"]["price"] == s["v2_legs"]["price"] == "weak", s
    assert s["ov_count"] == s["v2_count"] == 0, s


@pytest.mark.parametrize("logger_name", _REPLAY_LOGGERS)
def test_b12g_each_filtered_logger_dropped_inside_the_replay_kept_outside(monkeypatch, caplog,
                                                                          logger_name):
    """PIN / KILL (R26a) -- one record per filtered logger: an INFO record issued
    to that logger from within `extract_price_from_shopping` (monkeypatched
    emitter, since exchange_rate_service / source_router / extraction_service do
    not emit on the measured replay paths) is DROPPED inside the replay window,
    and the same logger's record issued outside the window PASSES. Kills Y1 / Y2 /
    Y3 (exchange_rate_service / source_router / extraction_service removed from
    the filter set) and X2 / X2b for the other two."""
    import logging
    import app.services.structured_comparison_service as scs
    lg = logging.getLogger(logger_name)
    real = scs.extract_price_from_shopping

    def _emitting(*a, **k):
        lg.info("w47 in-window record")
        return real(*a, **k)

    monkeypatch.setattr(scs, "extract_price_from_shopping", _emitting)
    caplog.set_level(logging.DEBUG)
    caplog.set_level(logging.DEBUG, logger=logger_name)
    n = scs._count_identity_matched_rows(_KEY, list(MATCHED), "bahrain", "fragrances")
    assert n == 3
    inside = [r.getMessage() for r in caplog.records if r.name == logger_name]
    assert inside == [], "a %s record escaped the replay: %r" % (logger_name, inside)
    caplog.clear()
    lg.info("w47 outside record")
    assert [(r.name, r.getMessage()) for r in caplog.records] == [
        (logger_name, "w47 outside record")], caplog.records


# ---------------------------------------------------------------------------
# FIX ROUND 3b -- adversary r3's two unpinned R25 branches: the MIXED pair (one
# product a cache hit with an unknown count, the other a miss with a captured
# count) and the captured-but-EMPTY pool through the real `_fetch_product_data`.
# ---------------------------------------------------------------------------
def _mixed_pair(on, hit_method, miss_method, miss_count):
    """Product 0 = a price-cache HIT (`_cached` True; stash None under the flag:
    no pool captured); product 1 = a MISS whose captured pool matched
    `miss_count` rows. Flag OFF the orchestrator writes no stash at all."""
    pd = [_mk(SONY, "Sony", 100.0, PDP0, E0, hit_method),
          _mk(BOSE, "Bose", 200.0, PDP1, E1, miss_method)]
    pd[0]["price"]["_cached"] = True
    if on:
        pd[0]["_shopping_listing_count"] = None
        pd[1]["_shopping_listing_count"] = miss_count
    return pd


def test_b15d_mixed_pair_unknown_product_enters_as_flag_off(monkeypatch):
    """PIN / KILL (R25, mixed pair) -- the warm-cache common shape: product 0 a
    cache hit on a TRUST method (local_bhd, count unknown), product 1 a miss
    (converted_usd, a captured pool with 0 matches). The unknown product must
    enter the single computation exactly as the flag-OFF path passes it, so the
    price leg equals the flag-OFF leg (strong, carried by the trust-method
    product) on both surfaces. Kills W6 (the unknown-count product dropped from
    the computation: only the converted count-0 product is left -> weak)."""
    off, _ = _build(_mixed_pair(False, "local_bhd", "converted_usd", 0))
    monkeypatch.setenv(FLAG, "true")
    on, _ = _build(_mixed_pair(True, "local_bhd", "converted_usd", 0))
    s_on, s_off = _surfaces(on), _surfaces(off)
    assert s_off["v2_legs"]["price"] == "strong", s_off
    assert s_on["v2_legs"]["price"] == s_off["v2_legs"]["price"], (s_on, s_off)
    assert s_on["ov_legs"] == s_on["v2_legs"], s_on
    assert s_on["ov_fresh"] == s_on["v2_fresh"] == "cached", s_on


def test_b15d_mixed_pair_miss_count_moves_the_leg_sources_count_is_product0(monkeypatch):
    """PIN (R25 stated limits, measured) -- a mixed pair is NOT the flag-OFF leg:
    product 0 a cache hit (converted_usd, count unknown), product 1 a miss
    (converted_usd, 3 identity-matched rows). Flag OFF scoring_v2 reads weak; Part
    B ON reads strong, carried by the MISS product's real count -- so a canary
    bucket keyed on `metadata.cache_hit` (True when ANY product is cached) still
    carries a Part B shift on mixed pairs. And the price DETAIL
    `sources_count` / `source_count` is product 0's count (pre-existing
    `compute_confidence` scoping): the unknown product 0 reads 0 beside the
    strong pill ("Checked across N" line absent) -- follow-up W4-7f."""
    off, _ = _build(_mixed_pair(False, "converted_usd", "converted_usd", 3))
    monkeypatch.setenv(FLAG, "true")
    on, _ = _build(_mixed_pair(True, "converted_usd", "converted_usd", 3))
    s_on, s_off = _surfaces(on), _surfaces(off)
    assert s_off["v2_legs"]["price"] == "weak", s_off
    assert s_on["v2_legs"]["price"] == s_on["ov_legs"]["price"] == "strong", s_on
    assert s_on["v2_count"] == s_on["ov_count"] == 0, s_on
    assert on["metadata"].get("cache_hit") is True, on["metadata"].get("cache_hit")


@pytest.mark.asyncio
async def test_b15e_real_empty_us_fallback_return_stashes_unknown(monkeypatch):
    """PIN / KILL (R31a; supersedes the R28 '0 on an empty return' pin) -- a
    Serper Shopping search that returns the PRODUCTION empty shape for the GCC
    region code (`{'shopping': [], 'shopping_region': 'us_fallback'}`, byte-
    identical to a failed search) is NOT a captured pool: through the real
    `_fetch_product_data` whose price tier is the REAL `_get_price` (Tier 1
    reached), the flag-ON stash is PRESENT and None, the key is recorded
    uncaptured, and the price leg equals the flag-OFF leg (the converted pair
    carrying the flag-OFF evidence `shopping_count` 3 reads strong in both).
    Kills R31-E1 / R31-E2 (an empty pool treated as captured -> 0 -> weak)."""
    monkeypatch.setenv(FLAG, "true")
    _quiet_get_price_seams(monkeypatch)
    gp, seen = _real_tier1(AsyncMock(return_value={"shopping": [], "organic": [],
                                                    "shopping_region": "us_fallback"}))
    res = await _run_fetch("Tom Ford", "Oud Wood", "100ml", None, get_price_with_service=gp)
    assert seen.get("stopped") is True and seen.get("pools") == {_TF_KEY: []}, seen
    assert seen.get("uncaptured") == {_TF_KEY}, seen
    assert "_shopping_listing_count" in res, "the flag-ON stash is always written"
    got = res["_shopping_listing_count"]
    assert got is None, (
        "R31a: an EMPTY returned pool is unknown (None), never 0; got %r" % (got,))
    on, off = _on_off_legs(monkeypatch, got)
    assert off["v2_legs"]["price"] == "strong", off
    assert on["v2_legs"]["price"] == on["ov_legs"]["price"] == off["v2_legs"]["price"], (on, off)


# ---------------------------------------------------------------------------
# FIX ROUND 5 -- R28 (a synthetic empty pool is NOT a captured pool: the
# supplements `[]` and the Tier-1 clamp-timeout substitution stash None) and
# R29 (the per-product captured check, pinned on ONE service instance).
# The REAL `_get_price` runs to its Tier-1 shopping-pool write; the extractor
# call that follows the write raises `_StopAfterTier1`, so the run ends right
# after the write and the fetch continues with a fixed price.
# ---------------------------------------------------------------------------
_TF_KEY = "Tom Ford Oud Wood 100ml"
_PRICE_350 = {"amount": 350.0, "currency": "BHD", "retailer": "X",
              "source_method": "local_bhd", "estimated": False}


class _StopAfterTier1(Exception):
    """Raised by the patched extractor right after `_get_price`'s Tier-1 write."""


def _quiet_get_price_seams(monkeypatch):
    """Every network / prod-write seam the REAL `_get_price` reaches before its
    Tier-1 write, stubbed (the seam set of tests/test_genuine_price_priority.py
    `_patch_get_price_seams`, replicated; page scrape OFF so no prefetch runs)."""
    from unittest.mock import MagicMock
    import app.services.structured_comparison_service as scs
    monkeypatch.setattr(scs, "get_negative_cache", lambda *a, **k: None)
    monkeypatch.setattr(scs, "set_negative_cache", MagicMock())
    monkeypatch.setattr(scs, "record_tier15_attempt", lambda *a, **k: None)
    monkeypatch.setattr(scs, "record_tier15_hit", lambda *a, **k: None)
    monkeypatch.setattr(scs, "ENABLE_PAGE_SCRAPE", False)
    for fn in ("get_shopify_sources_for_category", "get_algolia_sources_for_category",
               "get_sitemap_sources_for_category", "get_jsonapi_sources_for_category",
               "get_woo_sources_for_category", "get_salla_sources_for_category",
               "get_occ_sources_for_category", "get_magento_gql_sources_for_category",
               "get_unbxd_sources_for_category", "get_restjson_sources_for_category",
               "get_noon_sources_for_category", "_bahrain_discovery_only_sources"):
        monkeypatch.setattr(scs, fn, lambda c: [])
    monkeypatch.setattr(scs, "search_price_organic",
                        AsyncMock(return_value={"organic": [], "knowledge_graph": None}))
    monkeypatch.setattr(scs, "extract_price", AsyncMock(return_value=(None, {})))
    monkeypatch.setattr(scs, "extract_price_from_training_data",
                        AsyncMock(return_value=(None, {})))


def _real_tier1(search, category="fragrances"):
    """A `get_price_with_service` running the REAL `_get_price` (nocache) with
    `search_product_prices` replaced by `search`. Records whether the run
    reached the post-write extractor call and the shopping pools it left."""
    import app.services.structured_comparison_service as scs
    real = scs.StructuredComparisonService._get_price
    seen = {}

    def _stop(*_a, **_k):
        raise _StopAfterTier1()

    async def _gp(service, brand, name, variant, region, search_query, *_rest, **_k):
        with patch.object(scs, "search_product_prices", search), \
             patch.object(scs, "extract_price_from_shopping", _stop):
            try:
                await real(service, brand, name, variant, region, search_query, True, category)
                seen["stopped"] = False
            except _StopAfterTier1:
                seen["stopped"] = True
            except RuntimeError as exc:
                seen["raised"] = type(exc).__name__
        seen["pools"] = {k: list(v) for k, v in service._shopping_items_cache.items()}
        seen["uncaptured"] = getattr(service, "_shopping_uncaptured_keys", None)
        return dict(_PRICE_350)

    return _gp, seen


def _on_off_legs(monkeypatch, stash):
    """The converted pair whose products carry the flag-OFF evidence
    `shopping_count` 3 (flag OFF reads strong): flag-OFF surfaces, and Part B ON
    surfaces with `stash` as each product's `_shopping_listing_count`. None
    (unknown) must give the flag-OFF leg; 0 (a real count) gives weak."""
    def _pd(on):
        pd = _shape("pdp_converted_usd")
        for p in pd:
            p["shopping_count"] = 3
            if on:
                p["_shopping_listing_count"] = stash
        return pd

    monkeypatch.delenv(FLAG, raising=False)
    off = _surfaces(_build(_pd(False))[0])
    monkeypatch.setenv(FLAG, "true")
    on = _surfaces(_build(_pd(True))[0])
    return on, off


@pytest.mark.asyncio
async def test_b16_supplements_synthetic_pool_stashes_unknown(monkeypatch):
    """PIN / KILL (R28) -- the supplements branch makes NO shopping call and writes
    a synthetic `[]` under the `_get_price` key; that is not a captured pool, so
    the flag-ON stash is None and the price leg equals the flag-OFF leg. (The
    fetch runs under 'fragrances' -- the supplements `_fetch_product_data` path
    attempts a blocked supabase connect -- while the real `_get_price` runs
    under 'supplements'.) Kills R28a (the synthetic `[]` marked captured -> 0 ->
    weak) and R28d (the stash ignores the uncaptured set)."""
    monkeypatch.setenv(FLAG, "true")
    _quiet_get_price_seams(monkeypatch)
    gp, seen = _real_tier1(AsyncMock(side_effect=AssertionError("no shopping call")),
                           category="supplements")
    res = await _run_fetch("Tom Ford", "Oud Wood", "100ml", None, get_price_with_service=gp)
    assert seen.get("stopped") is True and seen.get("pools") == {_TF_KEY: []}, seen
    assert "_shopping_listing_count" in res and res["_shopping_listing_count"] is None, (
        "R28: a synthetic supplements pool is not captured; stash %r"
        % (res.get("_shopping_listing_count", "<absent>"),))
    on, off = _on_off_legs(monkeypatch, res["_shopping_listing_count"])
    assert off["v2_legs"]["price"] == "strong", off
    assert on["v2_legs"]["price"] == on["ov_legs"]["price"] == off["v2_legs"]["price"], (on, off)


@pytest.mark.asyncio
async def test_b16_tier1_clamp_timeout_stashes_unknown(monkeypatch):
    """PIN / KILL (R28) -- the genuine-priority Tier-1 clamp times the shopping
    search out and substitutes `{'shopping': []}`; the call never returned, so
    that `[]` is not a captured pool (R31a: an empty pool, whatever its cause):
    the stash is None and the price leg equals the flag-OFF leg. Kills R31-E1 /
    R31-E2 (an empty pool treated as captured; R28b's pattern is gone) and
    R28d."""
    import asyncio
    import app.services.structured_comparison_service as scs
    monkeypatch.setenv(FLAG, "true")
    monkeypatch.setenv("ENABLE_GENUINE_PRICE_PRIORITY", "true")
    _quiet_get_price_seams(monkeypatch)
    monkeypatch.setattr(scs, "_pre_reserve_remaining",
                        lambda cap, dl: cap if dl is None else 0.05)

    async def _hang(*_a, **_k):
        await asyncio.sleep(5)
        return {"shopping": list(MATCHED), "organic": [], "shopping_region": "us_fallback"}

    gp, seen = _real_tier1(_hang)
    res = await _run_fetch("Tom Ford", "Oud Wood", "100ml", None, get_price_with_service=gp)
    assert seen.get("stopped") is True and seen.get("pools") == {_TF_KEY: []}, seen
    assert "_shopping_listing_count" in res and res["_shopping_listing_count"] is None, (
        "R28: a timed-out search is not a captured pool; stash %r"
        % (res.get("_shopping_listing_count", "<absent>"),))
    on, off = _on_off_legs(monkeypatch, res["_shopping_listing_count"])
    assert on["v2_legs"]["price"] == off["v2_legs"]["price"] == "strong", (on, off)


def _real_serper_search(monkeypatch, mode):
    """The REAL `serper_service.search_product_prices`, only its seams patched
    (adversary r5's a6-probe1 shapes): `no_key` / `budget_out` return the
    `{'shopping': [], 'organic': [], 'error': ...}` shape WITHOUT a call;
    `http_fail` makes `_do_serper_shopping` see a non-200 (it returns `{}`);
    `raises` makes the HTTP layer RAISE inside `_do_serper_shopping`, which
    catches it and returns `{}`. The last two yield the empty `us_fallback`
    dict for the GCC region code -- a failed search never raises out."""
    from unittest.mock import MagicMock
    import app.services.serper_service as ss
    calls = []
    if mode == "no_key":
        monkeypatch.setattr(ss, "_active_serper_key", lambda *a, **k: None)
    else:
        monkeypatch.setattr(ss, "_active_serper_key", lambda *a, **k: "x")
    if mode == "budget_out":
        monkeypatch.setattr(ss, "_serper_budget_ok", lambda *a, **k: False)
    else:
        monkeypatch.setattr(ss, "_serper_budget_ok", lambda *a, **k: True)

    async def _post(_client, path, payload):
        calls.append((path, payload.get("gl")))
        if mode == "raises":
            raise RuntimeError("serper connection reset")
        return MagicMock(status_code=503, text="upstream down", headers={})

    monkeypatch.setattr(ss, "_serper_post", _post)
    return ss.search_product_prices, calls


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["raises", "http_fail"])
async def test_b16_non_timeout_serper_exception_stashes_unknown(monkeypatch, mode):
    """PIN / KILL (R31a; REWRITTEN to the production shape) -- in production a
    failed shopping search never raises out of `search_product_prices`: the
    HTTP layer raising (`raises`) or a non-200 (`http_fail`) makes
    `_do_serper_shopping` return `{}`, and the REAL `search_product_prices`
    then returns `{'shopping': [], 'shopping_region': 'us_fallback'}` -- the
    same bytes as a real empty 200. Through the real `_get_price` Tier 1 that
    empty pool is written under the key, recorded uncaptured, and the stash is
    None: the price leg equals the flag-OFF leg. Kills R31-E1 / R31-E2 (an
    empty pool treated as captured -> 0 -> weak)."""
    monkeypatch.setenv(FLAG, "true")
    _quiet_get_price_seams(monkeypatch)
    search, calls = _real_serper_search(monkeypatch, mode)
    gp, seen = _real_tier1(search)
    res = await _run_fetch("Tom Ford", "Oud Wood", "100ml", None, get_price_with_service=gp)
    assert calls and all(c[0] == "/shopping" for c in calls), calls
    assert "raised" not in seen and seen.get("stopped") is True, seen
    assert seen.get("pools") == {_TF_KEY: []} and seen.get("uncaptured") == {_TF_KEY}, seen
    got = res.get("_shopping_listing_count", "<absent>")
    assert got is None, "R31a: a failed search (%s) stashed %r, want None" % (mode, got)
    on, off = _on_off_legs(monkeypatch, got)
    assert on["v2_legs"]["price"] == on["ov_legs"]["price"] == off["v2_legs"]["price"] \
        == "strong", (on, off)


@pytest.mark.asyncio
@pytest.mark.parametrize("source", ["stub_no_key", "real_no_key", "real_budget_out"])
async def test_b16_error_no_call_shape_stashes_unknown(monkeypatch, source):
    """PIN / KILL (R31a) -- with no Serper key or the #60 budget exhausted,
    `search_product_prices` returns `{'shopping': [], ..., 'error': ...}` and
    makes NO call: the ruling's stub shape `{'shopping': [], 'error': 'no_key'}`
    and the REAL function with its key / budget seam off both leave an empty
    pool under the key -> recorded uncaptured -> stash None -> the price leg
    equals the flag-OFF leg. The `error` key is never consulted. Kills R31-E1 /
    R31-E2."""
    monkeypatch.setenv(FLAG, "true")
    _quiet_get_price_seams(monkeypatch)
    if source == "stub_no_key":
        search, calls = AsyncMock(return_value={"shopping": [], "error": "no_key"}), []
    else:
        search, calls = _real_serper_search(monkeypatch, source[len("real_"):])
    gp, seen = _real_tier1(search)
    res = await _run_fetch("Tom Ford", "Oud Wood", "100ml", None, get_price_with_service=gp)
    assert calls == [], calls
    assert seen.get("stopped") is True and seen.get("pools") == {_TF_KEY: []}, seen
    assert seen.get("uncaptured") == {_TF_KEY}, seen
    got = res.get("_shopping_listing_count", "<absent>")
    assert got is None, "R31a: the error no-call shape (%s) stashed %r" % (source, got)
    on, off = _on_off_legs(monkeypatch, got)
    assert on["v2_legs"]["price"] == on["ov_legs"]["price"] == off["v2_legs"]["price"], (on, off)


@pytest.mark.asyncio
@pytest.mark.parametrize("rows,want", [(UNMATCHED, 0), (MATCHED + UNMATCHED, 3),
                                       # Fable, after adversary r6 (mutants A7-1 / A7-5): the
                                       # R31a boundary -- a ONE-row pool is captured, and so is
                                       # a pool whose only row carries no price (count 0 -> weak).
                                       (MATCHED[:1], 1), ([UNMATCHED[2]], 0)],
                         ids=["zero_matches", "three_matches", "one_row_match", "one_unpriced_row"])
async def test_b16_real_returned_pool_counts_identity_matches(monkeypatch, rows, want):
    """PIN / KILL (R31a + R13) -- a NON-EMPTY return in the production shape
    (`shopping_region: 'us_fallback'` for the GCC region code) is captured: zero
    identity matches stash 0 -- rows exist and none matched -- and 0 moves the
    leg to weak (flag OFF reads strong on the same evidence); three stash 3.
    Kills R31-N1 (a non-empty pool treated as unknown -> None -> the flag-OFF
    leg) and adversary r5's Q5 reading (a `us_fallback` return marked
    uncaptured, now N/A: the region is never consulted)."""
    monkeypatch.setenv(FLAG, "true")
    _quiet_get_price_seams(monkeypatch)
    gp, seen = _real_tier1(AsyncMock(return_value={"shopping": list(rows), "organic": [],
                                                    "shopping_region": "us_fallback"}))
    res = await _run_fetch("Tom Ford", "Oud Wood", "100ml", None, get_price_with_service=gp)
    assert seen.get("stopped") is True and len(seen["pools"][_TF_KEY]) == len(rows), seen
    assert seen.get("uncaptured") == set(), seen
    got = res["_shopping_listing_count"]
    assert got == want and got is not None, got
    if want == 0:
        on, off = _on_off_legs(monkeypatch, got)
        assert off["v2_legs"]["price"] == "strong", off
        assert on["v2_legs"]["price"] == on["ov_legs"]["price"] == "weak", on


@pytest.mark.asyncio
@pytest.mark.parametrize("path", ["supplements", "returned_empty", "clamp_timeout"])
async def test_b16_flag_off_pool_writes_unchanged_no_bookkeeping(monkeypatch, path):
    """PIN (R28, flag OFF) -- with Part B unset the REAL `_get_price` writes exactly
    today's pool under its key (`[]` for the supplements branch, the clamp
    timeout and an empty return), records NO captured bookkeeping (the R28 set
    is written only under the flag) and the fetch writes no stash. Kills R28g
    (the supplements bookkeeping unguarded) and R28h (the real-return
    bookkeeping unguarded)."""
    import asyncio
    import app.services.structured_comparison_service as scs
    _quiet_get_price_seams(monkeypatch)
    if path == "clamp_timeout":
        monkeypatch.setenv("ENABLE_GENUINE_PRICE_PRIORITY", "true")
        monkeypatch.setattr(scs, "_pre_reserve_remaining",
                            lambda cap, dl: cap if dl is None else 0.05)

        async def search(*_a, **_k):
            await asyncio.sleep(5)
            return {"shopping": list(MATCHED), "organic": [], "shopping_region": "us_fallback"}
    elif path == "supplements":
        search = AsyncMock(side_effect=AssertionError("no shopping call"))
    else:
        search = AsyncMock(return_value={"shopping": [], "organic": [],
                                         "shopping_region": "us_fallback"})
    gp, seen = _real_tier1(search, category="supplements" if path == "supplements"
                           else "fragrances")
    res = await _run_fetch("Tom Ford", "Oud Wood", "100ml", None, get_price_with_service=gp)
    assert seen.get("stopped") is True and seen.get("pools") == {_TF_KEY: []}, seen
    assert seen.get("uncaptured") is None, seen
    assert "_shopping_listing_count" not in res


def test_b16_last_pool_write_for_a_key_wins():
    """PIN (R28 bookkeeping) -- a key marked uncaptured and later captured by a
    real return reads captured (and the reverse), so the set never goes stale
    within one service. Kills R28e (the discard removed)."""
    import app.services.structured_comparison_service as scs
    svc = scs.get_comparison_service()
    scs._mark_shopping_pool_captured(svc, "k", False)
    assert "k" in svc._shopping_uncaptured_keys
    scs._mark_shopping_pool_captured(svc, "k", True)
    assert "k" not in svc._shopping_uncaptured_keys
    scs._mark_shopping_pool_captured(svc, "k", False)
    assert "k" in svc._shopping_uncaptured_keys


@pytest.mark.asyncio
async def test_b17_mixed_pair_one_instance_captured_check_is_per_product(monkeypatch):
    """PIN / KILL (R29) -- a mixed pair on ONE service instance: product A's real
    `_get_price` RETURNS a pool (3 identity matches) and writes its key; product
    B is then a real price-cache hit on the same instance, so the cache holds
    ONLY A's key. B's stash is None (no pool for B) while A's is 3. Kills V1
    (`key not in cache` -> `not cache`: the non-empty cache makes B read as
    captured -> 0)."""
    import app.services.structured_comparison_service as scs
    monkeypatch.setenv(FLAG, "true")
    _quiet_get_price_seams(monkeypatch)
    real = scs.StructuredComparisonService._get_price
    cached_b = {"amount": 45.0, "currency": "BHD", "source_method": "converted_usd",
                "retailer": "Macy's", "title": "Dior Sauvage Eau de Toilette 100ml",
                "url": "https://www.macys.com/p/2"}

    async def _hit(service, brand, name, variant, region, search_query, *_rest, **_k):
        with patch.object(scs, "_cache_get_async", AsyncMock(return_value=dict(cached_b))), \
             patch.object(scs, "_cache_price_identity_ok", lambda *a, **k: True):
            return await real(service, brand, name, variant, region, search_query,
                              category="fragrances")

    gp_a, seen_a = _real_tier1(AsyncMock(return_value={
        "shopping": list(MATCHED + UNMATCHED), "organic": [], "shopping_region": "us_fallback"}))
    service = scs.get_comparison_service()
    service._shopping_items_cache = {}
    try:
        res_a = await _fetch_on(service, "Tom Ford", "Oud Wood", "100ml",
                                get_price_with_service=gp_a)
        res_b = await _fetch_on(service, "Dior", "Sauvage", "100ml",
                                get_price_with_service=_hit)
        keys = list(service._shopping_items_cache)
    finally:
        service._shopping_items_cache = {}
    assert seen_a.get("stopped") is True and keys == [_TF_KEY], (seen_a, keys)
    assert res_a["_shopping_listing_count"] == 3, res_a["_shopping_listing_count"]
    assert "_shopping_listing_count" in res_b and res_b["_shopping_listing_count"] is None, (
        "R29: the cache holds only the OTHER product's key; this product's count is "
        "unknown, got %r" % (res_b.get("_shopping_listing_count", "<absent>"),))


# ---------------------------------------------------------------------------
# FIX ROUND 6 -- R31b: the captured / uncaptured bookkeeping is keyed by the
# `_get_price` key (`_lc_key`), never the display identity. A brand-repeating
# name is the shape where the two differ ('Tom Ford Tom Ford Oud Wood 100ml' is
# the `_get_price` key, 'Tom Ford Oud Wood 100ml' the dedup'd display name).
# ---------------------------------------------------------------------------
_TF_REPEAT = ("Tom Ford", "Tom Ford Oud Wood", "100ml")
_TF_REPEAT_KEY = "Tom Ford Tom Ford Oud Wood 100ml"


@pytest.mark.asyncio
@pytest.mark.parametrize("path,want", [("empty_us_fallback", None), ("supplements", None),
                                       ("three_matches", 3)])
async def test_b18_bookkeeping_is_keyed_by_the_get_price_key(monkeypatch, path, want):
    """PIN / KILL (R31b) -- a product whose display identity differs from its
    `_get_price` key: the REAL `_get_price` writes (and marks) the pool under
    its own key, and the stash reads the mark under that same key, so an empty
    us_fallback return and the supplements `[]` stash None while a non-empty
    three-match return stashes 3. Kills adversary r5's Q1 (the uncaptured check
    reads the display `full_name`: the empty rows read as captured -> 0) and
    M-B6's class on the count read."""
    brand, name, variant = _TF_REPEAT
    monkeypatch.setenv(FLAG, "true")
    _quiet_get_price_seams(monkeypatch)
    category = "fragrances"
    if path == "supplements":
        search, category = AsyncMock(side_effect=AssertionError("no shopping call")), "supplements"
    else:
        rows = [] if path == "empty_us_fallback" else list(MATCHED + UNMATCHED)
        search = AsyncMock(return_value={"shopping": rows, "organic": [],
                                         "shopping_region": "us_fallback"})
    gp, seen = _real_tier1(search, category=category)
    res = await _run_fetch(brand, name, variant, None, get_price_with_service=gp)
    assert _getprice_key(brand, name, variant) == _TF_REPEAT_KEY
    assert res.get("full_name") and res["full_name"] != _TF_REPEAT_KEY, res.get("full_name")
    assert seen.get("stopped") is True and list(seen.get("pools", {})) == [_TF_REPEAT_KEY], seen
    assert seen.get("uncaptured") == (set() if want else {_TF_REPEAT_KEY}), seen
    got = res.get("_shopping_listing_count", "<absent>")
    assert got == want and (got is None) == (want is None), (
        "R31b: stash under the _get_price key for %s = %r, want %r" % (path, got, want))
