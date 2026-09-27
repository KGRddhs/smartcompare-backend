"""W4-6a -- rubric truth: stop reporting measured data as missing.

Findings PO-RUBRIC-01 / -02 / -03 (P1) and PO-RUBRIC-08 (P2). Spec
`.qa-s68/specs/W4_6A_UNIT_SPEC.md` as corrected by its ADVERSARIAL SPEC REVIEW
(C1-C8) and bound by the FABLE RULINGS R1-R13 (2026-09-26, session 68).

Two flags, both default OFF, both read PER CALL (`.strip().lower()` in
{"1","true","yes","on"}):

* ENABLE_VALUE_DIM_PARTIAL_SIGNAL ("V", ruling R1 = correction C1) -- the value
  dimension leaves the EMITTED `missing_data` list only when EVERY product in the
  pair has a price AND `_spec_missing` is equal across the pair (the same value
  formula on both sides). Internal missingness reads stay legacy, so V moves no
  arithmetic.
* ENABLE_TIE_IS_NOT_MISSING ("T") -- a B0-A array tie-collapse fires only when
  the tied signal is SPARSE on every product (R6: fact_check buckets < 3;
  review_count not > 0; spec coverage < CATEGORY_MIN_COVERAGE), a presence-credit
  category (empty HIGHER/LOWER sets: fashion, other) always counts as sparse (R2),
  and the reader returns False whenever ENABLE_MISSING_DIM_RENORM is ON (R5).
  The PO-RUBRIC-08 guard G + G' (skip a dim the winner leads by more than 5) +
  the zero-margin rule ride EITHER flag (red-gate ruling R14: `V or T`, with the
  T reader still coupled to renorm, so under renorm the guard is on iff V is);
  the zero-margin rule is ELIGIBILITY before the pick (R15: a dim the loser
  leads by < 1.0 is skipped; nothing eligible -> no pair), so a sweep pair ships
  `tradeoffs: []` / `key_tradeoff: ""` under the guard (R16). Flag OFF
  `_loser_strongest_dim` is today's, byte for byte.

Fix round 1 (ruling R21) pins five ruled boundaries the adversary's mutants
A2/A5/A6/A11/A12 showed unpinned: the guard's `< 1.0` on the rounded margin,
`_spec_sparse`'s `<` coverage test and its NON_SCORING_SPEC_KEYS strip, the
four-bucket fact_check sum, and the V INFO line only when a dim was un-stamped.

Fix round 2 (ruling R23) pins four more details the round-1 adversary's mutants
B1/B2/B12/B13 showed unpinned: the guard rounds the lead BEFORE comparing it
(a float-noise 1.0 lead such as 64.1 - 63.1 stays eligible), a spec value of
"N/A" is not a populated field, and `specs_likely` / `specs_unverified` count
in the four-bucket fact_check sum.

Test kinds (each docstring names its kind and reason):
  RED  -- fails at the red tree (HEAD 04acb757) on an assertion naming the absent
          behaviour; green once the ruled design lands.
  PIN  -- green at HEAD and must stay green.
  KILL -- a PIN that is also the named killer of a mutation of the ruled design
          (the mutation row is in its docstring).
  XFAIL(strict) -- test 18, a pin OF THE LIMIT (ruling R4).

Every test is FREE: no network (autouse guard below + the process-wide
qaren_netguard plugin), no DB, no LLM. Always a FRESH `ScoringService()` --
never `get_scoring_service()` and never setattr on the singleton (#186 class).
The builders live in `tests/fixtures/_gen_rubric_truth_flag_off_digests.py`
(the E2 generator, single source; loaded by path, `app.*` imported lazily).
New W4-6a symbols are resolved INSIDE the test bodies, never at import.
"""
from __future__ import annotations

import copy
import importlib.util
import ipaddress
import json
import logging
import os
import socket

import pytest

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_FIXTURES_DIR = os.path.join(_TESTS_DIR, "fixtures")
_SCORING_LOGGER = "app.services.scoring_service"

V_FLAG = "ENABLE_VALUE_DIM_PARTIAL_SIGNAL"
T_FLAG = "ENABLE_TIE_IS_NOT_MISSING"
RENORM_FLAG = "ENABLE_MISSING_DIM_RENORM"
SPECNORM_FLAG = "ENABLE_SPEC_FIELD_NORM"
BADGE_FLAG = "ENABLE_CATEGORY_VALUE_BADGE"

# Every env name the scoring surface reads that could move these results.
_CLEARED_ENV = (
    V_FLAG, T_FLAG, RENORM_FLAG, SPECNORM_FLAG, "ENABLE_BUNDLE_C_SCORING", BADGE_FLAG,
    "ENABLE_BEHAVIORAL_DIM_TRANSLATION", "DISABLE_DIM_NORM_DAMPENING",
    "WINNER_DIM_GAP_TOLERANCE", "WINNER_PRICE_AUTHORITY_POINTS",
    "WINNER_VALUE_WEIGHT_SCALE", "ENABLE_WINNER_PROSE_RECONCILE",
)

_STATE_ENV = {
    "OFF": {},
    "V": {V_FLAG: "true"},
    "T": {T_FLAG: "true"},
    "VT": {V_FLAG: "true", T_FLAG: "true"},
    "R": {RENORM_FLAG: "true"},
    "RV": {RENORM_FLAG: "true", V_FLAG: "true"},
    "RT": {RENORM_FLAG: "true", T_FLAG: "true"},
    "RVT": {RENORM_FLAG: "true", V_FLAG: "true", T_FLAG: "true"},
    "S": {SPECNORM_FLAG: "true"},
    "ST": {SPECNORM_FLAG: "true", T_FLAG: "true"},
    "SVT": {SPECNORM_FLAG: "true", V_FLAG: "true", T_FLAG: "true"},
}


# ---------------------------------------------------------------------------
# autouse: zero network (socket + curl_cffi.requests.get)
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
    any curl_cffi GET, and fail the node on an attempt even if the code under
    test swallows the error."""
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
    except ImportError:  # pragma: no cover - pinned in requirements
        _curl_requests = None
    if _curl_requests is not None:
        monkeypatch.setattr(_curl_requests, "get", guarded_curl_get)
    yield
    assert not attempts, "zero-network guard: network attempted: %r" % (attempts,)


@pytest.fixture(autouse=True)
def _scoring_env_default_off(monkeypatch):
    """Deterministic default state regardless of a developer `.env`: every flag
    and knob the scoring surface reads is unset, and the process-cached bundle-C
    flag is reset so the cleared env is what is actually read."""
    for name in _CLEARED_ENV:
        monkeypatch.delenv(name, raising=False)
    from app.services import scoring_service
    monkeypatch.setattr(scoring_service, "_BUNDLE_C_SCORING_FLAG", None, raising=False)
    yield


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
_GEN_CACHE = {}


def _load_fixture_module(filename):
    if filename not in _GEN_CACHE:
        path = os.path.join(_FIXTURES_DIR, filename)
        spec = importlib.util.spec_from_file_location("w46a_" + filename[:-3].lstrip("_"), path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _GEN_CACHE[filename] = mod
    return _GEN_CACHE[filename]


def _gen():
    """The E2 generator = the single source of the W4-6a builders."""
    return _load_fixture_module("_gen_rubric_truth_flag_off_digests.py")


def _gen_on():
    return _load_fixture_module("_gen_rubric_truth_flag_on_golden.py")


def _svc():
    from app.services.scoring_service import ScoringService
    return ScoringService()


def _state(monkeypatch, state):
    for name in _CLEARED_ENV:
        monkeypatch.delenv(name, raising=False)
    for k, v in _STATE_ENV[state].items():
        monkeypatch.setenv(k, v)


def _require(name):
    from app.services import scoring_service
    fn = getattr(scoring_service, name, None)
    assert fn is not None, (
        "scoring_service.%s is absent -- the W4-6a reader/helper is not implemented" % name
    )
    return fn


def _scenario(name):
    return _gen().scenarios()[name]


def _run(svc, products):
    """compute_scores + the tradeoff/verdict/summary surfaces, on a deep copy."""
    from app.services.response_builder import deterministic_verdict_fields
    from app.services.scoring_service import build_dimensions_v2, count_missing_dim_cells
    p = copy.deepcopy(products)
    res = svc.compute_scores(p)
    cat = res.get("category", "other")
    names = _gen().product_names(p)
    tradeoffs = svc.compute_tradeoff_pairs(
        res.get("dimension_winners", {}), names, res.get("winner_index", 0), scores=res.get("scores"),
    )
    s0 = res["scores"]["product_0"]
    s1 = res["scores"]["product_1"]
    summary = svc.build_scores_summary(res, names)
    return {
        "res": res, "cat": cat, "names": names, "tradeoffs": tradeoffs,
        "key_tradeoff": deterministic_verdict_fields(res, names, tradeoffs).get("key_tradeoff"),
        "b0": s0["breakdown"], "b1": s1["breakdown"],
        "md0": list(s0.get("missing_data") or []), "md1": list(s1.get("missing_data") or []),
        "md_raw": [s0.get("missing_data"), s1.get("missing_data")],
        "overall": [s0["overall"], s1["overall"]],
        "dw": res.get("dimension_winners") or {},
        "summary_lines": [ln.strip() for ln in summary.splitlines()
                          if "Score winner" in ln or "Dimension leaders" in ln],
        "v2": [[d.get("key"), d.get("score_a"), d.get("score_b"), d.get("winner")]
               for d in build_dimensions_v2(p, res, cat)],
        "cells": count_missing_dim_cells(res, cat),
        "weights": s0["weights_used"],
    }


def _na_contributors(r, threshold=1.0):
    """Dims whose margin contribution |(b0-b1)*w| exceeds `threshold` and that
    resolve N/A in dimension_winners."""
    out = []
    for d, w in r["weights"].items():
        c = (r["b0"].get(d, 50) - r["b1"].get(d, 50)) * w
        if abs(c) > threshold and (r["dw"].get(d) or {}).get("winner") == "N/A":
            out.append(d)
    return out


def _records(*groups):
    g = _gen()
    recs = {}
    if "S" in groups:
        recs.update({"S:" + k: v for k, v in g.scenarios().items()})
    if "G" in groups:
        recs.update({"G:" + k: v for k, v in g.grid().items()})
    if "D" in groups:
        recs.update({"D:" + k: v for k, v in g.d2_records().items()})
    return recs


def _extras():
    g = _gen()
    P = g.prod
    E = g.ELEC_SPECS
    return {
        # M4 killer: both products all-missing and priced, one `estimated` -- the
        # flag-OFF authority exemption spares BOTH today; an implementation whose
        # exemption reads the V-filtered list penalises the estimate (55.0 -> 51.0).
        "X:both_priceonly_one_estimated": [
            P("Brand A", "Thing X", "electronics", None, None, None, None, 50.0, source_method="estimated"),
            P("Brand B", "Thing Y", "electronics", None, None, None, None, 50.0)],
        "X:nodata_estimated_vs_measured": [
            P("Brand A", "Thing X", "electronics", None, None, None, None, 50.0, source_method="estimated"),
            P("Brand B", "Thing Y", "electronics", E, 3.0, 40, {"specs_verified": 5}, 50.0)],
        "X:priceonly_vs_measured": [
            P("Brand A", "Phone X", "electronics", None, None, None, None, 50.0),
            P("Brand B", "Phone Y", "electronics", E, 4.5, 900, g.FULL_FC, 52.0)],
        "X:speconly_noprice_vs_measured": [
            P("Brand A", "Phone X", "electronics", E, 4.5, 900, g.FULL_FC, None),
            P("Brand B", "Phone Y", "electronics", g.BETTER_ELEC_SPECS, 4.0, 300, g.FULL_FC, 52.0)],
        "X:neither_vs_measured": [
            P("Brand A", "Phone X", "electronics", None, 4.5, 900, g.FULL_FC, None),
            P("Brand B", "Phone Y", "electronics", E, 4.0, 300, g.FULL_FC, 52.0)],
    }


def _boundary_pair(**kw):
    g = _gen()
    a = dict(brand="Brand A", name="Phone X", category="electronics", specs=g.ELEC_SPECS,
             rating=4.5, review_count=900, fact_check=g.FULL_FC, price=50.0)
    b = dict(a, brand="Brand B", name="Phone Y")
    a.update(kw.get("a", {}))
    b.update(kw.get("b", {}))
    return [g.prod(**a), g.prod(**b)]


def _post_collapse_flags(svc, products):
    """Per-product `_spec_missing` / `_price_missing` AFTER `_normalize_scores`
    (the collapse sets `_spec_missing`), on deep copies."""
    from app.services.extraction_service import canonicalize_category
    from app.services.scoring_service import CATEGORY_DIMENSIONS
    cat = canonicalize_category(products[0].get("category"))
    if cat not in CATEGORY_DIMENSIONS:
        cat = "other"
    raw = [svc._compute_raw_scores(copy.deepcopy(p), cat) for p in products]
    svc._normalize_scores(raw, copy.deepcopy(products), cat)
    return [bool(r.get("_spec_missing")) for r in raw], [bool(r.get("_price_missing")) for r in raw]


# ===========================================================================
# Readers
# ===========================================================================
@pytest.mark.parametrize("reader,flag", [
    ("_value_dim_partial_signal_enabled", V_FLAG),
    ("_tie_is_not_missing_enabled", T_FLAG),
])
def test_readers_default_off_and_parse(monkeypatch, reader, flag):
    """RED (test 1) -- both W4-6a readers exist, default OFF and parse per call:
    unset / "" / "false" / "0" => False; "true" / " TRUE " / "On" / "1" / "yes" =>
    True. RED at HEAD: the readers are absent."""
    fn = _require(reader)
    monkeypatch.delenv(flag, raising=False)
    assert fn() is False, "%s must default OFF" % reader
    for raw in ("", "false", "0", "no", "off"):
        monkeypatch.setenv(flag, raw)
        assert fn() is False, "%s(%r) must be False" % (reader, raw)
    for raw in ("true", " TRUE ", "On", "1", "yes"):
        monkeypatch.setenv(flag, raw)
        assert fn() is True, "%s(%r) must be True (read per call)" % (reader, raw)


def test_tie_reader_inert_under_missing_dim_renorm(monkeypatch):
    """RED (test 2, ruling R5) -- `_tie_is_not_missing_enabled()` is False whenever
    ENABLE_MISSING_DIM_RENORM is ON (uncoupled T re-opens the #101 inversion on
    8/9 unrated_vs_2star rows), True with T on and renorm unset. Kills M8.
    RED at HEAD: the reader is absent."""
    fn = _require("_tie_is_not_missing_enabled")
    monkeypatch.setenv(T_FLAG, "true")
    monkeypatch.setenv(RENORM_FLAG, "true")
    assert fn() is False, "T must be inert while ENABLE_MISSING_DIM_RENORM is ON"
    monkeypatch.delenv(RENORM_FLAG, raising=False)
    assert fn() is True, "T on, renorm unset => the T reader is True"


# ===========================================================================
# PO-RUBRIC-01 (V)
# ===========================================================================
@pytest.mark.parametrize("scenario", ["R01_identical_spec_50v52", "R01b_nospec_50v52"],
                         ids=["identical_spec", "no_spec"])
def test_decisive_dim_is_never_reported_missing(monkeypatch, scenario):
    """RED (test 3) -- V ON, R01 / R01b (both priced 50.0 vs 52.0, `_spec_missing`
    equal across the pair): `value_score` is in neither emitted list, its winner
    is "Brand A Phone X", and every dim contributing more than 1.0 point to the
    margin is un-stamped and not N/A. RED at HEAD: value_score stamped on both,
    N/A, while carrying the whole 14.0-point margin."""
    _state(monkeypatch, "V")
    r = _run(_svc(), _scenario(scenario))
    assert r["overall"] == [72.0, 58.0]
    assert "value_score" not in r["md0"] and "value_score" not in r["md1"], (
        "V ON: the decisive value dim is still reported missing: %r / %r" % (r["md0"], r["md1"]))
    assert r["dw"]["value_score"]["winner"] == "Brand A Phone X", r["dw"]["value_score"]
    for d, w in r["weights"].items():
        if abs((r["b0"][d] - r["b1"][d]) * w) > 1.0:
            assert d not in r["md0"] and d not in r["md1"], d
            assert r["dw"][d]["winner"] != "N/A", d


def test_scores_summary_names_the_value_leader(monkeypatch):
    """RED (test 4) -- V ON, R01: the verdict prompt attributes the clear lead:
    `value=Brand A Phone X`. RED at HEAD: `value=N/A` beside a clear lead."""
    _state(monkeypatch, "V")
    r = _run(_svc(), _scenario("R01_identical_spec_50v52"))
    assert r["summary_lines"] == [
        "Score winner: Brand A Phone X (clear lead)",
        "Dimension leaders: performance=N/A, value=Brand A Phone X, build quality=N/A, "
        "features=tie, ecosystem=N/A, future-proofing=tie",
    ], r["summary_lines"]


def test_value_flag_off_identity_R01():
    """PIN (test 5) -- flags OFF, R01 is today's output: the four stamps,
    value=N/A, both summary lines verbatim, overall [72.0, 58.0], margin 14.0.
    Kills M9 (T always on) and any V leak into the flag-OFF path."""
    r = _run(_svc(), _scenario("R01_identical_spec_50v52"))
    four = ["performance_score", "value_score", "build_quality_score", "ecosystem_score"]
    assert r["md0"] == four and r["md1"] == four
    assert r["dw"]["value_score"] == {"winner": "N/A", "margin": None}
    assert r["overall"] == [72.0, 58.0] and r["res"]["win_margin"] == 14.0
    assert r["summary_lines"] == [
        "Score winner: Brand A Phone X (clear lead)",
        "Dimension leaders: performance=N/A, value=N/A, build quality=N/A, features=tie, "
        "ecosystem=N/A, future-proofing=tie",
    ]


def _arith(r):
    return (r["overall"], r["res"]["win_margin"], r["res"]["winner_index"], r["b0"], r["b1"])


def test_value_flag_is_arithmetic_neutral(monkeypatch):
    """KILL (test 6; M4, M6) -- V moves NO arithmetic: over the 14 scenarios, the
    144 grid rows and the extra shapes, OFF vs V, R vs RV and T vs VT give equal
    `overall`, `win_margin`, `winner_index` and `breakdown`. Anchors:
    nodata_estimated_vs_measured [55.0, 68.8] and both_priceonly_one_estimated
    [55.0, 55.0] with V OFF and ON (renorm OFF). Green at HEAD (V inert).
    M4 (authority exemption reads the emitted list) reddens it on
    both_priceonly_one_estimated (55.0 -> 51.0); M6 (V inside
    `_signal_missing_for`) on nodata_vs_measured_good under renorm."""
    svc = _svc()
    recs = _records("S", "G")
    recs.update(_extras())
    for base_state, v_state in (("OFF", "V"), ("R", "RV"), ("T", "VT")):
        _state(monkeypatch, base_state)
        base = {k: _arith(_run(svc, v)) for k, v in recs.items()}
        _state(monkeypatch, v_state)
        moved = [k for k, v in recs.items() if _arith(_run(svc, v)) != base[k]]
        assert not moved, "%s -> %s moved arithmetic on %d records, first %r" % (
            base_state, v_state, len(moved), moved[:5])
    for st in ("OFF", "V"):
        _state(monkeypatch, st)
        assert _run(svc, recs["X:nodata_estimated_vs_measured"])["overall"] == [55.0, 68.8], st
        assert _run(svc, recs["X:both_priceonly_one_estimated"])["overall"] == [55.0, 55.0], st


@pytest.mark.parametrize("record,expected_value_missing,kind", [
    ("X:priceonly_vs_measured", [True, False], "PIN"),
    ("X:speconly_noprice_vs_measured", [True, False], "PIN"),
    ("X:neither_vs_measured", [True, False], "PIN"),
    ("S:R01b_nospec_50v52", [False, False], "RED"),
], ids=["price_only_stays_stamped", "spec_only_no_price_stays_stamped",
        "neither_leg_stays_stamped", "like_for_like_unstamped"])
def test_value_missing_only_when_both_legs_gone(monkeypatch, record, expected_value_missing, kind):
    """RED/PIN (test 7, the spec's id; semantics FLIPPED by ruling R1 / C1) -- V ON,
    electronics: the value dim leaves the emitted list ONLY for a like-for-like
    pair (every product priced AND `_spec_missing` equal). A price-only product
    against a measured partner, a spec-only product with no price, and a product
    with neither leg all STAY stamped (PIN rows: green at HEAD, where every
    one-legged value dim is stamped; they kill M2/M3/M14). The both-priced,
    both-spec-less pair (R01b) is un-stamped (RED row: stamped at HEAD)."""
    _state(monkeypatch, "V")
    recs = dict(_extras())
    recs.update(_records("S"))
    r = _run(_svc(), recs[record])
    got = ["value_score" in r["md0"], "value_score" in r["md1"]]
    assert got == expected_value_missing, (
        "%s [%s]: value_score in missing_data per product = %r, want %r (md0=%r md1=%r)"
        % (record, kind, got, expected_value_missing, r["md0"], r["md1"]))


_V_RESIDUAL_NA_ROWS = ["G:fashion|one_missing_price", "G:other|one_missing_price",
                       "G:supplements|both_no_price"]


@pytest.mark.parametrize("state", ["V", "VT"])
def test_no_na_dim_contributes_to_margin_grid(monkeypatch, state):
    """RED (test 8, ruling R1) -- V ON and VT ON over the 144 grid rows: the rows
    where a dim contributing more than 1.0 point resolves N/A are EXACTLY the 3
    that no label can make honest (fashion/other one_missing_price,
    supplements both_no_price: sentinel / no-price arithmetic, W4-6b's). RED at
    HEAD: 16 rows (sparse_vs_sparse x9, fashion/other both_full,
    extreme_price_ratio, one_missing_price, supplements both_no_price)."""
    _state(monkeypatch, state)
    svc = _svc()
    rows = sorted(k for k, v in _records("G").items() if _na_contributors(_run(svc, v)))
    assert rows == _V_RESIDUAL_NA_ROWS, "%s: %d N/A-contributor rows: %r" % (state, len(rows), rows)


@pytest.mark.parametrize("state", ["V", "VT", "RV"])
def test_value_flag_never_crowns_a_void_on_value(monkeypatch, state):
    """KILL (C1 PIN; M14 = the spec's per-product V rule, M2) -- under V no record
    crowns a product on its value dimension when that product has no price, or
    when its value is price-only (`_spec_missing`) against a spec-blended partner.
    Over the 14 scenarios, the 144 grid rows, the 6 d2 payloads and the extras.
    Green at HEAD (every one-legged value dim is stamped, so it can only lose by
    default); the spec's per-product rule crowned the void on 24 grid rows."""
    _state(monkeypatch, state)
    svc = _svc()
    recs = _records("S", "G", "D")
    recs.update(_extras())
    bad = []
    for k, products in recs.items():
        r = _run(svc, products)
        vd = svc.value_dim_for(r["cat"])
        winner = (r["dw"].get(vd) or {}).get("winner")
        if winner not in r["names"]:
            continue
        i = r["names"].index(winner)
        spec_missing, price_missing = _post_collapse_flags(svc, products)
        if price_missing[i] or (spec_missing[i] and not spec_missing[1 - i]):
            bad.append(k)
    assert not bad, "%s crowns a void/price-only product on value in %d records: %r" % (
        state, len(bad), bad[:8])


# ===========================================================================
# PO-RUBRIC-02 (T)
# ===========================================================================
def test_equal_strong_signal_is_not_reported_missing(monkeypatch):
    """RED (test 9) -- T ON, R02 (identical fully verified pair, 50.0 vs 50.0):
    nothing is missing; build_quality 100, performance 65.0, ecosystem 98.5,
    overall [78.7, 78.7]. RED at HEAD: 4 stamps, the three collapsed dims at 50,
    overall 67.0."""
    _state(monkeypatch, "T")
    r = _run(_svc(), _scenario("R02_identical_verified_50v50"))
    assert r["md_raw"] == [None, None], "T ON: equal measured signal still stamped: %r" % (r["md_raw"],)
    for b in (r["b0"], r["b1"]):
        assert b["build_quality_score"] == 100
        assert b["performance_score"] == 65.0
        assert b["ecosystem_score"] == 98.5
    assert r["overall"] == [78.7, 78.7]


def test_saturated_popularity_tie_is_not_missing(monkeypatch):
    """RED (test 10) -- T ON, the recorded products of
    comparison_baseline_d2_post_bucket_a__electronics.json (both popularity_raw
    1.0): `ecosystem_score` is in neither list and scores 100 / 100. RED at HEAD:
    stamped on both at the 50 sentinel."""
    _state(monkeypatch, "T")
    r = _run(_svc(), _gen().d2_records()["comparison_baseline_d2_post_bucket_a__electronics.json"])
    assert "ecosystem_score" not in r["md0"] and "ecosystem_score" not in r["md1"], (r["md0"], r["md1"])
    assert (r["b0"]["ecosystem_score"], r["b1"]["ecosystem_score"]) == (100, 100)


def test_near_tie_spec_is_not_missing(monkeypatch):
    """RED (test 11) -- T ON, battery 4100 vs 4000 mAh (spec_raw gap under the
    dampened tie tolerance, both 65.0): 0 stamps, performance 65.0 / 65.0.
    RED at HEAD: 4 stamps."""
    _state(monkeypatch, "T")
    near = dict(_gen().ELEC_SPECS, battery="4100 mAh")
    r = _run(_svc(), _boundary_pair(b={"specs": near}))
    assert r["md_raw"] == [None, None], r["md_raw"]
    assert (r["b0"]["performance_score"], r["b1"]["performance_score"]) == (65.0, 65.0)


def test_sparse_tie_still_collapses(monkeypatch):
    """KILL (test 12; M10a-c) -- T ON, R02c (2/11 fields, fact_check
    {specs_unverified: 1}, review_count None): the same 4 stamps and the same
    breakdown as flags OFF -- B0-A behaviour kept for sparse evidence. Green at
    HEAD; a sparsity helper forced "not sparse" reddens it."""
    svc = _svc()
    off = _run(svc, _scenario("R02c_sparse_identical"))
    _state(monkeypatch, "T")
    on = _run(svc, _scenario("R02c_sparse_identical"))
    four = ["performance_score", "value_score", "build_quality_score", "ecosystem_score"]
    assert on["md0"] == four and on["md1"] == four, (on["md0"], on["md1"])
    assert (on["b0"], on["b1"]) == (off["b0"], off["b1"])


_BOUNDARY_ROWS = [
    # id, pair kwargs, T-ON missing_data of BOTH products
    ("fc_total_2", {"a": {"fact_check": {"specs_verified": 2}}, "b": {"fact_check": {"specs_verified": 2}}},
     ["build_quality_score"]),
    ("fc_total_3", {"a": {"fact_check": {"specs_verified": 3}}, "b": {"fact_check": {"specs_verified": 3}}},
     None),
    ("rc_none_sources2", {"a": {"review_count": None, "sources": 2}, "b": {"review_count": None, "sources": 2}},
     ["ecosystem_score"]),
    ("rc_zero", {"a": {"review_count": 0}, "b": {"review_count": 0}}, ["ecosystem_score"]),
    ("rc_1500_vs_2500", {"a": {"review_count": 1500}, "b": {"review_count": 2500}}, None),
    ("cov_6_of_11", "six", None),
    ("cov_5_of_11", "five", ["performance_score", "value_score"]),
    ("near_tie_battery_4100", "near", None),
]


@pytest.mark.parametrize("row_id,kw,expected", _BOUNDARY_ROWS, ids=[r[0] for r in _BOUNDARY_ROWS])
def test_sparsity_boundaries(monkeypatch, row_id, kw, expected):
    """RED (test 13, reclassified by ruling R10 / C4) -- the 8 boundary rows of
    spec section 3.2, each asserting the EXACT T-ON `missing_data` of both
    products (only the sparse signal stays stamped; the dense ones un-collapse).
    Every row is RED at HEAD, where all 8 carry the same 4 stamps. Kills M10a-f
    and M13 (fact_check `< 3` -> `<= 3` reddens fc_total_3)."""
    g = _gen()
    if kw == "six":
        specs = {k: g.ELEC_SPECS[k] for k in list(g.ELEC_SPECS)[:6]}
        kw = {"a": {"specs": specs}, "b": {"specs": specs}}
    elif kw == "five":
        specs = {k: g.ELEC_SPECS[k] for k in list(g.ELEC_SPECS)[:5]}
        kw = {"a": {"specs": specs}, "b": {"specs": specs}}
    elif kw == "near":
        kw = {"b": {"specs": dict(g.ELEC_SPECS, battery="4100 mAh")}}
    _state(monkeypatch, "T")
    r = _run(_svc(), _boundary_pair(**kw))
    assert r["md_raw"] == [expected, expected], "%s: T-ON missing_data %r, want %r on both" % (
        row_id, r["md_raw"], expected)


_MIXED_ROWS = [
    # id, pair kwargs (product A SPARSE on the signal, product B DENSE, equal score), (dim, T-ON value)
    ("reliability", {"a": {"fact_check": {"specs_verified": 2}}, "b": {"fact_check": {"specs_verified": 5}}},
     ("build_quality_score", 100)),
    ("popularity", {"a": {"review_count": None, "sources": 2}, "b": {"review_count": 1, "sources": 2}},
     ("ecosystem_score", 10.0)),
    ("spec", "six_vs_five", ("performance_score", 65.0)),
]


@pytest.mark.parametrize("row_id,kw,dim_value", _MIXED_ROWS, ids=[r[0] for r in _MIXED_ROWS])
def test_mixed_sparsity_tie_is_kept(monkeypatch, row_id, kw, dim_value):
    """RED (spec 3.2: the collapse fires only when the tied signal is sparse on
    EVERY product) -- T ON, an equal score where ONE product is sparse on the
    signal and the other dense (fact_check 2 vs 5 buckets; review_count None vs
    1, both with 2 source ratings; 6/11 vs 5/11 spec fields with a near-equal
    spec_raw): the tie is kept, nothing is stamped. RED at HEAD: 4 stamps.
    Kills the sparsity rule read as "ANY product sparse" (all -> any)."""
    g = _gen()
    if kw == "six_vs_five":
        six = {k: g.ELEC_SPECS[k] for k in list(g.ELEC_SPECS)[:6]}
        five = dict({k: g.ELEC_SPECS[k] for k in list(g.ELEC_SPECS)[:5]}, battery="3500 mAh")
        kw = {"a": {"specs": five}, "b": {"specs": six}}
    _state(monkeypatch, "T")
    r = _run(_svc(), _boundary_pair(**kw))
    assert r["md_raw"] == [None, None], "%s: mixed-sparsity tie still collapsed: %r" % (row_id, r["md_raw"])
    dim, value = dim_value
    assert (r["b0"][dim], r["b1"][dim]) == (value, value), (row_id, r["b0"][dim], r["b1"][dim])


def _schema_specs(category, n, heat=False):
    """The first `n` SCORING fields of the category schema (schema order, minus
    NON_SCORING_SPEC_KEYS), each a populated string; `heat` adds the non-scoring
    `heat_stability` key."""
    from app.services.extraction_service import CATEGORY_SPEC_SCHEMAS
    from app.services.scoring_service import NON_SCORING_SPEC_KEYS
    fields = [f for f in CATEGORY_SPEC_SCHEMAS[category] if f not in NON_SCORING_SPEC_KEYS][:n]
    specs = {f: "x %d" % i for i, f in enumerate(fields)}
    if heat:
        specs["heat_stability"] = "Good in Gulf heat"
    return specs


def _same_spec_pair(category, specs, fact_check=None):
    """Two products identical but for brand/name: the given specs, 4.5 stars /
    900 reviews, the given fact_check (default FULL_FC), 50.0 BHD each."""
    g = _gen()
    fc = g.FULL_FC if fact_check is None else fact_check
    return [g.prod("Brand A", "Item X", category, specs, 4.5, 900, fc, 50.0),
            g.prod("Brand B", "Item Y", category, specs, 4.5, 900, fc, 50.0)]


def test_spec_coverage_equal_to_threshold_is_not_sparse(monkeypatch):
    """KILL (ruling R21, adversary r0 A5: `_spec_sparse` coverage `<` -> `<=`) --
    `_spec_sparse` tests coverage with `<` exactly as `_score_specs` applies its
    coverage penalty, so a coverage EQUAL to CATEGORY_MIN_COVERAGE is dense. The
    reachable equality among direction-bearing categories is fragrances 3/10 ==
    0.3 (supplements has 11 scoring fields, so 4/11 < 0.4 and 5/11 > 0.4 -- no
    supplements equality exists). T ON, an identical fully verified fragrance pair
    with 3 of 10 scoring fields keeps its spec tie (nothing stamped); 2 of 10 stays
    sparse (character + wear_value stamped). RED at the red tree (T inert: 4
    stamps); `<=` makes 3/10 sparse and reddens it."""
    from app.services.scoring_service import CATEGORY_MIN_COVERAGE
    spec_sparse = _require("_spec_sparse")
    assert 3 / 10 == CATEGORY_MIN_COVERAGE["fragrances"]
    assert spec_sparse({"specs": _schema_specs("fragrances", 3)}, "fragrances") is False
    assert spec_sparse({"specs": _schema_specs("fragrances", 2)}, "fragrances") is True
    _state(monkeypatch, "T")
    svc = _svc()
    at = _run(svc, _same_spec_pair("fragrances", _schema_specs("fragrances", 3)))
    assert at["md_raw"] == [None, None], "coverage == threshold collapsed as sparse: %r" % (at["md_raw"],)
    below = _run(svc, _same_spec_pair("fragrances", _schema_specs("fragrances", 2)))
    assert below["md_raw"] == [["character_score", "wear_value_score"]] * 2, below["md_raw"]


def test_spec_na_string_is_not_a_populated_field(monkeypatch):
    """KILL (ruling R23, adversary r1 B2: `_spec_sparse` counts a field whose
    value is the string "N/A" as populated) -- spec 3.2: a field counts when it
    is truthy AND != "N/A". A fragrance whose 3 filled scoring fields (exactly
    the 3/10 == 0.3 threshold) include one "N/A" has 2 real fields and is
    SPARSE; 3 real fields plus a fourth "N/A" is dense (the "N/A" moves neither
    way). T ON, an identical fully verified pair with the "N/A" product collapses
    its spec tie exactly like the 2-field pair (character + wear_value stamped).
    RED at the red tree (T inert: 4 stamps); counting "N/A" reads 3/10 (dense),
    keeps the tie and reddens it."""
    spec_sparse = _require("_spec_sparse")
    at = _schema_specs("fragrances", 3)
    with_na = dict(at, **{list(at)[0]: "N/A"})
    four = _schema_specs("fragrances", 4)
    three_plus_na = dict(four, **{list(four)[3]: "N/A"})
    assert spec_sparse({"specs": with_na}, "fragrances") is True
    assert spec_sparse({"specs": three_plus_na}, "fragrances") is False
    _state(monkeypatch, "T")
    r = _run(_svc(), _same_spec_pair("fragrances", with_na))
    assert r["md_raw"] == [["character_score", "wear_value_score"]] * 2, (
        "an 'N/A' spec value counted as populated: %r" % (r["md_raw"],))


def test_reliability_bucket_sum_counts_specs_flagged(monkeypatch):
    """KILL (ruling R21 / R6, adversary r0 A6: `specs_flagged` dropped from the
    fact_check bucket sum) -- the reliability sparsity total is the FOUR spec
    buckets (verified + likely + flagged + unverified), so a fact_check whose only
    non-zero bucket is `specs_flagged: 3` is dense and `specs_flagged: 2` sparse.
    T ON, an identical pair carrying `{specs_flagged: 3}` keeps its reliability
    tie (nothing stamped); `{specs_flagged: 2}` collapses it (build_quality
    stamped). RED at the red tree (T inert: 4 stamps); the three-bucket sum reads
    0 and reddens it."""
    rel_sparse = _require("_reliability_sparse")
    assert rel_sparse({"fact_check": {"specs_flagged": 3}}) is False
    assert rel_sparse({"fact_check": {"specs_flagged": 2}}) is True
    _state(monkeypatch, "T")
    svc = _svc()
    elec = _gen().ELEC_SPECS
    dense = _run(svc, _same_spec_pair("electronics", elec, {"specs_flagged": 3}))
    assert dense["md_raw"] == [None, None], "flagged-only fact_check read as sparse: %r" % (dense["md_raw"],)
    sparse = _run(svc, _same_spec_pair("electronics", elec, {"specs_flagged": 2}))
    assert sparse["md_raw"] == [["build_quality_score"]] * 2, sparse["md_raw"]


@pytest.mark.parametrize("bucket,tied_value", [("specs_likely", 70.0), ("specs_unverified", 30.0)],
                         ids=["likely", "unverified"])
def test_reliability_bucket_sum_counts_likely_and_unverified(monkeypatch, bucket, tied_value):
    """KILL (ruling R23 / R6, adversary r1 B13 / B12: `specs_likely` or
    `specs_unverified` dropped from the fact_check bucket sum) -- one node per
    bucket: a fact_check whose ONLY non-zero bucket is that one, at the threshold
    (3), is dense; at 2 it is sparse. T ON, an identical fully specced pair
    carrying `{<bucket>: 3}` keeps its reliability tie (nothing stamped,
    build_quality = the measured tie: 70.0 likely-only, 30.0 unverified-only);
    `{<bucket>: 2}` collapses it (build_quality stamped). RED at the red tree (T
    inert: 4 stamps); the sum without that bucket reads 0 and reddens it."""
    rel_sparse = _require("_reliability_sparse")
    assert rel_sparse({"fact_check": {bucket: 3}}) is False
    assert rel_sparse({"fact_check": {bucket: 2}}) is True
    _state(monkeypatch, "T")
    svc = _svc()
    elec = _gen().ELEC_SPECS
    dense = _run(svc, _same_spec_pair("electronics", elec, {bucket: 3}))
    assert dense["md_raw"] == [None, None], "%s-only fact_check read as sparse: %r" % (bucket, dense["md_raw"])
    assert (dense["b0"]["build_quality_score"], dense["b1"]["build_quality_score"]) == (tied_value, tied_value)
    sparse = _run(svc, _same_spec_pair("electronics", elec, {bucket: 2}))
    assert sparse["md_raw"] == [["build_quality_score"]] * 2, sparse["md_raw"]


def test_spec_coverage_is_measured_on_scoring_keys_only(monkeypatch):
    """KILL (ruling R21, adversary r0 A12: `_spec_sparse` stops stripping
    NON_SCORING_SPEC_KEYS) -- coverage is measured on the schema's SCORING fields
    only (the `_score_specs` field selection), so the non-scoring `heat_stability`
    key moves neither the numerator nor the denominator. skincare (10 scoring
    fields, threshold 0.35) with 3 scoring fields plus `heat_stability` is sparse
    (3/10; counting the key would read 4/11 = 0.364, dense); makeup (11 scoring
    fields, 0.35) with 4 scoring fields is dense (4/11; the un-stripped schema
    would read 4/12 = 0.333, sparse). T ON the same holds for identical fully
    verified pairs. RED at the red tree (T inert: 4 stamps)."""
    from app.services.extraction_service import CATEGORY_SPEC_SCHEMAS
    from app.services.scoring_service import NON_SCORING_SPEC_KEYS
    spec_sparse = _require("_spec_sparse")
    assert "heat_stability" in NON_SCORING_SPEC_KEYS
    assert "heat_stability" in CATEGORY_SPEC_SCHEMAS["skincare"]
    assert "heat_stability" in CATEGORY_SPEC_SCHEMAS["makeup"]
    assert spec_sparse({"specs": _schema_specs("skincare", 3, heat=True)}, "skincare") is True
    assert spec_sparse({"specs": _schema_specs("makeup", 4)}, "makeup") is False
    _state(monkeypatch, "T")
    svc = _svc()
    skin = _run(svc, _same_spec_pair("skincare", _schema_specs("skincare", 3, heat=True)))
    assert skin["md_raw"] == [["actives_score", "results_value_score"]] * 2, skin["md_raw"]
    makeup = _run(svc, _same_spec_pair("makeup", _schema_specs("makeup", 4)))
    assert makeup["md_raw"] == [None, None], makeup["md_raw"]


def test_tie_flag_restores_scoring_v2_rows(monkeypatch):
    """RED (test 14) -- T ON, R02: the phone's `scoring_v2.dimensions` rows regain
    the three silently omitted dims (performance 65.0/65.0, build_quality 100/100,
    ecosystem 98.5/98.5): 8 keys. RED at HEAD: 5 rows."""
    _state(monkeypatch, "T")
    r = _run(_svc(), _scenario("R02_identical_verified_50v50"))
    assert [row[0] for row in r["v2"]] == [
        "price", "reviews", "value", "performance", "build_quality", "feature", "ecosystem", "futureproof"], r["v2"]
    rows = {row[0]: row[1:3] for row in r["v2"]}
    assert rows["performance"] == [65.0, 65.0]
    assert rows["build_quality"] == [100, 100]
    assert rows["ecosystem"] == [98.5, 98.5]


def test_tie_flag_inert_under_renorm(monkeypatch):
    """KILL (test 15; M8, gate E4) -- ENABLE_MISSING_DIM_RENORM ON + T ON is
    identical to renorm ON alone: the full `compute_scores` output AND the
    tradeoff pairs (G rides the coupled T reader) over the 144 grid rows and the
    14 scenarios; `electronics|unrated_vs_2star` keeps R's [58.3, 58.3], winner 1.
    Green at HEAD; uncoupled T flips it to [70.9, 68.4], winner 0."""
    svc = _svc()
    recs = _records("S", "G")

    def snap(products):
        r = _run(svc, products)
        return json.loads(json.dumps(r["res"])), r["tradeoffs"]

    _state(monkeypatch, "R")
    base = {k: snap(v) for k, v in recs.items()}
    _state(monkeypatch, "RT")
    moved = [k for k, v in recs.items() if snap(v) != base[k]]
    assert not moved, "renorm+T differs from renorm on %d records: %r" % (len(moved), moved[:5])
    r = _run(svc, recs["G:electronics|unrated_vs_2star"])
    assert r["overall"] == [58.3, 58.3] and r["res"]["winner_index"] == 1


def test_tie_flag_composes_with_spec_field_norm(monkeypatch):
    """RED (test 16) -- S ON + T ON, the identical-spec fixture of
    tests/test_scoring_spec_field_normalization.py::test_identical_specs_still_collapse_to_tie
    (7/11 fields, 4.5 / 1000 reviews): the dense spec tie is kept --
    `_spec_missing` is not set, `performance_score` is not in `missing_data` and
    scores 65.0 / 65.0. RED at HEAD: collapsed (the S-alone pin stays S-alone)."""
    from tests import test_scoring_spec_field_normalization as sf
    specs = dict(sf._COMMON_ELECTRONICS_FIELDS, battery="4500 mAh")
    products = [sf._make_phone("A", None, specs=dict(specs)), sf._make_phone("B", None, specs=dict(specs))]
    _state(monkeypatch, "ST")
    svc = _svc()
    raw = [svc._compute_raw_scores(copy.deepcopy(p), "electronics") for p in products]
    svc._normalize_scores(raw, copy.deepcopy(products), "electronics")
    assert not raw[0].get("_spec_missing") and not raw[1].get("_spec_missing"), (
        "S+T: a dense identical-spec tie is still collapsed to missing")
    r = _run(svc, products)
    assert "performance_score" not in r["md0"] and "performance_score" not in r["md1"]
    assert (r["b0"]["performance_score"], r["b1"]["performance_score"]) == (65.0, 65.0)


# ===========================================================================
# PO-RUBRIC-03 (fashion / other)
# ===========================================================================
_PRESENCE = [("R03_fashion_oxford_v_pu_real", "craft_score", "cpw_score"),
             ("R03c_other_alu_v_abs_real", "function_score", "value_score")]


@pytest.mark.parametrize("scenario,spec_dim,value_dim", _PRESENCE, ids=["fashion", "other"])
def test_fashion_other_presence_credit_tie_stays_stamped(monkeypatch, scenario, spec_dim, value_dim):
    """KILL (test 17, craft/function half -- ruling R2 = C2; M15) -- T ON, R03 / R03c:
    fashion/other have no numeric spec direction, so `spec_raw` 1.0 == 1.0 is
    presence credit, not a measured tie: the spec dim STAYS stamped at 50 / 50
    on both products and the overall is today's. Green at HEAD; removing the
    presence-credit exemption from the spec sparsity helper reddens it (craft
    65.0 == 65.0 shown as a merit tie, R03's winner flips)."""
    svc = _svc()
    off = _run(svc, _scenario(scenario))
    _state(monkeypatch, "T")
    on = _run(svc, _scenario(scenario))
    assert spec_dim in on["md0"] and spec_dim in on["md1"], (on["md0"], on["md1"])
    assert (on["b0"][spec_dim], on["b1"][spec_dim]) == (50, 50)
    assert on["overall"] == off["overall"] and on["res"]["winner_index"] == off["res"]["winner_index"]


@pytest.mark.parametrize("scenario,spec_dim,value_dim", _PRESENCE, ids=["fashion", "other"])
def test_fashion_other_value_leg_not_reported_missing(monkeypatch, scenario, spec_dim, value_dim):
    """RED (test 17, VT half) -- VT ON, R03 / R03c (both priced, `_spec_missing`
    equal because the presence-credit spec tie stays collapsed): the value leg
    (`cpw_score` / `value_score`) is in neither list; the spec dim stays stamped.
    RED at HEAD: the value leg is stamped on both (N/A with a -7.0 / -10.5
    contribution)."""
    _state(monkeypatch, "VT")
    r = _run(_svc(), _scenario(scenario))
    assert value_dim not in r["md0"] and value_dim not in r["md1"], (r["md0"], r["md1"])
    assert spec_dim in r["md0"] and spec_dim in r["md1"]


@pytest.mark.xfail(strict=True, reason=(
    "PO-RUBRIC-03 limit (ruling R4 / open question 2): fashion/other have no numeric "
    "spec discriminator, so two different products tie on craft/function under any "
    "W4-6a flag state; separation needs a non-numeric merit table (W4-6c, Ahmed's "
    "product call). strict=True: the day a discriminator lands this XPASSes."))
def test_spec_dim_can_separate_two_fashion_products(monkeypatch):
    """XFAIL(strict) (test 18) -- a pin OF THE LIMIT: VT ON, R03 (Italian
    hand-welted calfskin vs glued PU) => |craft_0 - craft_1| > 3.0. Fails at HEAD
    (50 == 50) and under this unit (the collapse is kept, 50 == 50)."""
    _state(monkeypatch, "VT")
    r = _run(_svc(), _scenario("R03_fashion_oxford_v_pu_real"))
    assert abs(r["b0"]["craft_score"] - r["b1"]["craft_score"]) > 3.0


def test_fashion_price_leg_restored(monkeypatch):
    """RED (test 19) -- V ON, R03: `cpw_score` is in neither list, its winner is
    "Brand B Oxford Two", and the phone rows gain ["cpw", 30.0, 100.0, 1] (the
    8-row cap has room because craft stays omitted). RED at HEAD: cpw N/A, no row."""
    _state(monkeypatch, "V")
    r = _run(_svc(), _scenario("R03_fashion_oxford_v_pu_real"))
    assert "cpw_score" not in r["md0"] and "cpw_score" not in r["md1"], (r["md0"], r["md1"])
    assert r["dw"]["cpw_score"]["winner"] == "Brand B Oxford Two", r["dw"]["cpw_score"]
    assert ["cpw", 30.0, 100.0, 1] in r["v2"], r["v2"]


# ===========================================================================
# PO-RUBRIC-08 (G + G' + zero-margin, riding T -- ruling R3)
# ===========================================================================
_R08_OFF = {"R08d_loser_sparse_best_is_sentinel": 50, "R08e_loser_sparse_fc_mix": 40.0}


@pytest.mark.parametrize("scenario", sorted(_R08_OFF), ids=["R08d", "R08e"])
def test_loser_strongest_dim_never_names_a_missing_dim(monkeypatch, scenario):
    """RED (test 20, corrected target per ruling R3) -- flag OFF the fallback is
    today's byte for byte (`loser_wins` = the build_quality 50 sentinel, margin
    50 / 40.0, "stays competitive on build quality."). T ON: the void is skipped,
    performance (45.0 vs the winner's 85.0) is skipped by G', and no zero-margin
    claim is left -- `tradeoffs == []`, `key_tradeoff == ""`; never "stays
    competitive on performance" at 45 vs 85. RED at HEAD: the void is named."""
    svc = _svc()
    off = _run(svc, _scenario(scenario))
    assert off["tradeoffs"][0]["loser_wins"] == {
        "dimension": "build_quality_score", "product": "Brand B Phone Y", "margin": _R08_OFF[scenario]}
    assert off["key_tradeoff"] == "Brand B Phone Y stays competitive on build quality."
    _state(monkeypatch, "T")
    on = _run(svc, _scenario(scenario))
    loser_md = on["md1"] if on["res"]["winner_index"] == 0 else on["md0"]
    named = [p["loser_wins"]["dimension"] for p in on["tradeoffs"]]
    assert not [d for d in named if d in loser_md], (
        "T ON: the runner-up card names a dimension the payload declares missing: %r" % named)
    assert on["tradeoffs"] == [], on["tradeoffs"]
    assert on["key_tradeoff"] == ""
    assert "stays competitive on performance" not in on["key_tradeoff"]


def _hand_scores(winner_breakdown, loser_breakdown, loser_md=None, winner_md=None):
    return {
        "product_0": {"overall": 80.0, "breakdown": dict(winner_breakdown), "missing_data": winner_md},
        "product_1": {"overall": 60.0, "breakdown": dict(loser_breakdown), "missing_data": loser_md},
    }


def test_loser_strongest_dim_returns_none_when_only_voids_remain(monkeypatch):
    """RED (test 21) -- T ON, hand-built: every numeric loser dim is in its
    `missing_data` => `_loser_strongest_dim` is None, `compute_tradeoff_pairs(...,
    scores=)` is [] and `key_tradeoff` is "". RED at HEAD: the 50 sentinel is
    named as the runner-up's strength."""
    from app.services.response_builder import deterministic_verdict_fields
    _state(monkeypatch, "T")
    svc = _svc()
    scores = _hand_scores({"a_score": 90.0, "b_score": 80.0, "c_score": 70.0},
                          {"a_score": 50, "b_score": 50, "c_score": 50},
                          loser_md=["a_score", "b_score", "c_score"])
    assert svc._loser_strongest_dim(scores, 0, "Loser L") is None
    dw = {"a_score": {"winner": "Winner W", "margin": 40.0},
          "b_score": {"winner": "Winner W", "margin": 30.0},
          "c_score": {"winner": "Winner W", "margin": 20.0}}
    pairs = svc.compute_tradeoff_pairs(dw, ["Winner W", "Loser L"], 0, scores=scores)
    assert pairs == []
    result = {"scores": scores, "winner_index": 0}
    assert deterministic_verdict_fields(result, ["Winner W", "Loser L"], pairs)["key_tradeoff"] == ""


def test_loser_strongest_dim_skips_dim_absent_from_winner(monkeypatch):
    """RED (test 22; M11b) -- T ON, hand-built: the loser's highest dim is absent
    from the winner's breakdown => skipped; the next real dim (loser leads 70 vs
    60) is chosen with margin 10.0. RED at HEAD: the absent dim is named, margin 0."""
    _state(monkeypatch, "T")
    got = _svc()._loser_strongest_dim(
        _hand_scores({"a_score": 60.0, "z_score": 95.0}, {"x_score": 90.0, "a_score": 70.0}), 0, "Loser L")
    assert got == {"dimension": "a_score", "product": "Loser L", "margin": 10.0}, got


def test_loser_strongest_dim_skips_dim_the_winner_leads(monkeypatch):
    """RED (G' of ruling R3) -- T ON, hand-built: the loser's best dim is one
    the WINNER leads by more than 5 (a: 80 vs 90) => skipped; the next dim is a
    real loser lead (b: 62 vs 60) => chosen with margin 2.0. RED at HEAD: a is
    named with margin 0 (a "competitive" claim on a dim the winner leads by 10).
    Under R15 (a dim the loser leads by < 1.0 is ineligible before the pick) G'
    is the strict subset "winner leads by > 5" of that one eligibility rule, so
    a G'-only removal is an equivalent mutant; the eligibility rule relaxed to
    G' alone (M18) reddens this file via the zero-margin rows."""
    _state(monkeypatch, "T")
    got = _svc()._loser_strongest_dim(
        _hand_scores({"a_score": 90.0, "b_score": 60.0}, {"a_score": 80.0, "b_score": 62.0}), 0, "Loser L")
    assert got == {"dimension": "b_score", "product": "Loser L", "margin": 2.0}, got


def test_loser_strongest_dim_drops_zero_margin_claim(monkeypatch):
    """RED (zero-margin rule of ruling R3, folds PO-RUBRIC-08b) -- T ON, hand-built:
    every eligible loser dim is a tie or a small deficit (70 vs 70, 60 vs 62) =>
    no `loser_wins` with margin < 1.0 is emitted: None. RED at HEAD: a is named
    at margin 0 ("stays competitive" on a tie)."""
    _state(monkeypatch, "T")
    got = _svc()._loser_strongest_dim(
        _hand_scores({"a_score": 70.0, "b_score": 62.0}, {"a_score": 70.0, "b_score": 60.0}), 0, "Loser L")
    assert got is None, got


def test_loser_real_strength_unchanged(monkeypatch):
    """KILL (test 23) -- flags OFF: R03's tradeoffs are today's exact pair
    (durability 29.0 vs style 21.9) and R08c's fallback names performance at
    margin 0 (today's F4.2 copy, untouched OFF). T ON: R03's real strength is
    still named, unchanged (G/G' never drop a measured loser lead)."""
    svc = _svc()
    r03_pair = [{"loser_wins": {"dimension": "durability_score", "margin": 29.0, "product": "Maison A Oxford One"},
                 "winner_wins": {"dimension": "style_score", "margin": 21.9, "product": "Brand B Oxford Two"}}]
    assert _run(svc, _scenario("R03_fashion_oxford_v_pu_real"))["tradeoffs"] == r03_pair
    r08c = _run(svc, _scenario("R08c_loser_has_real_strength"))
    assert r08c["tradeoffs"][0]["loser_wins"] == {
        "dimension": "performance_score", "margin": 0, "product": "Brand B Phone Y"}
    _state(monkeypatch, "T")
    assert _run(svc, _scenario("R03_fashion_oxford_v_pu_real"))["tradeoffs"] == r03_pair


def test_loser_genuine_fifty_is_still_eligible(monkeypatch):
    """KILL (test 24; M12) -- T ON, hand-built: the loser's best dim is a REAL 50.0
    (a 2.5-star review normalizes to exactly 50.0) that is NOT in its
    `missing_data` and that it leads 50.0 vs 42.0 => still chosen, margin 8.0.
    Green at HEAD (no guard); a value-equality guard (`val == MISSING_SCORE`)
    drops it."""
    _state(monkeypatch, "T")
    got = _svc()._loser_strongest_dim(
        _hand_scores({"review_score": 42.0, "value_score": 90.0}, {"review_score": 50.0, "value_score": 40.0}),
        0, "Loser L")
    assert got == {"dimension": "review_score", "product": "Loser L", "margin": 8.0}, got


@pytest.mark.parametrize("state", ["V", "T", "VT", "RV"])
def test_no_same_dimension_tradeoff_pair(monkeypatch, state):
    """KILL (C6 M16 PIN) -- V / T / VT / RV ON (the guard rides either flag, R14),
    over the 14 scenarios, 144 grid rows and 6 d2 payloads: no tradeoff pair has
    `loser_wins.dimension == winner_wins.dimension` ("X wins value by 70" beside
    "Y stays competitive on value"). Green at HEAD (0 records)."""
    _state(monkeypatch, state)
    svc = _svc()
    bad = [k for k, v in _records("S", "G", "D").items()
           if any(p["loser_wins"]["dimension"] == p["winner_wins"]["dimension"] for p in _run(svc, v)["tradeoffs"])]
    assert not bad, bad


@pytest.mark.parametrize("state", ["V", "T", "VT", "RV"])
def test_no_void_or_zero_margin_loser_claim_over_records(monkeypatch, state):
    """RED (rulings R3 + R14 over the record set; the V and RV rows are R14's pins
    and R17's renorm + V twin) -- V / T / VT / RV ON, over the 169 records (14
    scenarios, 144 grid rows, 6 d2 payloads, 5 extras): no `loser_wins` names a
    dim in the loser's own `missing_data`, and none carries a margin < 1.0.
    RED at HEAD: 66 records carry a margin-0 "stays competitive" claim and 2
    (R08d/R08e) name the void. The guard gated on T alone reddens the V and RV
    rows (measured on the prototype: 11 void-named records, 77 / 78 margin-0
    claims)."""
    _state(monkeypatch, state)
    svc = _svc()
    void, zero = [], []
    recs = _records("S", "G", "D")
    recs.update(_extras())
    assert len(recs) == 169
    for k, v in recs.items():
        r = _run(svc, v)
        loser_md = r["md1"] if r["res"]["winner_index"] == 0 else r["md0"]
        for p in r["tradeoffs"]:
            if p["loser_wins"]["dimension"] in loser_md:
                void.append(k)
            if p["loser_wins"]["margin"] < 1.0:
                zero.append(k)
    assert not void, "%s: void named as the runner-up's strength: %r" % (state, void)
    assert not zero, "%s: %d records with a margin<1.0 'stays competitive' claim, first %r" % (
        state, len(zero), zero[:5])


@pytest.mark.parametrize("state", ["V", "T"])
def test_zero_margin_dim_is_ineligible_before_the_pick(monkeypatch, state):
    """RED (red-gate ruling R15, zero-margin = eligibility BEFORE the pick) --
    hand-built sweep: the loser's top-scoring dim a leads by only 0.5 (80.0 vs
    79.5) while b leads by 3.0 (60.0 vs 57.0). Flags OFF: today's fallback names
    a at margin 0.5. Guard ON (V or T): a is ineligible, the pick is the
    strongest ELIGIBLE dim, b at margin 3.0, and the pair names it. Reading (a)
    (pick a, then drop the < 1.0 pair) returns no pair -> red."""
    winner = {"a_score": 79.5, "b_score": 57.0, "c_score": 90.0}
    loser = {"a_score": 80.0, "b_score": 60.0, "c_score": 70.0}
    dw = {"c_score": {"winner": "Winner W", "margin": 20.0}}
    svc = _svc()
    assert svc._loser_strongest_dim(_hand_scores(winner, loser), 0, "Loser L") == {
        "dimension": "a_score", "product": "Loser L", "margin": 0.5}
    _state(monkeypatch, state)
    got = svc._loser_strongest_dim(_hand_scores(winner, loser), 0, "Loser L")
    assert got == {"dimension": "b_score", "product": "Loser L", "margin": 3.0}, got
    pairs = svc.compute_tradeoff_pairs(dw, ["Winner W", "Loser L"], 0, scores=_hand_scores(winner, loser))
    assert [p["loser_wins"] for p in pairs] == [got], pairs


def test_guard_margin_boundary_is_one_point(monkeypatch):
    """KILL (ruling R21 on R15's boundary, adversary r0 A2: `< 1.0` -> `<= 1.0`)
    -- the eligibility rule compares the loser's lead ROUNDED to 1 decimal (the
    breakdown's own precision) with `< 1.0`: a lead of exactly 1.0 stays ELIGIBLE
    and the next representable lead below it, 0.9, does not. Under V and under T:
    (a) the only loser lead is 81.0 vs 80.0 => named at margin 1.0 and the pair
    ships; (b) the only loser lead is 80.9 vs 80.0 => None, no pair; (c) the
    loser's top dim leads by 0.9 and another by exactly 1.0 => the 1.0 dim is the
    pick. Flags OFF the 0.9 dim is today's fallback. RED at the red tree ((b)
    names the 0.9 dim); `<= 1.0` drops the 1.0 leads and reddens (a) and (c);
    `< 1.1` drops them too. The rule is ROUNDED (ruling R23, correcting R21's
    premise): `round(lead, 1) < 1.0` is ineligible, so a raw lead of 0.999
    rounds to 1.0 and IS eligible (margin 1.0), and the first ineligible
    1-decimal lead is 0.9; the round itself is pinned by
    test_guard_rounds_the_lead_before_comparing."""
    dw = {"c_score": {"winner": "Winner W", "margin": 20.0}}
    names = ["Winner W", "Loser L"]
    one = ({"a_score": 80.0, "c_score": 90.0}, {"a_score": 81.0, "c_score": 70.0})
    under = ({"a_score": 80.0, "c_score": 90.0}, {"a_score": 80.9, "c_score": 70.0})
    pick = ({"a_score": 80.0, "b_score": 60.0, "c_score": 90.0}, {"a_score": 80.9, "b_score": 61.0, "c_score": 70.0})
    svc = _svc()
    assert svc._loser_strongest_dim(_hand_scores(*under), 0, "Loser L") == {
        "dimension": "a_score", "product": "Loser L", "margin": 0.9}
    for state in ("V", "T"):
        _state(monkeypatch, state)
        got = svc._loser_strongest_dim(_hand_scores(*one), 0, "Loser L")
        assert got == {"dimension": "a_score", "product": "Loser L", "margin": 1.0}, (state, got)
        pairs = svc.compute_tradeoff_pairs(dw, names, 0, scores=_hand_scores(*one))
        assert [p["loser_wins"] for p in pairs] == [got], (state, pairs)
        assert svc._loser_strongest_dim(_hand_scores(*under), 0, "Loser L") is None, state
        assert svc.compute_tradeoff_pairs(dw, names, 0, scores=_hand_scores(*under)) == [], state
        got = svc._loser_strongest_dim(_hand_scores(*pick), 0, "Loser L")
        assert got == {"dimension": "b_score", "product": "Loser L", "margin": 1.0}, (state, got)


def test_guard_rounds_the_lead_before_comparing(monkeypatch):
    """KILL (ruling R23, adversary r1 B1: the guard compares the raw
    `val - winner` instead of `round(val - winner, 1)`) -- breakdowns carry 1
    decimal, and some genuine 1.0 leads between 1-decimal values fall just under
    1.0 in float arithmetic (measured: 64.1 - 63.1 = 0.9999999999999929,
    4.1 - 3.1 = 0.9999999999999996; 4.3 - 3.3 is exactly 1.0). The guard rounds
    the lead to 1 decimal first, so each of those is ELIGIBLE at margin 1.0 under
    V and under T, and so is a raw 0.999 lead (80.999 vs 80.0, rounds to 1.0 --
    the rounded rule R23 states). RED at the red tree (no guard: the loser's
    highest dim c is named at margin 0); dropping the round makes every case
    ineligible (None, no pair) and reddens it."""
    dw = {"c_score": {"winner": "Winner W", "margin": 20.0}}
    names = ["Winner W", "Loser L"]
    svc = _svc()
    for loser_val, winner_val in ((64.1, 63.1), (4.1, 3.1), (80.999, 80.0)):
        assert loser_val - winner_val < 1.0 and round(loser_val - winner_val, 1) == 1.0
        scores = _hand_scores({"a_score": winner_val, "c_score": 90.0}, {"a_score": loser_val, "c_score": 70.0})
        for state in ("V", "T"):
            _state(monkeypatch, state)
            got = svc._loser_strongest_dim(scores, 0, "Loser L")
            assert got == {"dimension": "a_score", "product": "Loser L", "margin": 1.0}, (
                state, loser_val, winner_val, got)
            pairs = svc.compute_tradeoff_pairs(dw, names, 0, scores=scores)
            assert [p["loser_wins"] for p in pairs] == [got], (state, loser_val, winner_val, pairs)


# The two TestTradeoffPairs sweep fixtures of tests/test_scoring_service.py
# (F4.2 flag-OFF pins; they carry the R16 delenv of both W4-6a names).
_SWEEP_WINNERS_A = {d: {"winner": "Product A", "margin": m} for d, m in (
    ("performance_score", 15.0), ("value_score", 12.0), ("build_quality_score", 10.0),
    ("feature_score", 8.0), ("ecosystem_score", 7.0), ("futureproof_score", 6.0))}
_SWEEP_SCORES_A = {
    "product_0": {"breakdown": {"performance_score": 90, "value_score": 85, "build_quality_score": 88,
                                "feature_score": 80, "ecosystem_score": 75, "futureproof_score": 70}},
    "product_1": {"breakdown": {"performance_score": 55, "value_score": 62, "build_quality_score": 50,
                                "feature_score": 48, "ecosystem_score": 45, "futureproof_score": 40}},
}
_SWEEP_WINNERS_B = {d: dict(v, winner="Product B") for d, v in _SWEEP_WINNERS_A.items()}
_SWEEP_SCORES_B = {
    "product_0": {"breakdown": {"performance_score": 50, "value_score": 48, "build_quality_score": 66,
                                "feature_score": 45, "ecosystem_score": 40, "futureproof_score": 38}},
    "product_1": {"breakdown": {"performance_score": 90, "value_score": 85, "build_quality_score": 80,
                                "feature_score": 78, "ecosystem_score": 75, "futureproof_score": 70}},
}


@pytest.mark.parametrize("state", ["V", "T", "VT"])
def test_sweep_pair_ships_no_runner_up_caption_under_guard(monkeypatch, state):
    """RED (red-gate ruling R16, the flag-ON twins of the F4.2 / W4-10 sweep pins)
    -- a sweep pair (the winner leads every eligible dim) under the guard ships
    `tradeoffs == []` and `key_tradeoff == ""`: the fabricated runner-up strength
    is gone. Twins of tests/test_scoring_service.py::TestTradeoffPairs::
    test_sweep_with_scores_falls_back_to_loser_strongest / test_sweep_fallback_winner_idx_1
    (flags OFF: value_score / build_quality_score named at margin 0) and of the
    W4-10 brand-repeating REPEAT pair of tests/test_tradeoffs_dedup_parity.py
    (flags OFF: "Xerjoff Erba Pura stays competitive on longevity." at margin 0).
    RED at HEAD: the margin-0 fallback is named. Product note (R16): the phone's
    RunnerUpWinsCard must render its empty state for `tradeoffs: []`."""
    from app.services.response_builder import deterministic_verdict_fields
    from tests import test_tradeoffs_dedup_parity as tdp
    svc = _svc()
    names = ["Product A", "Product B"]
    off_a = svc.compute_tradeoff_pairs(_SWEEP_WINNERS_A, names, 0, scores=copy.deepcopy(_SWEEP_SCORES_A))
    off_b = svc.compute_tradeoff_pairs(_SWEEP_WINNERS_B, names, 1, scores=copy.deepcopy(_SWEEP_SCORES_B))
    assert [p["loser_wins"] for p in off_a][:1] == [
        {"dimension": "value_score", "product": "Product B", "margin": 0}]
    assert [p["loser_wins"] for p in off_b][:1] == [
        {"dimension": "build_quality_score", "product": "Product A", "margin": 0}]
    assert _run(svc, tdp.REPEAT())["key_tradeoff"] == "Xerjoff Erba Pura stays competitive on longevity."
    _state(monkeypatch, state)
    for winners, scores, wi in ((_SWEEP_WINNERS_A, _SWEEP_SCORES_A, 0), (_SWEEP_WINNERS_B, _SWEEP_SCORES_B, 1)):
        pairs = svc.compute_tradeoff_pairs(winners, names, wi, scores=copy.deepcopy(scores))
        assert pairs == [], (state, wi, pairs)
        result = {"scores": copy.deepcopy(scores), "winner_index": wi}
        assert deterministic_verdict_fields(result, names, pairs)["key_tradeoff"] == ""
    rep = _run(svc, tdp.REPEAT())
    assert rep["tradeoffs"] == [] and rep["key_tradeoff"] == "", (rep["tradeoffs"], rep["key_tradeoff"])


@pytest.mark.parametrize("scenario", sorted(_R08_OFF), ids=["R08d", "R08e"])
def test_value_flag_guard_is_active_under_renorm(monkeypatch, scenario):
    """RED (red-gate ruling R17, the renorm + V twin of test 15) -- under
    ENABLE_MISSING_DIM_RENORM the coupled T reader is False, so the guard is on
    iff V is: renorm alone (and renorm + T, test 15) keeps today's void-named
    fallback ("stays competitive on build quality." at margin 50 / 40.0), while
    renorm + V names no void and ships no margin < 1.0 pair (`[]`, "").
    RED at HEAD: V is inert, the void is named under RV too."""
    svc = _svc()
    _state(monkeypatch, "R")
    r = _run(svc, _scenario(scenario))
    assert r["tradeoffs"][0]["loser_wins"] == {
        "dimension": "build_quality_score", "product": "Brand B Phone Y", "margin": _R08_OFF[scenario]}
    _state(monkeypatch, "RV")
    r = _run(svc, _scenario(scenario))
    assert r["tradeoffs"] == [] and r["key_tradeoff"] == "", (r["tradeoffs"], r["key_tradeoff"])


# ===========================================================================
# R11 consumers: trust_validation_service.validate_verdict
# ===========================================================================
_VV = {
    # scenario: (OFF same, OFF other, T same, T other) -- (validated, softened, flagged, adjustment)
    "R01_identical_spec_50v52": ((1, 2, 0, None), (0, 2, 1, "low"), (1, 5, 0, None), (0, 5, 1, "low")),
    "R02_identical_verified_50v50": ((0, 3, 0, None), (0, 3, 0, "low"), (0, 6, 0, None), (0, 6, 0, "low")),
    "R08c_loser_has_real_strength": ((5, 0, 0, None), (1, 0, 4, "low"), (5, 1, 0, None), (1, 1, 4, "low")),
}


@pytest.mark.parametrize("scenario", sorted(_VV))
def test_verdict_validation_counts_under_tie_flag(monkeypatch, scenario):
    """RED (ruling R11a, the consumer the spec missed) -- `validate_verdict` reads the
    breakdown with `== MISSING_SCORE`, so the un-collapsed T values start counting
    as claims. Driven with a stubbed GPT verdict (`{"winner_index": ...}` = the
    scoring winner and the other product) in both states: the OFF shape is pinned
    (green at HEAD) and the T-ON shape is the measured one (claims_softened rises:
    R01 2 -> 5, R02 3 -> 6, R08c 0 -> 1; confidence_adjustment unchanged on all 169
    probe records). RED at HEAD: T inert, softened stays at the OFF count."""
    from app.services.trust_validation_service import validate_verdict
    svc = _svc()

    def shape(state):
        _state(monkeypatch, state)
        res = svc.compute_scores(copy.deepcopy(_scenario(scenario)))
        wi = res["winner_index"]
        out = []
        for verdict_wi in (wi, 1 - wi):
            v = validate_verdict({"winner_index": verdict_wi}, res, res["category"])
            out.append((v["claims_validated"], v["claims_softened"], v["claims_flagged"],
                        v["confidence_adjustment"]))
        return tuple(out)

    off_same, off_other, t_same, t_other = _VV[scenario]
    assert shape("OFF") == (off_same, off_other)
    assert shape("T") == (t_same, t_other), "T ON: validate_verdict shape %r, want %r" % (
        shape("T"), (t_same, t_other))


# ===========================================================================
# Logs (spec 3.4; C6 M17)
# ===========================================================================
def _w46a_records(caplog):
    return [r for r in caplog.records if "W4-6a" in r.getMessage()]


@pytest.mark.parametrize("state", ["OFF", "R", "S", "RT"])
def test_flags_off_emit_no_w4_6a_log_line(monkeypatch, caplog, state):
    """KILL (C6 M17 caplog PIN) -- with both W4-6a flags unset (and with T set
    under renorm, where it is inert) the full scoring + tradeoff path over the
    scenarios and the grid emits NO log line containing "W4-6a" at any level.
    Green at HEAD."""
    _state(monkeypatch, state)
    svc = _svc()
    with caplog.at_level(logging.DEBUG):
        for v in _records("S", "G").values():
            _run(svc, v)
    assert not _w46a_records(caplog), [r.getMessage() for r in _w46a_records(caplog)][:3]


def test_flag_on_log_lines(monkeypatch, caplog):
    """RED (spec 3.4 canary lines) -- at most one INFO per call: T ON R02 =>
    "W4-6a tie kept" naming reliability, popularity and spec; T ON R02c => "W4-6a
    tie collapsed (sparse)" naming the same three; V ON R01 => "W4-6a value dim
    partial" naming value_score. RED at HEAD: no such line."""
    svc = _svc()

    def lines(state, scenario):
        _state(monkeypatch, state)
        caplog.clear()
        with caplog.at_level(logging.DEBUG, logger=_SCORING_LOGGER):
            svc.compute_scores(copy.deepcopy(_scenario(scenario)))
        return [(r.levelno, r.getMessage()) for r in _w46a_records(caplog)]

    kept = lines("T", "R02_identical_verified_50v50")
    assert len(kept) == 1 and kept[0][0] == logging.INFO and "tie kept" in kept[0][1], kept
    for sig in ("reliability", "popularity", "spec"):
        assert sig in kept[0][1], kept
    sparse = lines("T", "R02c_sparse_identical")
    assert len(sparse) == 1 and "tie collapsed (sparse)" in sparse[0][1], sparse
    for sig in ("reliability", "popularity", "spec"):
        assert sig in sparse[0][1], sparse
    partial = lines("V", "R01_identical_spec_50v52")
    assert len(partial) == 1 and "value dim partial" in partial[0][1] and "value_score" in partial[0][1], partial


def test_value_partial_log_only_when_a_dim_was_unstamped(monkeypatch, caplog):
    """KILL (ruling R21 / spec 3.4, adversary r0 A11: the V line emitted whenever
    the like-for-like condition holds) -- V ON, a both-priced pair with specs on
    both sides (ELEC_SPECS 50.0 vs BETTER_ELEC_SPECS 52.0): V's condition holds
    (every product priced, `_spec_missing` equal) but no value dim was stamped, so
    nothing is un-stamped and NO "W4-6a value dim partial" line is emitted (the
    section-9 activation canary counts these lines). The contrast row, R01 under
    V, un-stamps value_score and emits exactly one. RED at the red tree (R01
    emits none); gating the line on the condition alone reddens the first row."""
    g = _gen()
    pair = [g.prod("Brand A", "Phone X", "electronics", g.ELEC_SPECS, 4.5, 900, g.FULL_FC, 50.0),
            g.prod("Brand B", "Phone Y", "electronics", g.BETTER_ELEC_SPECS, 4.5, 900, g.FULL_FC, 52.0)]
    svc = _svc()
    _state(monkeypatch, "V")
    caplog.clear()
    with caplog.at_level(logging.DEBUG, logger=_SCORING_LOGGER):
        r = _run(svc, pair)
    assert "value_score" not in r["md0"] and "value_score" not in r["md1"], r["md_raw"]
    assert not _w46a_records(caplog), [x.getMessage() for x in _w46a_records(caplog)]
    caplog.clear()
    with caplog.at_level(logging.DEBUG, logger=_SCORING_LOGGER):
        svc.compute_scores(copy.deepcopy(_scenario("R01_identical_spec_50v52")))
    got = [x.getMessage() for x in _w46a_records(caplog)]
    assert len(got) == 1 and "value dim partial" in got[0], got


# ===========================================================================
# Identity + KPI (gates E2 / E3)
# ===========================================================================
def test_flags_off_record_digests():
    """KILL (test 25, gate E2; M9) -- the 164 records x 3 states (all unset;
    renorm ON; spec-field-norm ON), W4-6a flags unset, reproduce the digests
    captured at BASE 61585c58 in tests/fixtures/rubric_truth_flag_off_digests.json
    key by key (tradeoffs excluded). Green at HEAD; T-always-on reddens it."""
    with open(os.path.join(_FIXTURES_DIR, "rubric_truth_flag_off_digests.json"), encoding="utf-8") as fh:
        expected = json.load(fh)["digests"]
    got = _gen().build_digests()
    assert len(expected) == 492 and sorted(got) == sorted(expected)
    diff = [k for k in sorted(expected) if got[k] != expected[k]]
    assert not diff, "flag-OFF record digests moved on %d keys, first %r" % (len(diff), diff[:1])


def test_flag_on_golden():
    """RED (test 26, gate E3) -- (a) the generator's OFF regeneration equals the two
    existing flag-OFF goldens for the sensitive builders (proves its shape; green
    at HEAD); (b) each of V, T, VT moves at least one golden-builder result (the
    flags are live); (c) V, T, VT equal tests/fixtures/rubric_truth_flag_on_golden.json
    (generated from the GREEN head); (d) the value-badge and behavioral goldens
    stay green with V, T and VT set. RED at HEAD at (b): the flags are inert."""
    gen_on = _gen_on()
    off = gen_on.build_golden(("OFF",))["OFF"]
    for bname, fname in (("renorm", "missing_dim_renorm_flag_off_golden.json"),
                         ("specnorm", "spec_field_norm_flag_off_golden.json")):
        with open(os.path.join(_FIXTURES_DIR, fname), encoding="utf-8") as fh:
            assert off[bname] == json.load(fh), "generator OFF shape != %s" % fname
    on = gen_on.build_golden(gen_on.ON_STATES)
    for state in gen_on.ON_STATES:
        assert on[state] != off, "W4-6a flag state %s is inert on the golden builders" % state
    path = os.path.join(_FIXTURES_DIR, "rubric_truth_flag_on_golden.json")
    assert os.path.exists(path), "the flag-ON golden has not been generated from the green head"
    with open(path, encoding="utf-8") as fh:
        golden = json.load(fh)
    for state in gen_on.ON_STATES:
        for bname in ("renorm", "specnorm"):
            for cat, expected in golden[state][bname].items():
                assert on[state][bname][cat] == expected, "%s/%s/%s deviates from the flag-ON golden" % (
                    state, bname, cat)
    from tests import test_behavior_dimension_translation as bd
    from tests import test_value_badge_category_dims as vb
    saved = {k: os.environ.get(k) for k in (V_FLAG, T_FLAG)}
    try:
        for state in gen_on.ON_STATES:
            for k in (V_FLAG, T_FLAG):
                os.environ.pop(k, None)
            os.environ.update(_STATE_ENV[state])
            vb.test_flag_off_badges_match_golden()
            bd.test_flag_off_weights_and_label_match_golden(_svc(), None)
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def test_missing_cell_kpi_counts_only_true_gaps(monkeypatch):
    """RED (test 27) -- VT ON, `count_missing_dim_cells`: R02 0/12, R02c 6/12,
    R01b 2/12 (HEAD 8/12 on all three: the eval KPI counted erased ties and the
    priced value leg as gaps)."""
    _state(monkeypatch, "VT")
    svc = _svc()
    got = {s: _run(svc, _scenario(s))["cells"]["count"] for s in
           ("R02_identical_verified_50v50", "R02c_sparse_identical", "R01b_nospec_50v52")}
    assert got == {"R02_identical_verified_50v50": 0, "R02c_sparse_identical": 6, "R01b_nospec_50v52": 2}, got
