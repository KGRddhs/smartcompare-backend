"""S78-TG (session 78, 2026-10-14) -- RED file: the residual guard for the Tier-2 / Tier-3
spec fills (ENABLE_TIER_FILL_RESIDUAL_GUARD + TAIL_RESERVE_SECONDS).

Authoritative: .qa-s78/S78_TG_UNIT_SPEC.md (section 4, rows R1a-R16 + the mutation table
4.1), RULINGS_S78_TG_SM.md (TG1-TG6) and RULINGS_S78_TG_SM_SPEC_REVIEW.md (TG-A1..A7; they
win). Every file:line below is at main e0f3e475; scs = app/services/structured_comparison_service.py.

RED at e0f3e475 unless a node says PIN. A RED node fails on an AssertionError (the helper the
unit adds is missing, the tier stub was called, or the mark / key / line is absent); a PIN is
green at e0f3e475 and must stay green (the flag-OFF / no-skip contract; it kills post-GREEN
mutants). R17 is the existing node
tests/test_s75_fanout_identity.py::test_FY25_flag_off_compare_identity_matches_main.

Contract this file fixes for GREEN (the spec's names):
  * scs._tail_reserve_seconds() -> _float_knob("TAIL_RESERVE_SECONDS", 6.5) (TG2).
  * scs._tier_fill_residual_short(residual, wall) -> residual < wall + reserve (TG3, strict).
  * StructuredComparisonService._tier_fill_skipped: list of {"product": <slot>, "tier":
    "tier2"|"tier3"}, reset per run at both entries; appended once per skip under the flag.
  * one INFO `[L2.6] <tier> skipped residual=<x.x>s product=<i>` per skip (TG4).
  * _stamp_unit_metadata writes metadata.tier_fill_skipped (a sorted COPY) only when the list
    is non-empty, without re-reading the flag (Q4).
  * a tier with nothing to fill (the subtype-filtered non-negotiables all present, or the D1
    no-fabrication veto ON) is called exactly as at base: no line, no mark (Q1 / TG-A2).

Hygiene: pure ASCII, LF; bounded runner only; conftest netguard on (every network leaf is
faked); no credential shape anywhere; stage timings are driven through the module global
`_DEBUG_STAGE_TIMINGS` (TG-A1), never through the env; "no mark" in a PIN is read with
getattr(..., []) or through the stamp, never as a direct attribute read (TG-A4).
"""
from __future__ import annotations

import asyncio
import logging
import re
import time
from contextlib import contextmanager
from unittest.mock import AsyncMock, patch

import pytest

# Q6 / TG-A7: the identity harness's helpers (never a test_* name). Importing the module first
# also applies its import-time OPENAI_API_KEY default before scs is imported.
from tests.test_s75_fanout_identity import QUERY, _complete, _scenario  # noqa: E402

import app.main  # noqa: E402,F401  (configure_logging at collection, the T18 precedent)
import app.services.structured_comparison_service as scs  # noqa: E402

SCS_LOGGER = "app.services.structured_comparison_service"
SKIP_RE = re.compile(r"^\[L2\.6\] (tier2|tier3) skipped residual=-?\d+\.\ds product=\d+$")
UNIT_ENV = ("ENABLE_TIER_FILL_RESIDUAL_GUARD", "TAIL_RESERVE_SECONDS",
            "ENABLE_PHASE2_RESIDUAL_GUARD", "PHASE2_MIN_RESIDUAL_SECONDS",
            "ENABLE_SPECS_NO_FABRICATION")
PRODUCT = {"brand": "", "name": "Ajmal Aristocrat", "variant": None, "category": "fragrances",
           "search_query": "Ajmal Aristocrat", "_explicit": True}
PRODUCT_B = {"brand": "", "name": "Rasasi Hawas", "variant": None, "category": "fragrances",
             "search_query": "Rasasi Hawas", "_explicit": True}
# longevity (a fragrances non-negotiable, extraction_service.py:375) is missing.
SPECS_GAP = {"concentration": "EDP", "volume_ml": 100, "scent_family": "woody"}
# R10d: a TV whose only gaps are the four electronics non-negotiables its subtype drops
# (extraction_service.py:319, electronics.tv drops battery / processor / ram / rear_camera).
TV = {"brand": "Samsung", "name": "Neo QLED 55 TV", "variant": None, "category": "electronics",
      "search_query": "Samsung Neo QLED 55 TV", "_explicit": True}
SPECS_TV = {"screen_size": "55 in", "panel_type": "QLED"}
BOTH = [{"product": 0, "tier": "tier2"}, {"product": 0, "tier": "tier3"}]
FOUR = [{"product": 0, "tier": "tier2"}, {"product": 0, "tier": "tier3"},
        {"product": 1, "tier": "tier2"}, {"product": 1, "tier": "tier3"}]


# ===========================================================================
# helpers
# ===========================================================================
class _NoRead:
    """A deadline stand-in that fails the test if a flag-OFF path reads it (copied from
    tests/test_s75_fanout_starve.py:226-233)."""

    def _boom(self, *_a, **_k):
        raise AssertionError("S78-TG: the flag-OFF tier path read _compare_deadline")

    __sub__ = __rsub__ = __lt__ = __le__ = __gt__ = __ge__ = __float__ = _boom


@pytest.fixture(autouse=True)
def _unit_env(monkeypatch):
    for name in UNIT_ENV:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(scs, "_DEBUG_STAGE_TIMINGS", False)  # TG-A1: never via the env


@pytest.fixture
def svc():
    return scs.StructuredComparisonService()


@pytest.fixture
def parse_flags_off(monkeypatch):
    monkeypatch.delenv("ENABLE_PARSE_BUDGET", raising=False)
    monkeypatch.delenv("ENABLE_PARSE_PRESPLIT", raising=False)
    monkeypatch.delenv("PARSE_TIMEOUT_SECONDS", raising=False)


def _set_or_del(monkeypatch, name, raw):
    if raw is None:
        monkeypatch.delenv(name, raising=False)
    else:
        monkeypatch.setenv(name, raw)


@contextmanager
def _tier_mocks(svc, specs, calls):
    """tests/test_s75_fanout_starve.py::_phase_mocks (:236-276) with RECORDING tier stubs:
    the REAL _fetch_product_data runs to its return; every network leaf is faked; Phase 2
    runs (the rating / smart-fallback stubs return at once)."""

    async def _specs(*_a, **_k):
        return dict(specs)

    async def _none(*_a, **_k):
        return None

    async def _rating(*_a, **_k):
        return {"rating": None, "review_count": None, "rating_verified": False,
                "rating_source": None}

    async def _empty(*_a, **_k):
        return {}

    async def _search(*_a, **_k):
        return {"organic": [], "shopping": []}

    async def _tier2(**kwargs):
        calls.append(("tier2", kwargs))
        return {}

    async def _tier3(**kwargs):
        calls.append(("tier3", kwargs))
        return {}

    with patch.object(svc, "_get_specs", side_effect=_specs), \
            patch.object(svc, "_get_price", side_effect=_none), \
            patch.object(svc, "_get_reviews", side_effect=_none), \
            patch.object(svc, "_get_verified_rating", side_effect=_rating), \
            patch.object(svc, "_smart_fallback_extract", side_effect=_empty), \
            patch.object(svc, "_track_serper_cost", lambda *a, **k: None), \
            patch.object(scs, "search_web", _search), \
            patch.object(scs, "tier2_fill_non_negotiables", _tier2), \
            patch.object(scs, "tier3_synthesize_non_negotiables", _tier3), \
            patch.object(scs, "collect_retailer_ratings", lambda *a, **k: []), \
            patch.object(scs, "get_product_image_url", AsyncMock(return_value=None)):
        yield


async def _fetch(svc, *, product=PRODUCT, specs=SPECS_GAP, partial_slot=None):
    calls = []
    with _tier_mocks(svc, specs, calls):
        result = await asyncio.wait_for(
            svc._fetch_product_data(dict(product), "bahrain", True, True, nocache=True,
                                    partial_slot=partial_slot),
            timeout=20.0)
    return result, calls


def _tiers(calls):
    return [tier for tier, _kw in calls]


def _skip_lines(caplog):
    return [r.getMessage() for r in caplog.records
            if r.name == SCS_LOGGER and r.getMessage().startswith("[L2.6] tier")]


def _info_skip_lines(caplog):
    return [r.getMessage() for r in caplog.records
            if r.name == SCS_LOGGER and r.levelno == logging.INFO
            and r.getMessage().startswith("[L2.6] tier")]


def _seed_partial(svc, result):
    svc._partial_build_ctx = {"query": "A vs B", "region": "bahrain", "from_cache": False,
                              "user_preferences": None, "category_used": "fragrances",
                              "category_switched": False, "original_category": None}
    svc._partial_product_data = [result, dict(result, name="Rasasi Hawas",
                                              full_name="Rasasi Hawas")]
    svc._partial_scoring_result = None
    svc._partial_comparison = None
    svc._partial_product_names = None
    svc._shopping_items_cache = {}


def _partial_metadata(svc, result):
    _seed_partial(svc, result)
    response = svc._build_partial_response(elapsed_seconds=1.0)
    return response.get("metadata") or {}


def _marks(svc):
    return getattr(svc, "_tier_fill_skipped", None)


def _assert_base_kwargs(calls, product, result):
    """R2 / R6: each tier stub called ONCE with exactly the base kwargs, specs_so_far being
    the product's own specs dict (the same object both tiers see)."""
    assert _tiers(calls) == ["tier2", "tier3"], calls
    for _tier, kwargs in calls:
        assert set(kwargs) == {"brand", "name", "variant", "category", "specs_so_far"}, kwargs
        assert kwargs["brand"] == product["brand"], kwargs
        assert kwargs["name"] == product["name"], kwargs
        assert kwargs["variant"] is None, kwargs
        assert kwargs["category"] == product["category"], kwargs
        assert kwargs["specs_so_far"] is result["specs"], (
            "the tier must see the product's own specs dict object")


def _assert_no_skip(svc, caplog, result):
    assert _skip_lines(caplog) == [], _skip_lines(caplog)
    assert getattr(svc, "_tier_fill_skipped", []) == [], getattr(svc, "_tier_fill_skipped", [])
    assert "tier_fill_skipped" not in _partial_metadata(svc, result)


# ===========================================================================
# R1a / R1b -- both tiers skipped on a short residual, the line, the mark, the partial key
# ===========================================================================
@pytest.mark.asyncio
@pytest.mark.parametrize("slot, want_product", [(None, 0), (1, 1)], ids=["R1a_slot_none",
                                                                         "R1b_slot_1"])
async def test_R1_short_residual_skips_both_tiers(svc, monkeypatch, caplog, slot, want_product):
    """R1a / R1b (TG3, TG4): flag ON, reserve 6.5 (unset), residual 2.0 s < 4.0 + 6.5 and
    < 3.0 + 6.5, longevity missing -> neither tier is called; two INFO lines (tier2 then
    tier3) naming the product slot (None -> 0); the marks list; the partial builder's
    metadata.tier_fill_skipped. RED at e0f3e475: both tiers always run."""
    monkeypatch.setenv("ENABLE_TIER_FILL_RESIDUAL_GUARD", "true")
    svc._compare_deadline = time.monotonic() + 2.0
    caplog.set_level(logging.INFO, logger=SCS_LOGGER)
    result, calls = await _fetch(svc, partial_slot=slot)
    assert calls == [], (
        "S78-TG: a tier ran with a 2.0 s residual below wall + 6.5 s and the flag ON: %r"
        % (_tiers(calls),))
    lines = _info_skip_lines(caplog)
    assert len(lines) == 2, lines
    assert all(SKIP_RE.match(line) for line in lines), lines
    assert [SKIP_RE.match(line).group(1) for line in lines] == ["tier2", "tier3"], lines
    assert all(line.endswith(" product=%d" % want_product) for line in lines), lines
    want = [{"product": want_product, "tier": "tier2"}, {"product": want_product, "tier": "tier3"}]
    assert _marks(svc) == want, _marks(svc)
    metadata = _partial_metadata(svc, result)
    assert metadata.get("tier_fill_skipped") == want, metadata


# ===========================================================================
# R2 -- PIN: ample residual, both tiers called exactly as at base
# ===========================================================================
@pytest.mark.asyncio
async def test_R2_pin_ample_residual_runs_both_tiers_as_at_base(svc, monkeypatch, caplog):
    """R2 PIN: flag ON, residual 100 s >= every threshold -> each tier called once with the
    base kwargs (specs_so_far IS result["specs"]); no line; no mark; no partial key."""
    monkeypatch.setenv("ENABLE_TIER_FILL_RESIDUAL_GUARD", "true")
    svc._compare_deadline = time.monotonic() + 100.0
    caplog.set_level(logging.INFO, logger=SCS_LOGGER)
    result, calls = await _fetch(svc)
    _assert_base_kwargs(calls, PRODUCT, result)
    _assert_no_skip(svc, caplog, result)


# ===========================================================================
# R3 / R4 -- the two decisions are independent; the walls are read at call time
# ===========================================================================
@pytest.mark.asyncio
@pytest.mark.parametrize("big, skipped, ran", [("_TIER2_WALL_SECONDS", "tier2", "tier3"),
                                               ("_TIER3_WALL_SECONDS", "tier3", "tier2")],
                         ids=["R3_tier2_wall_40", "R4_tier3_wall_40"])
async def test_R3_R4_independent_decisions(svc, monkeypatch, caplog, big, skipped, ran):
    """R3 / R4 (TG3): one wall patched to 40.0 s (read from the module global at call time),
    residual 25 s: the big-wall tier is skipped (25 < 46.5) and the other one runs
    (25 >= 9.5 / 10.5). One line, one mark. RED at e0f3e475: both tiers run."""
    monkeypatch.setenv("ENABLE_TIER_FILL_RESIDUAL_GUARD", "true")
    monkeypatch.setattr(scs, big, 40.0)
    svc._compare_deadline = time.monotonic() + 25.0
    caplog.set_level(logging.INFO, logger=SCS_LOGGER)
    _result, calls = await _fetch(svc)
    assert _tiers(calls) == [ran], (
        "S78-TG: with %s = 40.0 and a 25 s residual only %s may run; ran %r"
        % (big, ran, _tiers(calls)))
    lines = _info_skip_lines(caplog)
    assert len(lines) == 1 and SKIP_RE.match(lines[0]), lines
    assert SKIP_RE.match(lines[0]).group(1) == skipped, lines
    assert _marks(svc) == [{"product": 0, "tier": skipped}], _marks(svc)


# ===========================================================================
# R5a / R5b -- PIN: no deadline -> never skip
# ===========================================================================
@pytest.mark.asyncio
@pytest.mark.parametrize("how", ["R5a_none", "R5b_missing"])
async def test_R5_pin_no_deadline_never_skips(svc, monkeypatch, caplog, how):
    """R5a / R5b PIN (TG3): flag ON, reserve 1000, `_compare_deadline` None or absent (a
    __new__-built instance) -> both tiers called, no line, no mark."""
    monkeypatch.setenv("ENABLE_TIER_FILL_RESIDUAL_GUARD", "true")
    monkeypatch.setenv("TAIL_RESERVE_SECONDS", "1000")
    if how == "R5a_none":
        svc._compare_deadline = None
    else:
        del svc._compare_deadline
    caplog.set_level(logging.INFO, logger=SCS_LOGGER)
    result, calls = await _fetch(svc)
    assert _tiers(calls) == ["tier2", "tier3"], calls
    _assert_no_skip(svc, caplog, result)


# ===========================================================================
# R6 -- PIN: flag OFF never reads the deadline and calls both tiers as at base
# ===========================================================================
@pytest.mark.asyncio
async def test_R6_pin_flag_off_never_reads_the_deadline(svc, monkeypatch, caplog):
    """R6 PIN (TG4 flag-OFF identity): flag unset, reserve 1000, a reading stand-in as the
    deadline -> both tiers called with the base kwargs; no line; no mark; no key; the
    stand-in never raised."""
    monkeypatch.setenv("TAIL_RESERVE_SECONDS", "1000")
    svc._compare_deadline = _NoRead()
    caplog.set_level(logging.INFO, logger=SCS_LOGGER)
    result, calls = await _fetch(svc)
    _assert_base_kwargs(calls, PRODUCT, result)
    _assert_no_skip(svc, caplog, result)


# ===========================================================================
# R7 -- the TAIL_RESERVE_SECONDS knob table (TG2)
# ===========================================================================
KNOB_ROWS = [(None, 6.5), ("", 6.5), ("   ", 6.5), ("abc", 6.5), ("0", 6.5), ("-1", 6.5),
             ("nan", 6.5), ("inf", 6.5), ("-inf", 6.5), ("3.5", 3.5), (" 7.25 ", 7.25),
             ("1e3", 1000.0)]
KNOB_IDS = ["unset", "empty", "blank", "abc", "zero", "negative", "nan", "inf", "neg_inf",
            "3.5", "padded_7.25", "1e3"]


@pytest.mark.parametrize("raw, want", KNOB_ROWS, ids=KNOB_IDS)
def test_R7_tail_reserve_knob_table(monkeypatch, raw, want):
    """R7 (TG2, the S65d float-knob rule): unset / blank / garbage / non-finite / <= 0 ->
    6.5, read per call. RED at e0f3e475: scs has no _tail_reserve_seconds."""
    reader = getattr(scs, "_tail_reserve_seconds", None)
    assert callable(reader), "S78-TG: scs has no _tail_reserve_seconds() knob reader"
    _set_or_del(monkeypatch, "TAIL_RESERVE_SECONDS", raw)
    got = reader()
    assert isinstance(got, float) and got == want, (raw, got)


# ===========================================================================
# R8-on / R8-off -- the flag-reader table (TG1)
# ===========================================================================
@pytest.mark.asyncio
@pytest.mark.parametrize("raw", ["true", "TRUE", " true ", "1", "yes", "ON", "on"],
                         ids=["true", "TRUE", "padded_true", "1", "yes", "ON", "on"])
async def test_R8_on_flag_reader_truthy_values_skip(svc, monkeypatch, caplog, raw):
    """R8-on (TG1: `.strip().lower()` in the house truthy set): each value turns the guard ON
    -> residual 2.0 s skips both tiers, two lines. RED at e0f3e475: the tiers run."""
    monkeypatch.setenv("ENABLE_TIER_FILL_RESIDUAL_GUARD", raw)
    svc._compare_deadline = time.monotonic() + 2.0
    caplog.set_level(logging.INFO, logger=SCS_LOGGER)
    _result, calls = await _fetch(svc)
    assert calls == [], (
        "S78-TG: flag value %r must read ON; the tiers ran: %r" % (raw, _tiers(calls)))
    assert len(_info_skip_lines(caplog)) == 2, _info_skip_lines(caplog)


@pytest.mark.asyncio
@pytest.mark.parametrize("raw", [None, "", "false", "0", "no", "off", "garbage", "tru e"],
                         ids=["unset", "empty", "false", "0", "no", "off", "garbage", "tru_e"])
async def test_R8_off_pin_flag_reader_falsy_values_never_read(svc, monkeypatch, caplog, raw):
    """R8-off PIN (TG1): every non-truthy value is OFF -> the deadline (a reading stand-in) is
    never read, both tiers called, no line, no mark."""
    _set_or_del(monkeypatch, "ENABLE_TIER_FILL_RESIDUAL_GUARD", raw)
    svc._compare_deadline = _NoRead()
    caplog.set_level(logging.INFO, logger=SCS_LOGGER)
    result, calls = await _fetch(svc)
    assert _tiers(calls) == ["tier2", "tier3"], calls
    _assert_no_skip(svc, caplog, result)


# ===========================================================================
# R9 -- the pure decision table (TG3: strict < on wall + reserve)
# ===========================================================================
DECISION_ROWS = [(None, 10.49, 4.0, True), (None, 10.5, 4.0, False), (None, 10.51, 4.0, False),
                 (None, 9.49, 3.0, True), (None, 9.5, 3.0, False), (None, -1.0, 4.0, True),
                 ("1", 4.99, 4.0, True), ("1", 5.0, 4.0, False)]
DECISION_IDS = ["10.49_w4", "10.5_w4_boundary", "10.51_w4", "9.49_w3", "9.5_w3_boundary",
                "negative_w4", "reserve1_4.99_w4", "reserve1_5.0_w4_boundary"]


@pytest.mark.parametrize("reserve, residual, wall, want", DECISION_ROWS, ids=DECISION_IDS)
def test_R9_residual_short_decision_table(monkeypatch, reserve, residual, wall, want):
    """R9 (TG3): skip iff residual < wall + reserve, STRICTLY (10.5 and 9.5 are exact binary
    floats); the reserve is the knob read per call. RED at e0f3e475: no
    _tier_fill_residual_short."""
    decide = getattr(scs, "_tier_fill_residual_short", None)
    assert callable(decide), "S78-TG: scs has no _tier_fill_residual_short(residual, wall)"
    _set_or_del(monkeypatch, "TAIL_RESERVE_SECONDS", reserve)
    assert decide(residual, wall) is want, (reserve, residual, wall)


# ===========================================================================
# R10a-R10d -- the "has work" predicate (Q1, TG-A2)
# ===========================================================================
@pytest.mark.asyncio
async def test_R10a_pin_nothing_missing_is_never_skipped(svc, monkeypatch, caplog):
    """R10a PIN: every fragrances non-negotiable present -> the tiers are called as at base
    (they no-op themselves) even on a short residual; no line, no mark."""
    monkeypatch.setenv("ENABLE_TIER_FILL_RESIDUAL_GUARD", "true")
    svc._compare_deadline = time.monotonic() + 2.0
    caplog.set_level(logging.INFO, logger=SCS_LOGGER)
    result, calls = await _fetch(svc, specs={"concentration": "EDP", "longevity": "8h"})
    assert _tiers(calls) == ["tier2", "tier3"], calls
    _assert_no_skip(svc, caplog, result)


@pytest.mark.asyncio
async def test_R10b_pin_no_fabrication_veto_is_never_skipped(svc, monkeypatch, caplog):
    """R10b PIN: longevity missing but ENABLE_SPECS_NO_FABRICATION ON (the D1 veto: the tiers
    would return {} at once) -> called as at base; no skip line; no mark."""
    monkeypatch.setenv("ENABLE_TIER_FILL_RESIDUAL_GUARD", "true")
    monkeypatch.setenv("ENABLE_SPECS_NO_FABRICATION", "true")
    svc._compare_deadline = time.monotonic() + 2.0
    caplog.set_level(logging.INFO, logger=SCS_LOGGER)
    result, calls = await _fetch(svc)
    assert _tiers(calls) == ["tier2", "tier3"], calls
    _assert_no_skip(svc, caplog, result)


@pytest.mark.asyncio
async def test_R10c_na_value_counts_as_missing(svc, monkeypatch, caplog):
    """R10c: the only gap is concentration == "N/A" (kept by _clean_specs, scs:3376) -> the
    same "N/A" / "" rule as the tiers -> both skipped, two lines. RED at e0f3e475."""
    monkeypatch.setenv("ENABLE_TIER_FILL_RESIDUAL_GUARD", "true")
    svc._compare_deadline = time.monotonic() + 2.0
    caplog.set_level(logging.INFO, logger=SCS_LOGGER)
    result, calls = await _fetch(svc, specs={"concentration": "N/A", "longevity": "8h"})
    assert result["specs"].get("concentration") == "N/A", result["specs"]
    assert calls == [], (
        "S78-TG: an \"N/A\" non-negotiable is a gap; the tiers ran: %r" % (_tiers(calls),))
    assert len(_info_skip_lines(caplog)) == 2, _info_skip_lines(caplog)
    assert _marks(svc) == BOTH, _marks(svc)


@pytest.mark.asyncio
async def test_R10d_pin_subtype_dropped_gaps_are_never_skipped(svc, monkeypatch, caplog):
    """R10d PIN (TG-A2): an electronics TV whose only gaps are fields its subtype drops ->
    no work for either tier -> both called exactly as at base on a short residual; no line,
    no mark. Kills M23 (the predicate ignores the subtype)."""
    from app.services.extraction_service import non_negotiable_fields_for

    subtype = scs._detect_subtype(TV["brand"], TV["name"], TV["category"])
    assert subtype == "electronics.tv", subtype
    assert non_negotiable_fields_for("electronics", subtype) == [], subtype
    plain = non_negotiable_fields_for("electronics")
    assert plain and not any(field in SPECS_TV for field in plain), plain
    monkeypatch.setenv("ENABLE_TIER_FILL_RESIDUAL_GUARD", "true")
    svc._compare_deadline = time.monotonic() + 2.0
    caplog.set_level(logging.INFO, logger=SCS_LOGGER)
    result, calls = await _fetch(svc, product=TV, specs=SPECS_TV)
    _assert_base_kwargs(calls, TV, result)
    _assert_no_skip(svc, caplog, result)


# ===========================================================================
# R11 -- the success-path stamps (REST body, stream complete) through the full pipeline
# ===========================================================================
def test_R11_full_pipeline_marks_the_rest_success_and_stream_complete(monkeypatch):
    """R11 (TG4): the identity harness (tests/test_s75_fanout_identity.py, real entries and
    the real _fetch_product_data, every leaf faked), the flag ON and TAIL_RESERVE_SECONDS
    1000 (set through monkeypatch: _scenario only pops its own UNIT_ENV names) -> both tiers
    skipped on both products; the REST success body and the stream `complete` payload carry
    metadata.tier_fill_skipped, sorted. The harness's electronics specs leave processor /
    ram / rear_camera missing. RED at e0f3e475: no key."""
    monkeypatch.setenv("ENABLE_TIER_FILL_RESIDUAL_GUARD", "true")
    monkeypatch.setenv("TAIL_RESERVE_SECONDS", "1000")
    rest = asyncio.run(_scenario("rest", QUERY))
    assert rest["payload"].get("success") is True, rest["payload"]
    metadata = rest["payload"].get("metadata") or {}
    assert metadata.get("partial") is not True, metadata
    assert metadata.get("tier_fill_skipped") == FOUR, (
        "S78-TG: the REST success body lacks metadata.tier_fill_skipped: %r"
        % (metadata.get("tier_fill_skipped"),))
    stream = asyncio.run(_scenario("stream", QUERY))
    complete = _complete(stream["payload"])
    stream_meta = complete.get("metadata") or {}
    assert stream_meta.get("partial") is not True, stream_meta
    assert stream_meta.get("tier_fill_skipped") == FOUR, stream_meta.get("tier_fill_skipped")


# ===========================================================================
# R12 -- PIN: both entries reset the marks per run (the FY4 pattern)
# ===========================================================================
def _install_presplit_pipeline(svc, monkeypatch):
    """tests/test_s75_fanout_starve.py:756 (a copy): the LLM parse is a stub, the category
    resolution is a stub, _fetch_product_data seeds the early buffer and hangs, so the 0.5 s
    cap builds a partial from the early buffer."""
    monkeypatch.setattr(scs, "STREAM_HARD_CAP_SECONDS", 0.5)
    parsed = {"products": [
        {"brand": "Apple", "name": "iPhone 15", "variant": None, "category": "electronics",
         "search_query": "Apple iPhone 15"},
        {"brand": "Samsung", "name": "Galaxy S24", "variant": None, "category": "electronics",
         "search_query": "Samsung Galaxy S24"}], "comparison_type": "value"}

    async def _parse(_query):
        await asyncio.sleep(0.01)
        return dict(parsed), {"prompt_tokens": 10, "completion_tokens": 5}

    monkeypatch.setattr(scs, "parse_product_query", _parse)

    async def _resolve(products, selected_category, parser_path=False):
        return ("electronics", False, None)

    monkeypatch.setattr(scs, "_resolve_pair_category", _resolve)

    async def _hang(product_info, region, include_specs, include_reviews, nocache=False,
                    partial_slot=None):
        if partial_slot is not None and isinstance(svc._early_specs_buffer, list):
            svc._early_specs_buffer[partial_slot] = {
                "brand": "", "name": product_info["name"], "full_name": product_info["name"],
                "category": "electronics", "specs": {"display": "6.1 in"}, "price": None,
            }
        await asyncio.sleep(30)

    monkeypatch.setattr(svc, "_fetch_product_data", _hang)


async def _stream_to_complete(gen, limit=60):
    terminal = None
    events = 0
    try:
        async for kind, payload in gen:
            events += 1
            if kind == "complete" or events > limit:
                terminal = (kind, payload)
                break
    finally:
        await gen.aclose()
    return terminal


@pytest.mark.asyncio
@pytest.mark.parametrize("entry", ["rest", "stream"])
async def test_R12_pin_entries_reset_stale_marks(svc, monkeypatch, parse_flags_off, entry):
    """R12 PIN (M20): a stale mark from an earlier run of the instance never reaches the
    REST partial or the stream partial: each entry resets the list per run. Flag unset."""
    _install_presplit_pipeline(svc, monkeypatch)
    svc._tier_fill_skipped = [{"product": 9, "tier": "tier2"}]
    if entry == "rest":
        body = await svc.compare_from_text("iPhone 15 vs Galaxy S24", nocache=True)
    else:
        terminal = await _stream_to_complete(
            svc.compare_from_text_streaming("iPhone 15 vs Galaxy S24", nocache=True))
        assert terminal is not None and terminal[0] == "complete", terminal
        body = terminal[1]
    metadata = body.get("metadata") or {}
    assert metadata.get("partial") is True, metadata
    assert "tier_fill_skipped" not in metadata, metadata


# ===========================================================================
# R13 / R14 -- the stamp: a sorted copy, no flag re-read; nothing on an empty list
# ===========================================================================
def test_R13_stamp_writes_a_sorted_copy_without_rereading_the_flag(svc):
    """R13 (TG-A6, Q4, Q5): flag UNSET (a skip recorded under the flag is stamped without a
    re-read); the stamp sorts by (product, tier) and writes a copy: mutating an element of
    the stamped list or appending to it leaves the instance list unchanged. RED at
    e0f3e475: no key."""
    raw = [{"product": 1, "tier": "tier3"}, {"product": 0, "tier": "tier3"},
           {"product": 1, "tier": "tier2"}, {"product": 0, "tier": "tier2"}]
    svc._tier_fill_skipped = [dict(m) for m in raw]
    resp = {"metadata": {}}
    svc._stamp_unit_metadata(resp)
    out = resp["metadata"].get("tier_fill_skipped")
    assert out == FOUR, "S78-TG: the stamp wrote %r, want the sorted marks" % (out,)
    out[0]["tier"] = "x"
    out.append({"product": 7, "tier": "tier2"})
    assert svc._tier_fill_skipped == raw, svc._tier_fill_skipped


def test_R14_pin_empty_marks_and_non_dict_metadata(svc):
    """R14 PIN: an empty list writes no key; a non-dict metadata never raises."""
    svc._tier_fill_skipped = []
    resp = {"metadata": {}}
    svc._stamp_unit_metadata(resp)
    assert "tier_fill_skipped" not in resp["metadata"], resp
    svc._tier_fill_skipped = [{"product": 0, "tier": "tier2"}]
    for odd in ({"metadata": None}, {"metadata": ["x"]}, {}):
        svc._stamp_unit_metadata(odd)
        assert "tier_fill_skipped" not in odd, odd


# ===========================================================================
# R15 -- PIN: a skipped tier still records its stage-timing key
# ===========================================================================
@pytest.mark.asyncio
async def test_R15_pin_skipped_tiers_still_record_stage_timings(svc, monkeypatch):
    """R15 PIN (TG-A1, M21): `_DEBUG_STAGE_TIMINGS` True (the module global), flag ON,
    residual 2.0 s -> result["_stage_timings_ms"] has tier2_fallback_ms and tier3_synth_ms
    (floats >= 0), as at base."""
    monkeypatch.setattr(scs, "_DEBUG_STAGE_TIMINGS", True)
    monkeypatch.setenv("ENABLE_TIER_FILL_RESIDUAL_GUARD", "true")
    svc._compare_deadline = time.monotonic() + 2.0
    result, _calls = await _fetch(svc)
    timings = result.get("_stage_timings_ms") or {}
    for key in ("tier2_fallback_ms", "tier3_synth_ms"):
        assert key in timings, (key, sorted(timings))
        assert isinstance(timings[key], float) and timings[key] >= 0.0, (key, timings[key])


# ===========================================================================
# R16 -- two products in one gather: per-product marks on the shared list
# ===========================================================================
@pytest.mark.asyncio
async def test_R16_two_products_in_one_gather_mark_their_own_slots(svc, monkeypatch, caplog):
    """R16 (TG4): partial_slot 0 and 1 gathered on ONE instance, flag ON, residual 2.0 s ->
    four skips; sorted marks [(0,t2),(0,t3),(1,t2),(1,t3)]; two lines per slot. RED at
    e0f3e475: the tiers run."""
    monkeypatch.setenv("ENABLE_TIER_FILL_RESIDUAL_GUARD", "true")
    svc._compare_deadline = time.monotonic() + 2.0
    caplog.set_level(logging.INFO, logger=SCS_LOGGER)
    calls = []
    with _tier_mocks(svc, SPECS_GAP, calls):
        await asyncio.wait_for(asyncio.gather(
            svc._fetch_product_data(dict(PRODUCT), "bahrain", True, True, nocache=True,
                                    partial_slot=0),
            svc._fetch_product_data(dict(PRODUCT_B), "bahrain", True, True, nocache=True,
                                    partial_slot=1)), timeout=20.0)
    assert calls == [], "S78-TG: tiers ran on a 2.0 s residual: %r" % (_tiers(calls),)
    marks = _marks(svc)
    assert isinstance(marks, list), marks
    assert sorted(marks, key=lambda m: (m["product"], m["tier"])) == FOUR, marks
    lines = _info_skip_lines(caplog)
    assert len(lines) == 4 and all(SKIP_RE.match(line) for line in lines), lines
    for slot in (0, 1):
        mine = [line for line in lines if line.endswith(" product=%d" % slot)]
        assert sorted(SKIP_RE.match(line).group(1) for line in mine) == ["tier2", "tier3"], (
            slot, lines)
