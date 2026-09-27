"""W4-7 Part A -- the reliability dimension stops scoring what nobody checked.

Finding PO-FACTCHECK-CONFIDENCE-01 (P1). Spec `.qa-s68/specs/W4_7_UNIT_SPEC.md`
as corrected by its ADVERSARIAL SPEC REVIEW and bound by the FABLE RULINGS
(R1, R2, R7; 2026-09-26, session 68).

Flag ENABLE_RELIABILITY_UNCHECKED_ABSENCE (default OFF, read PER CALL, the
`confidence_factcheck_wiring_enabled` idiom). Reader
`scoring_service.reliability_unchecked_absence_enabled()`.

Ruled shape (R2): ONE-SIDED None -- an all-unverified fact-check
(verified + likely + flagged == 0, at least one bucket populated) has NO
reliability score, exactly like the empty case -- AND the reader returns False
unless ENABLE_MISSING_DIM_RENORM is ON (coupled, pinned both ways): under the
legacy MISSING_SCORE = 50 path a one-sided None would let unchecked beat
measured-bad (#101), under renorm the missing dimension is excluded for the pair
and never scores. There is NO pair-symmetric collapse (the spec body's
`_normalize_scores` change is overruled). Consequence pinned by A6: zero-bucket
vs 8/0/0 -> reliability excluded, the crown falls to the other dimensions.

Test kinds (each docstring names its kind and reason):
  RED  -- fails at HEAD 15e1fb89 on an assertion naming the absent behaviour.
  PIN  -- green at HEAD and must stay green.
  KILL -- a PIN that is also the named killer of a mutation (row in docstring).

Every number below was measured at HEAD 15e1fb89 (red phase, session 68) through
the real ScoringService. Always a FRESH ScoringService(); the new reader is
resolved INSIDE test bodies, never at import.
"""
from __future__ import annotations

import copy
import ipaddress
import socket

import pytest

FLAG = "ENABLE_RELIABILITY_UNCHECKED_ABSENCE"
RENORM = "ENABLE_MISSING_DIM_RENORM"
BUNDLE_C = "ENABLE_BUNDLE_C_SCORING"

_CLEARED_ENV = (
    "ENABLE_RELIABILITY_UNCHECKED_ABSENCE", "ENABLE_CONFIDENCE_SINGLE_COMPUTATION",
    "ENABLE_FACTCHECK_SHOPPING_KEY", "ENABLE_CONFIDENCE_FACTCHECK_WIRING",
    "ENABLE_FACTCHECK_CURRENCY_NORMALIZATION", "ENABLE_FACTCHECK_HONEST_ABSENCE",
    "ENABLE_SPEC_CONFIDENCE_CACHE", "ENABLE_CITATION_RUBRIC_V2", "ENABLE_BUNDLE_C_SCORING",
    "ENABLE_MISSING_DIM_RENORM", "ENABLE_SPEC_FIELD_NORM", "ENABLE_PRESCORING_SHOWABLE_GUARD",
    "ENABLE_REGION_CURRENCY_GUARD", "ENABLE_HONEST_PARTIAL_SCORING",
    "ENABLE_VALUE_DIM_PARTIAL_SIGNAL", "ENABLE_TIE_IS_NOT_MISSING",
    "ENABLE_CATEGORY_VALUE_BADGE", "ENABLE_BEHAVIORAL_DIM_TRANSLATION",
    "DISABLE_DIM_NORM_DAMPENING", "WINNER_DIM_GAP_TOLERANCE",
    "WINNER_PRICE_AUTHORITY_POINTS", "WINNER_VALUE_WEIGHT_SCALE",
    "ENABLE_WINNER_PROSE_RECONCILE",
)

CATEGORIES = ("electronics", "other", "supplements", "fragrances", "fashion",
              "grocery", "makeup", "skincare", "haircare")


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
    """Every flag the scoring / confidence / fact-check surface reads is unset and
    the process-cached bundle-C flag is reset, so the cleared env is what runs."""
    for name in _CLEARED_ENV:
        monkeypatch.delenv(name, raising=False)
    from app.services import scoring_service
    monkeypatch.setattr(scoring_service, "_BUNDLE_C_SCORING_FLAG", None, raising=False)
    yield


# ---------------------------------------------------------------------------
# helpers / fixtures (stated in full so every number reproduces)
# ---------------------------------------------------------------------------
PDP0 = "https://bolo.bh/products/sony-wh-1000xm5"
PDP1 = "https://bolo.bh/products/bose-qc-ultra"
E0 = {"battery_life": "30 hours", "ram": "8 GB", "storage": "256 GB",
      "screen_size": "6.1 inch", "weight": "250 g"}
PHONE_SPECS = {"display": "6.1 inch", "battery": "4000 mAh", "storage": "128 GB",
               "ram": "8 GB", "weight": "180 g", "camera": "48 MP",
               "processor": "A-chip", "os": "OS 17"}


def _svc():
    from app.services.scoring_service import ScoringService
    return ScoringService()


def _fc(v=0, l=0, u=0, f=0, pv=False, rs=None):  # noqa: E741
    return {"specs_verified": v, "specs_likely": l, "specs_unverified": u,
            "specs_flagged": f, "price_verified": pv, "price_deviation_pct": None,
            "review_sentiment_consistent": rs, "review_rating_deviation": None}


def _ident(name, brand, url, fc, cat="electronics"):
    """The identical-pair product: 150 BHD local_bhd, bolo.bh PDP, 4.5 / 1000, E0."""
    p = {"name": name, "full_name": name, "brand": brand, "category": cat,
         "price": {"amount": 150.0, "currency": "BHD", "source_method": "local_bhd",
                   "url": url, "title": name, "in_stock": True, "retailer": "Best Buy"},
         "best_price": 150.0, "retailer": "Best Buy", "specs": dict(E0),
         "rating": 4.5, "review_count": 1000}
    if fc is not None:
        p["fact_check"] = fc
    return p


def _p1pair(fa, fb, cat="electronics"):
    """The spec's probe-1 pair: Alpha Phone One 300 BHD 4.4/900 vs Beta Phone Two
    280 BHD 4.4/950, 8 phone specs, local_bhd."""
    a = {"brand": "Alpha", "name": "Phone One", "category": cat,
         "price": {"amount": 300.0, "currency": "BHD", "source_method": "local_bhd",
                   "estimated": False},
         "rating": 4.4, "review_count": 900, "specs": dict(PHONE_SPECS), "fact_check": fa}
    b = copy.deepcopy(a)
    b.update({"brand": "Beta", "name": "Phone Two",
              "price": {"amount": 280.0, "currency": "BHD", "source_method": "local_bhd",
                        "estimated": False},
              "rating": 4.4, "review_count": 950, "fact_check": fb})
    return [a, b]


def _dim(cat):
    from app.services.scoring_service import ScoringService
    return [d for d, s in ScoringService._DIMENSION_SIGNAL_MAP[cat].items()
            if s == "reliability"][0]


def _summ(res, cat):
    d = _dim(cat)
    s = res["scores"]
    return {
        "vals": [s["product_0"]["breakdown"].get(d), s["product_1"]["breakdown"].get(d)],
        "md": [d in (s["product_0"].get("missing_data") or []),
               d in (s["product_1"].get("missing_data") or [])],
        "overall": [s["product_0"]["overall"], s["product_1"]["overall"]],
        "winner_index": res.get("winner_index"),
        "win_margin": res.get("win_margin"),
        "dim_winner": (res.get("dimension_winners") or {}).get(d),
    }


def _score(pd, cat):
    return _summ(_svc().compute_scores(copy.deepcopy(pd)), cat)


def _on(monkeypatch):
    """The ruled ON state: the Part A flag AND its coupled precondition."""
    monkeypatch.setenv(FLAG, "true")
    monkeypatch.setenv(RENORM, "true")


UNCHECKED = [
    ("unv1", _fc(u=1), 0.3), ("unv3", _fc(u=3), 0.3), ("unv8", _fc(u=8), 0.3),
    ("unv11", _fc(u=11), 0.3), ("unv50", _fc(u=50), 0.3),
    ("unv8_pvT", _fc(u=8, pv=True), 0.4),
    ("unv8_rsT", _fc(u=8, rs=True), 0.35),
    ("unv8_rsF", _fc(u=8, rs=False), 0.19999999999999998),
    ("unv8_pvT_rsT", _fc(u=8, pv=True, rs=True), 0.45),
]
CHECKED = [
    ("v1u7", _fc(v=1, u=7), 0.3875), ("l1u7", _fc(l=1, u=7), 0.35),
    ("f1u7", _fc(f=1, u=7), 0.2625), ("f1", _fc(f=1), 0.0), ("v2u6", _fc(v=2, u=6), 0.475),
    ("empty", {}, None), ("zeros", _fc(), None),
]


# ---------------------------------------------------------------------------
# A1 / A2 / A3 -- _score_reliability
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("label,fc,head", UNCHECKED, ids=[c[0] for c in UNCHECKED])
def test_a1_unchecked_fact_check_is_absent_flag_on(monkeypatch, label, fc, head):
    """RED -- flag ON (+ its coupled ENABLE_MISSING_DIM_RENORM): an all-unverified
    fact-check is ABSENCE -> None. HEAD returns the constant 0.3 (+0.1 pv, +0.05 /
    -0.1 sentiment) regardless of how many fields were 'checked'.
    Kills M-A1 (drop the unchecked return None)."""
    _on(monkeypatch)
    got = _svc()._score_reliability(dict(fc))
    assert got is None, (
        "ABSENT BEHAVIOUR: all-unverified fact_check %s still scores %r under %s=true "
        "+ %s=true (expected None = no reliability score)" % (label, got, FLAG, RENORM))


@pytest.mark.parametrize("state", [None, "false"])
@pytest.mark.parametrize("label,fc,head", UNCHECKED, ids=[c[0] for c in UNCHECKED])
def test_a2_flag_off_values_unchanged(monkeypatch, label, fc, head, state):
    """PIN / KILL -- flag unset AND "false" (renorm ON too, so only the flag
    decides): HEAD values 0.3 x5, 0.4, 0.35, 0.2, 0.45. Kills M-A4 (reader
    forced True)."""
    monkeypatch.setenv(RENORM, "true")
    if state is not None:
        monkeypatch.setenv(FLAG, state)
    assert _svc()._score_reliability(dict(fc)) == pytest.approx(head)


@pytest.mark.parametrize("state", ["unset", "on"])
@pytest.mark.parametrize("label,fc,val", CHECKED, ids=[c[0] for c in CHECKED])
def test_a3_checked_shapes_identical_both_states(monkeypatch, label, fc, val, state):
    """PIN / KILL -- a fact-check with any verified / likely / flagged field is
    untouched by the flag: 0.3875 / 0.35 / 0.2625 / 0.0 / 0.475; {} and zeros ->
    None. Kills M-A3 (absence on every populated fact_check)."""
    if state == "on":
        _on(monkeypatch)
    got = _svc()._score_reliability(dict(fc))
    if val is None:
        assert got is None
    else:
        assert got == pytest.approx(val)


def test_a1b_flag_on_without_renorm_is_inert(monkeypatch):
    """PIN / KILL -- coupling (R2): flag ON with ENABLE_MISSING_DIM_RENORM unset
    keeps HEAD values (a one-sided None on the legacy MISSING_SCORE=50 path is the
    #101 inversion). Kills M-A6 (reader ignores renorm)."""
    monkeypatch.setenv(FLAG, "true")
    for label, fc, head in UNCHECKED:
        assert _svc()._score_reliability(dict(fc)) == pytest.approx(head), label


# ---------------------------------------------------------------------------
# A4 -- price_verified alone cannot move the winner (9 categories, both orders)
# ---------------------------------------------------------------------------
_A4_HEAD_MARGIN = {"electronics": 1.5, "other": 1.4, "supplements": 2.5, "fragrances": 1.5,
                   "fashion": 1.5, "grocery": 2.0, "makeup": 2.0, "skincare": 2.0,
                   "haircare": 1.5}


@pytest.mark.parametrize("cat", CATEGORIES)
def test_a4_price_verified_alone_cannot_move_the_winner(monkeypatch, cat):
    """RED -- identical pair (only price_verified differs, both 0/0/8), flag ON:
    the reliability dim is 50 on both products, in BOTH missing_data, and
    win_margin == 0.0 in both orders. HEAD (renorm ON too): 40.0 / 30.0, the
    pv-True product wins both orders by the category margin (1.5/1.4/2.5/1.5/1.5/
    2.0/2.0/2.0/1.5). The crown at 0.0 is NOT asserted (W4-6b's tie-break)."""
    _on(monkeypatch)
    a = _ident("Alpha One", "Alpha", PDP0, _fc(u=8, pv=True), cat)
    b = _ident("Beta Two", "Beta", PDP1, _fc(u=8, pv=False), cat)
    for order in ([a, b], [b, a]):
        s = _score(order, cat)
        assert s["vals"] == [50, 50] and s["md"] == [True, True] and s["win_margin"] == 0.0, (
            "ABSENT BEHAVIOUR: price_verified alone still moves the %s reliability dim: %r "
            "(HEAD margin %s)" % (cat, s, _A4_HEAD_MARGIN[cat]))


@pytest.mark.parametrize("cat", CATEGORIES)
def test_a4b_flag_off_identical_pair_head_numbers(cat):
    """PIN / KILL -- flag unset: the identical pair reads 40.0 / 30.0, the pv-True
    product wins both orders by the measured margin; the dim is in neither
    missing_data. Kills M-A4."""
    a = _ident("Alpha One", "Alpha", PDP0, _fc(u=8, pv=True), cat)
    b = _ident("Beta Two", "Beta", PDP1, _fc(u=8, pv=False), cat)
    ab = _score([a, b], cat)
    ba = _score([b, a], cat)
    assert ab["vals"] == [40.0, 30.0] and ab["md"] == [False, False]
    assert ab["winner_index"] == 0 and ba["winner_index"] == 1
    assert ab["win_margin"] == _A4_HEAD_MARGIN[cat] == ba["win_margin"]


# ---------------------------------------------------------------------------
# A5 -- one-sided unchecked: under renorm the dim is excluded for the pair
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("cat", ["electronics", "other", "supplements", "fragrances"])
@pytest.mark.parametrize("checked_label,checked", [("v2u6", _fc(v=2, u=6)), ("f1u7", _fc(f=1, u=7))])
def test_a5_one_sided_unchecked_scores_as_absent(monkeypatch, cat, checked_label, checked):
    """RED -- probe-1 pair, one side checked (2/0/6 or flagged 1 + 7), the other
    0/0/8. Flag ON: the unchecked side has NO reliability score, so the pair
    scores EXACTLY like the same pair with that side's fact_check empty (today's
    zero-bucket None) -- overall, winner_index, win_margin and the dim flags equal,
    the unchecked side carries the dim in missing_data. HEAD (renorm ON): the
    unchecked 0.3 scores (30.0) and the flagged side's 26.2 loses the dim by 3.8.
    Kills M-A1. (Spec body's 'flagged product never the dim winner' is NOT asserted:
    under R2's one-sided design dimension_winners names the only side with data,
    margin None -- today's behaviour for every one-sided missing dim.)"""
    _on(monkeypatch)
    got = _score(_p1pair(checked, _fc(u=8), cat), cat)
    ref = _score(_p1pair(checked, {}, cat), cat)
    assert got["md"] == [False, True] and got == ref, (
        "ABSENT BEHAVIOUR: the unchecked 0/0/8 side still scores under the flag: %r "
        "(the absent-side equivalent is %r)" % (got, ref))


# ---------------------------------------------------------------------------
# A6 -- zero-bucket rows (R2 consequence) + A6b flag-OFF HEAD numbers
# ---------------------------------------------------------------------------
def test_a6_zero_bucket_vs_unchecked_both_absent(monkeypatch):
    """RED -- zero buckets (and no fact_check key) vs 0/0/8, flag ON: BOTH sides are
    absent -> build_quality_score in BOTH missing_data, 50 / 50, win_margin 0.0,
    overall 67.0 / 67.0. HEAD (renorm ON): the 0/0/8 side is present (30.0), only
    product 0 is missing, overall 70.0 / 70.0, winner 1."""
    _on(monkeypatch)
    for fa in (_fc(), None):
        s = _score([_ident("Alpha One", "Alpha", PDP0, fa), _ident("Beta Two", "Beta", PDP1, _fc(u=8))],
                   "electronics")
        assert s["md"] == [True, True] and s["vals"] == [50, 50] and s["win_margin"] == 0.0 \
            and s["overall"] == [67.0, 67.0], (
                "ABSENT BEHAVIOUR: the unchecked side still carries a reliability score: %r" % (s,))


@pytest.mark.parametrize("state", ["renorm_only", "on"])
def test_a6_fully_verified_row_excluded_under_renorm(monkeypatch, state):
    """PIN / KILL -- R2's stated cost: zero buckets vs 8/0/0 (fully verified) and vs
    2/0/6. Under renorm the one-sided missing dim is EXCLUDED; the crown falls to
    the other (identical) dimensions: overall 70.0 / 70.0, winner 1, margin 0.0,
    displayed 50 / 100 (50 / 47.5), only product 0 missing. The flag changes
    nothing here (zero buckets are None already). Kills M-A2 (a pair-symmetric
    collapse re-added: 67.0 / 67.0 winner 0)."""
    monkeypatch.setenv(RENORM, "true")
    if state == "on":
        monkeypatch.setenv(FLAG, "true")
    for fb, shown in ((_fc(v=8), 100), (_fc(v=2, u=6), 47.5)):
        s = _score([_ident("Alpha One", "Alpha", PDP0, _fc()), _ident("Beta Two", "Beta", PDP1, fb)],
                   "electronics")
        assert s["vals"] == [50, shown] and s["md"] == [True, False]
        assert s["overall"] == [70.0, 70.0] and s["winner_index"] == 1 and s["win_margin"] == 0.0


def test_a6b_flag_off_zero_bucket_head_numbers():
    """PIN / KILL -- flag unset (no renorm): the live one-sided inversion, HEAD
    numbers: zero buckets vs 0/0/8 -> 50 / 30.0, winner 0, margin 3.0, 67.0 / 64.0;
    vs 2/0/6 -> 50 / 47.5, winner 0, margin 0.4; vs 8/0/0 -> 50 / 100, winner 1,
    margin 7.5, 67.0 / 74.5; no fact_check key vs 0/0/8 = row 1. Kills M-A4."""
    rows = [(_fc(), _fc(u=8), [50, 30.0], 0, 3.0, [67.0, 64.0]),
            (_fc(), _fc(v=2, u=6), [50, 47.5], 0, 0.4, [67.0, 66.6]),
            (_fc(), _fc(v=8), [50, 100], 1, 7.5, [67.0, 74.5]),
            (None, _fc(u=8), [50, 30.0], 0, 3.0, [67.0, 64.0])]
    for fa, fb, vals, wi, wm, ov in rows:
        s = _score([_ident("Alpha One", "Alpha", PDP0, fa), _ident("Beta Two", "Beta", PDP1, fb)],
                   "electronics")
        assert (s["vals"], s["winner_index"], s["win_margin"], s["overall"]) == (vals, wi, wm, ov), s


# ---------------------------------------------------------------------------
# A7 / A8 / A13 -- unchanged shapes
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("state", ["unset", "on"])
def test_a7_equal_and_both_absent_unchanged(monkeypatch, state):
    """PIN -- 0/0/8 pv False on both (the v2.1 tie collapse) and {} on both:
    50 / 50, dim winner N/A, both missing; overall 62.2 / 76.3, winner 1, margin
    14.1; flag unset and ON."""
    if state == "on":
        _on(monkeypatch)
    for fa, fb in ((_fc(u=8), _fc(u=8)), ({}, {})):
        s = _score(_p1pair(fa, fb), "electronics")
        assert s["vals"] == [50, 50] and s["md"] == [True, True]
        assert s["dim_winner"] == {"winner": "N/A", "margin": None}
        assert (s["overall"], s["winner_index"], s["win_margin"]) == ([62.2, 76.3], 1, 14.1)


@pytest.mark.parametrize("state", [None, "false"])
def test_a8_flag_off_scores_exact(monkeypatch, state):
    """PIN / KILL -- probe-1 pair flag unset / "false" (renorm ON, so only the flag
    decides): pv T vs F -> 40.0 / 30.0, 60.8 / 73.3, winner 1, margin 12.5;
    sentiment T vs F -> 35.0 / 20.0, 60.0 / 71.8, margin 11.8. Kills M-A4."""
    monkeypatch.setenv(RENORM, "true")
    if state is not None:
        monkeypatch.setenv(FLAG, state)
    s = _score(_p1pair(_fc(u=8, pv=True), _fc(u=8)), "electronics")
    assert (s["vals"], s["overall"], s["winner_index"], s["win_margin"]) == (
        [40.0, 30.0], [60.8, 73.3], 1, 12.5)
    s = _score(_p1pair(_fc(u=8, rs=True), _fc(u=8, rs=False)), "electronics")
    assert (s["vals"], s["overall"], s["winner_index"], s["win_margin"]) == (
        [35.0, 20.0], [60.0, 71.8], 1, 11.8)


@pytest.mark.parametrize("state", ["unset", "on"])
def test_a13_two_checked_sides_unchanged(monkeypatch, state):
    """PIN / KILL -- two CHECKED sides are untouched: 2/0/6 vs 1/0/7 -> 47.5 / 38.8,
    dim winner Alpha by 8.7, 61.9 / 74.7, winner 1, margin 12.8; 2/0/6 vs flagged
    1 + 7 -> 47.5 / 26.2, Alpha by 21.3, 61.9 / 72.8, margin 10.9. Kills M-A3
    (absence on ANY populated fact_check)."""
    if state == "on":
        _on(monkeypatch)
    s = _score(_p1pair(_fc(v=2, u=6), _fc(v=1, u=7)), "electronics")
    assert (s["vals"], s["dim_winner"], s["overall"], s["winner_index"], s["win_margin"]) == (
        [47.5, 38.8], {"winner": "Alpha Phone One", "margin": 8.7}, [61.9, 74.7], 1, 12.8)
    s = _score(_p1pair(_fc(v=2, u=6), _fc(f=1, u=7)), "electronics")
    assert (s["vals"], s["dim_winner"], s["overall"], s["winner_index"], s["win_margin"]) == (
        [47.5, 26.2], {"winner": "Alpha Phone One", "margin": 21.3}, [61.9, 72.8], 1, 10.9)


# ---------------------------------------------------------------------------
# A9 / A10 -- the reader (truth table, per call, coupling both ways)
# ---------------------------------------------------------------------------
def _reader():
    from app.services import scoring_service
    fn = getattr(scoring_service, "reliability_unchecked_absence_enabled", None)
    assert fn is not None, (
        "ABSENT BEHAVIOUR: scoring_service.reliability_unchecked_absence_enabled() "
        "does not exist")
    return fn


def test_a9_reader_truth_table_and_per_call(monkeypatch):
    """RED -- the reader: with renorm ON, true/TRUE/" true "/1/yes/on -> True;
    false/""/0/no/unset -> False; a flip between two calls is honoured (read per
    call). Kills M-A5 (no .strip().lower())."""
    fn = _reader()
    monkeypatch.setenv(RENORM, "true")
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
    monkeypatch.setenv(FLAG, "false")
    assert fn() is False


def test_a10_reader_coupled_to_missing_dim_renorm(monkeypatch):
    """RED -- R2 coupling pinned both ways: flag ON + renorm unset/"false" -> False;
    renorm ON + flag unset -> False; both ON -> True. Kills M-A6."""
    fn = _reader()
    monkeypatch.setenv(FLAG, "true")
    monkeypatch.delenv(RENORM, raising=False)
    assert fn() is False
    monkeypatch.setenv(RENORM, "false")
    assert fn() is False
    monkeypatch.setenv(RENORM, "true")
    assert fn() is True
    monkeypatch.delenv(FLAG, raising=False)
    assert fn() is False


# ---------------------------------------------------------------------------
# A11 -- honest-absence composition; A12 -- the two flag-OFF-only rubric pins
# ---------------------------------------------------------------------------
def test_a11_pv_none_off_half():
    """PIN -- 0/0/8 with price_verified None (the #106 honest-absence shape) ->
    0.3 with the flag unset."""
    assert _svc()._score_reliability(_fc(u=8, pv=None)) == pytest.approx(0.3)


def test_a11_pv_none_on_half(monkeypatch):
    """RED -- the same input -> None under the flag (+ renorm). HEAD 0.3."""
    _on(monkeypatch)
    got = _svc()._score_reliability(_fc(u=8, pv=None))
    assert got is None, "ABSENT BEHAVIOUR: 0/0/8 pv None scores %r under the flag" % (got,)


@pytest.mark.parametrize("state", ["unset", "flag_only"])
def test_a12_rubric_pins_run_flag_off(monkeypatch, state):
    """PIN -- tests/test_fact_checking.py::...::test_flagged_scores_below_unverified_
    in_reliability (and test_fabricated_citation_no_longer_outscores_training)
    compare an all-unverified _score_reliability with `<`: under the Part A flag
    (+ renorm) that input is None, so those pins are FLAG-OFF-ONLY by construction
    (the PR says so). With the flag unset -- and with the flag alone, renorm unset
    (coupled OFF) -- both inputs are numbers and flagged < unverified holds."""
    if state == "flag_only":
        monkeypatch.setenv(FLAG, "true")
    s = _svc()
    flagged = s._score_reliability(
        {"specs_verified": 0, "specs_likely": 0, "specs_flagged": 1, "specs_unverified": 0})
    unverified = s._score_reliability(
        {"specs_verified": 0, "specs_likely": 0, "specs_flagged": 0, "specs_unverified": 1})
    assert isinstance(flagged, float) and isinstance(unverified, float)
    assert flagged < unverified


# ---------------------------------------------------------------------------
# A14 -- composition with ENABLE_BUNDLE_C_SCORING (R2)
# ---------------------------------------------------------------------------
def test_a14_composes_with_bundle_c(monkeypatch):
    """RED -- flag ON + renorm + ENABLE_BUNDLE_C_SCORING=true on the probe-1 pair
    2/0/6 vs 0/0/8: no exception, the unchecked side is absent (in missing_data)
    and the pair scores like the empty-side equivalent (64.4 / 81.0, winner 1,
    margin 16.6, measured on the design probe). HEAD: 47.5 / 30.0 scored."""
    _on(monkeypatch)
    monkeypatch.setenv(BUNDLE_C, "true")
    got = _score(_p1pair(_fc(v=2, u=6), _fc(u=8)), "electronics")
    ref = _score(_p1pair(_fc(v=2, u=6), {}), "electronics")
    assert got["md"] == [False, True] and got == ref, (
        "ABSENT BEHAVIOUR: under bundle-C the unchecked side still scores: %r vs %r" % (got, ref))
