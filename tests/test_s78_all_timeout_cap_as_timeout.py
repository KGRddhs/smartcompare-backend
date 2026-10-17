"""S78-F8 -- report an all-timeout hard cap as TIMEOUT, not INSUFFICIENT_DATA.

Unit spec: .qa-s78/S78_F8_UNIT_SPEC.md (base main e0f3e475), as amended by the Fable rulings
RULINGS_S78_F8_SPEC_REVIEW.md (R1-R13). Flag ENABLE_ALL_TIMEOUT_CAP_AS_TIMEOUT (default OFF,
read per call through scs._flag_on).

Design under test (rulings R2/R3/R7):
  * scs._phase1_race_outcome(res) classifies one Phase-1 gather result: an asyncio.TimeoutError
    instance -> "timeout", any other BaseException instance -> "error", anything else -> "ok".
  * StructuredComparisonService._phase1_race_outcomes: slot -> {race key -> outcome}, set to {}
    in __init__ and reset at BOTH entries; under the flag (and partial_slot not None) the two
    DATA races (specs, price) are recorded EAGERLY by done-callbacks (a cancelled task records
    nothing), and the post-loop block writes all four keys in phase1_keys order.
  * _cap_all_data_races_timed_out(): flag first; per populated buffer slot, usable data
    (specs or price not None) -> False; no record + a landed specs/price key -> False; a
    recorded specs/price outcome other than "timeout" -> False; an ABSENT data race counts as
    timed out; True only with at least one populated slot.
  * The REST hard-cap handler's INSUFFICIENT_DATA branch returns the base TIMEOUT body (five
    keys, no api_calls) when the predicate is True, with ONE WARNING line (R7 format).

RED = fails at base e0f3e475 on an AssertionError naming the absent behaviour (a missing
symbol is read with getattr(..., None) INSIDE the test body and asserted; never an
ImportError / AttributeError / KeyError at collection or in the body) and passes after GREEN.
PIN = passes at base and must stay green.

Hygiene: pure ASCII, LF; the bounded runner only; the worktree conftest wires the netguard
(no host is ever resolved by these nodes except the route's fire-and-forget sentinel
attempts in F15); no credential-shaped literal; no personal value.
"""
from __future__ import annotations

import asyncio
import copy
import json
import logging
import re
from unittest.mock import patch

import pytest

from tests.test_s75_fanout_identity import FIXTURE, QUERY, _all_digests, _install, _new_state

import app.main  # noqa: F401  (configure_logging; the app for the route node)
import app.services.structured_comparison_service as scs

SCS_LOGGER = "app.services.structured_comparison_service"
FLAG = "ENABLE_ALL_TIMEOUT_CAP_AS_TIMEOUT"
UNIT_ENV = (FLAG, "ENABLE_EARLY_SPECS_STASH", "ENABLE_PARSE_PRESPLIT", "ENABLE_PARSE_BUDGET",
            "ENABLE_UNIFIED_SEARCH_BOUND", "ENABLE_PHASE2_RESIDUAL_GUARD",
            "ENABLE_TIER_FILL_RESIDUAL_GUARD", "DEBUG_STAGE_TIMINGS")
TIMEOUT_KEYS = {"success", "error", "code", "elapsed_seconds", "total_cost"}
INSUFF_KEYS = TIMEOUT_KEYS | {"api_calls"}
INCOMPLETE = "Comparison data was incomplete " + chr(0x2014) + " choose different products."
IDENTITY_KEYS = {"brand", "name", "full_name", "variant", "category", "query"}
CAP_PREFIX = "[L2.7] hard-cap: every"
CAP_RE = re.compile(
    r"^\[L2\.7\] hard-cap: every Phase-1 data race timed out or was cut "
    r"\(products=(\d+), data races recorded=(\d+), timed out=(\d+)\) "
    r"for query=.+ -- reporting TIMEOUT, not INSUFFICIENT_DATA$")
ALL4_TIMEOUT = {"specs": "timeout", "price": "timeout", "reviews": "timeout",
                "image_url": "timeout"}
FLAG_ON_VALUES = ["true", "TRUE", " true ", "1", "yes", "ON", "on"]
FLAG_OFF_VALUES = [None, "", "false", "0", "no", "off", "garbage", "tru e"]
PARSED_E = {"products": [
    {"brand": "Apple", "name": "iPhone 15", "variant": None, "category": "electronics",
     "search_query": "Apple iPhone 15"},
    {"brand": "Samsung", "name": "Galaxy S24", "variant": None, "category": "electronics",
     "search_query": "Samsung Galaxy S24"}], "comparison_type": "value"}
NAME_A = "iPhone 15"
NAME_B = "Galaxy S24"


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    for name in UNIT_ENV:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(scs, "_DEBUG_STAGE_TIMINGS", False)


def _set_flag(monkeypatch, value="true"):
    if value is None:
        monkeypatch.delenv(FLAG, raising=False)
    else:
        monkeypatch.setenv(FLAG, value)


def IDENT(name):
    """The six identity keys _fetch_product_data registers (scs:5503-5506)."""
    return {"brand": "", "name": name, "full_name": name, "variant": None,
            "category": "supplements", "query": name}


def _records(caplog):
    return [r for r in caplog.records if r.name == SCS_LOGGER]


def _cap_lines(caplog):
    """The D5 line: WARNING exactly (R6), the R7 prefix."""
    return [r for r in _records(caplog)
            if r.levelno == logging.WARNING and r.getMessage().startswith(CAP_PREFIX)]


def _cap_any(caplog):
    """Any record carrying the D5 prefix, at ANY level (for the 'no line' assertions)."""
    return [r for r in _records(caplog) if r.getMessage().startswith(CAP_PREFIX)]


def _no_usable_lines(caplog):
    return [r for r in _records(caplog) if "no usable partial" in r.getMessage()]


def _race_timeout_lines(caplog):
    return [r for r in _records(caplog)
            if r.getMessage().startswith("[L2.6] Phase 1 race timeout")]


def _one_cap_groups(caplog):
    lines = _cap_lines(caplog)
    assert len(lines) == 1, "S78-F8 D5: want exactly one WARNING hard-cap line, got %r" % (
        [r.getMessage() for r in _cap_any(caplog)],)
    m = CAP_RE.match(lines[0].getMessage())
    assert m, "S78-F8 D5: the hard-cap line does not match the R7 format: %r" % (
        lines[0].getMessage(),)
    return tuple(int(g) for g in m.groups())


def _rec(svc):
    return getattr(svc, "_phase1_race_outcomes", None)


def _assert_timeout_body(body):
    assert body.get("code") == "TIMEOUT", (
        "S78-F8: an all-timeout hard cap must report TIMEOUT, got code=%r" % (body.get("code"),))
    assert set(body) == TIMEOUT_KEYS, "S78-F8: the TIMEOUT body keys moved: %r" % (sorted(body),)
    assert body["success"] is False
    assert body["error"] == scs.TIMEOUT_FRIENDLY_MESSAGE
    assert isinstance(body["elapsed_seconds"], float)


def _assert_insufficient_body(body):
    assert body.get("code") == "INSUFFICIENT_DATA", "base verdict moved: %r" % (body.get("code"),)
    assert set(body) == INSUFF_KEYS, "base INSUFFICIENT_DATA keys moved: %r" % (sorted(body),)
    assert body["success"] is False
    assert body["error"] == INCOMPLETE
    assert "api_calls" in body


# ---------------------------------------------------------------- the flag-OFF stand-ins
class _NoReadDict(dict):
    """A _phase1_race_outcomes stand-in that records and refuses every read."""

    READS = []

    def _boom(self, *_a, **_k):
        _NoReadDict.READS.append("read")
        raise AssertionError("S78-F8: the flag-OFF path read _phase1_race_outcomes")

    __getitem__ = _boom
    get = _boom
    __contains__ = _boom
    __iter__ = _boom
    __len__ = _boom
    __bool__ = _boom
    keys = _boom
    items = _boom
    values = _boom


def _boom_property(name, reads):
    def _get(_self):
        reads.append(name)
        raise AssertionError("S78-F8: the flag-OFF predicate read %s" % name)
    return property(_get)


# ---------------------------------------------------------------- the hang-impl harness
def _hang_impl(svc, monkeypatch, seed, cap=0.2):
    """test_compare_timeout_graceful pattern: seed the stash, then hang past the cap."""
    monkeypatch.setattr(scs, "STREAM_HARD_CAP_SECONDS", cap)

    async def _impl(*_a, **_k):
        seed(svc)
        await asyncio.sleep(60)
    monkeypatch.setattr(svc, "_compare_from_text_impl", _impl)


def _seed_two_identities(svc):
    svc._early_specs_buffer = [IDENT("A"), IDENT("B")]


async def _run_rest(svc, caplog, **kw):
    caplog.set_level(logging.INFO, logger=SCS_LOGGER)
    return await asyncio.wait_for(svc.compare_from_text(QUERY, nocache=True, **kw), 30)


# ---------------------------------------------------------------- the real-entry harness
async def _raise_t(*_a, **_k):
    raise asyncio.TimeoutError()


async def _raise_rt(*_a, **_k):
    raise RuntimeError("s78f8")


async def _hang(*_a, **_k):
    await asyncio.sleep(60)


async def _none(*_a, **_k):
    return None


async def _reviews_ok(*_a, **_k):
    return {"summary": "ok"}


async def _specs_dict(*_a, **_k):
    return {"battery_mah": 4000, "display_size_in": 6.1}


async def _rating_ok(*_a, **_k):
    return {"rating": None, "review_count": None}


def _per_name(by_name, default):
    async def _leaf(brand, name, *a, **k):
        return await by_name.get(name, default)(brand, name, *a, **k)
    return _leaf


def _install_real(svc, monkeypatch, *, specs=_raise_t, price=_raise_t, reviews=_raise_t,
                  image=_raise_t, rating=_hang, cap=1.0):
    """Spec 1.5: the REAL compare_from_text -> REAL _compare_from_text_impl -> REAL
    _fetch_product_data x2 with every network leaf faked; the verified rating hangs by
    default so the cap fires in Phase 2 after both loops ran."""
    monkeypatch.setattr(scs, "STREAM_HARD_CAP_SECONDS", cap)

    async def _parse(_query):
        return json.loads(json.dumps(PARSED_E)), {"prompt_tokens": 10, "completion_tokens": 5}

    async def _resolve(products, selected_category, parser_path=False):
        return ("electronics", False, None)

    async def _search(*_a, **_k):
        return {"organic": [], "shopping": []}

    async def _empty(*_a, **_k):
        return {}

    async def _drugs(*_a, **_k):
        return []

    monkeypatch.setattr(scs, "parse_product_query", _parse)
    monkeypatch.setattr(scs, "_resolve_pair_category", _resolve)
    monkeypatch.setattr(scs, "search_web", _search)
    monkeypatch.setattr(scs, "tier2_fill_non_negotiables", _empty)
    monkeypatch.setattr(scs, "tier3_synthesize_non_negotiables", _empty)
    monkeypatch.setattr(scs, "collect_retailer_ratings", lambda *a, **k: [])
    monkeypatch.setattr(scs, "get_product_image_url", image)
    monkeypatch.setattr(scs, "find_matching_drugs", _drugs)
    monkeypatch.setattr(svc, "_get_specs", specs)
    monkeypatch.setattr(svc, "_get_price", price)
    monkeypatch.setattr(svc, "_get_reviews", reviews)
    monkeypatch.setattr(svc, "_get_verified_rating", rating)
    monkeypatch.setattr(svc, "_smart_fallback_extract", _empty)
    monkeypatch.setattr(svc, "_track_serper_cost", lambda *a, **k: None)


def _parking_price(svc):
    """A price leaf that parks a converted 9.5 BHD price, then times out (spec F7)."""
    async def _price(brand, name, variant, region, search_query, nocache, category):
        full = scs._product_display_identity(brand, name, variant, search_query, False)[0]
        svc._parked_price[full] = {"amount": 9.5, "currency": "BHD",
                                   "source_method": "converted_usd", "retailer": "Example",
                                   "url": "https://example.com/p", "estimated": False}
        raise asyncio.TimeoutError()
    return _price


async def _fetch_direct(svc, monkeypatch, *, partial_slot, include_specs=True,
                        include_reviews=True):
    """F11: one direct _fetch_product_data call, Phase 2 not hung."""
    _install_real(svc, monkeypatch, specs=_specs_dict, price=_raise_t, reviews=_raise_rt,
                  image=_none, rating=_rating_ok)
    return await asyncio.wait_for(svc._fetch_product_data(
        dict(PARSED_E["products"][0]), "bahrain", include_specs, include_reviews,
        nocache=True, partial_slot=partial_slot), 20.0)


# ================================================================ F1 / F1b / F2
@pytest.mark.asyncio
async def test_F1_mid_gather_identities_only_reports_timeout(monkeypatch, caplog):
    """RED: both buffer slots hold identities only and nothing was recorded (the cap cut
    the gather): the handler must ship the base TIMEOUT body with one D5 WARNING
    (products=2, recorded=0, timed out=0) and keep the base 'no usable partial' WARNING.
    Base returns INSUFFICIENT_DATA with api_calls."""
    _set_flag(monkeypatch)
    svc = scs.StructuredComparisonService()
    _hang_impl(svc, monkeypatch, _seed_two_identities)
    body = await _run_rest(svc, caplog)
    _assert_timeout_body(body)
    assert _one_cap_groups(caplog) == (2, 0, 0)
    assert len(_no_usable_lines(caplog)) == 1


@pytest.mark.asyncio
async def test_F1b_real_entry_specs_and_price_cut_mid_gather(monkeypatch, caplog):
    """RED: real entry, specs + price hang, reviews / image return; the 1.0 s cap cuts the
    gather: TIMEOUT, D5 groups (2, 0, 0), identity-only buffer, and the record stays {} (a
    task cancelled by the cap records NOTHING, R2 / M29). Base: INSUFFICIENT_DATA."""
    _set_flag(monkeypatch)
    svc = scs.StructuredComparisonService()
    _install_real(svc, monkeypatch, specs=_hang, price=_hang, reviews=_reviews_ok, image=_none)
    body = await _run_rest(svc, caplog)
    _assert_timeout_body(body)
    assert _one_cap_groups(caplog) == (2, 0, 0)
    buf = svc._early_specs_buffer
    assert isinstance(buf, list) and len(buf) == 2
    for pd in buf:
        assert isinstance(pd, dict) and set(pd) == IDENTITY_KEYS, sorted(pd)
    assert _rec(svc) == {}, "S78-F8 R2: a cancelled race must record nothing: %r" % (_rec(svc),)


@pytest.mark.asyncio
async def test_F2_real_entry_all_four_races_time_out(monkeypatch, caplog):
    """RED: real entry, all four leaves raise TimeoutError, the cap fires in Phase 2: the
    record holds every race as 'timeout' for both slots, the body is TIMEOUT with D5 groups
    (2, 4, 4), and the 8 base [L2.6] lines are still logged. Base: INSUFFICIENT_DATA and no
    _phase1_race_outcomes attribute."""
    _set_flag(monkeypatch)
    svc = scs.StructuredComparisonService()
    _install_real(svc, monkeypatch)
    body = await _run_rest(svc, caplog)
    assert _rec(svc) == {0: dict(ALL4_TIMEOUT), 1: dict(ALL4_TIMEOUT)}, (
        "S78-F8 D3: missing / wrong Phase-1 race record: %r" % (_rec(svc),))
    _assert_timeout_body(body)
    assert _one_cap_groups(caplog) == (2, 4, 4)
    assert len(_race_timeout_lines(caplog)) == 8


# ================================================================ F3 (a) / (b) / (c), F3b
@pytest.mark.asyncio
async def test_F3a_pin_specs_completed_none_keeps_insufficient_data(monkeypatch, caplog):
    """PIN (F3 (a) verdict half, R4): product A's specs race COMPLETED with None, every
    other leaf times out: the base INSUFFICIENT_DATA body (six keys, the incomplete
    sentence) ships and no D5 line is logged. Passes at base (probe F3)."""
    _set_flag(monkeypatch)
    svc = scs.StructuredComparisonService()
    _install_real(svc, monkeypatch, specs=_per_name({NAME_A: _none}, _raise_t))
    body = await _run_rest(svc, caplog)
    _assert_insufficient_body(body)
    assert _cap_any(caplog) == []


@pytest.mark.asyncio
async def test_F3a_red_specs_completed_none_is_recorded_ok(monkeypatch, caplog):
    """RED (F3 (a) record half, R4): the completed specs race of product A is recorded as
    'ok' (slot 0), B's as 'timeout'. Base: no record (getattr reads None)."""
    _set_flag(monkeypatch)
    svc = scs.StructuredComparisonService()
    _install_real(svc, monkeypatch, specs=_per_name({NAME_A: _none}, _raise_t))
    await _run_rest(svc, caplog)
    rec = _rec(svc)
    assert isinstance(rec, dict), "S78-F8 D3: no _phase1_race_outcomes record: %r" % (rec,)
    assert rec.get(0, {}).get("specs") == "ok", rec
    assert rec.get(1, {}).get("specs") == "timeout", rec


@pytest.mark.asyncio
async def test_F3_b_pin_mid_gather_landed_specs_key_keeps_insufficient_data(monkeypatch, caplog):
    """PIN (F3 (b)): slot 0 recorded all-timeout, slot 1 unrecorded with a LANDED specs key
    (a completed race): fail closed to the base INSUFFICIENT_DATA body, no D5 line."""
    _set_flag(monkeypatch)
    svc = scs.StructuredComparisonService()

    def _seed(s):
        s._early_specs_buffer = [IDENT("A"), dict(IDENT("B"), specs=None)]
        s._phase1_race_outcomes = {0: {"specs": "timeout", "price": "timeout"}}
    _hang_impl(svc, monkeypatch, _seed)
    body = await _run_rest(svc, caplog)
    _assert_insufficient_body(body)
    assert _cap_any(caplog) == []


@pytest.mark.asyncio
async def test_F3_c_pin_price_completed_none_keeps_insufficient_data(monkeypatch, caplog):
    """PIN (F3 (c)): specs hang, the price race COMPLETES with None (the price callback
    lands the key): the base INSUFFICIENT_DATA body, no D5 line (probe Q2 price-none)."""
    _set_flag(monkeypatch)
    svc = scs.StructuredComparisonService()
    _install_real(svc, monkeypatch, specs=_hang, price=_none)
    body = await _run_rest(svc, caplog)
    _assert_insufficient_body(body)
    assert _cap_any(caplog) == []


@pytest.mark.asyncio
async def test_F3b_capture3_reviews_landed_still_reports_timeout(monkeypatch, caplog):
    """RED (capture 3): every leaf times out except reviews, which returns a value: reviews
    never count, so TIMEOUT with D5 groups (2, 4, 4) and reviews recorded 'ok' on both
    slots. Base: INSUFFICIENT_DATA (probe F3b)."""
    _set_flag(monkeypatch)
    svc = scs.StructuredComparisonService()
    _install_real(svc, monkeypatch, reviews=_reviews_ok)
    body = await _run_rest(svc, caplog)
    _assert_timeout_body(body)
    rec = _rec(svc)
    assert isinstance(rec, dict), rec
    assert rec.get(0, {}).get("reviews") == "ok" and rec.get(1, {}).get("reviews") == "ok", rec
    assert _one_cap_groups(caplog) == (2, 4, 4)


# ================================================================ F4a / F4b / F4c
@pytest.mark.asyncio
async def test_F4a_flag_off_never_reads_the_record(monkeypatch, caplog):
    """PIN: flag unset, the F1 seed plus a read-refusing record: the base INSUFFICIENT_DATA
    body ships byte-for-byte (six keys, the U+2014 sentence, api_calls), no D5 line, and the
    record was never read. Passes at base (nothing reads the attribute)."""
    _NoReadDict.READS = []
    svc = scs.StructuredComparisonService()

    def _seed(s):
        _seed_two_identities(s)
        s._phase1_race_outcomes = _NoReadDict()
    _hang_impl(svc, monkeypatch, _seed)
    body = await _run_rest(svc, caplog)
    _assert_insufficient_body(body)
    assert _cap_any(caplog) == []
    assert _NoReadDict.READS == []


@pytest.mark.asyncio
async def test_F4b_flag_off_record_block_writes_nothing(monkeypatch, caplog):
    """PIN: flag unset, the F2 setup through the REAL _fetch_product_data: INSUFFICIENT_DATA
    and the record stays empty (no callback, no post-loop write OFF)."""
    svc = scs.StructuredComparisonService()
    _install_real(svc, monkeypatch)
    body = await _run_rest(svc, caplog)
    _assert_insufficient_body(body)
    assert getattr(svc, "_phase1_race_outcomes", {}) == {}


def test_F4c_flag_off_predicate_reads_no_state(monkeypatch):
    """RED: flag unset, raising CLASS properties for _early_specs_buffer and
    _phase1_race_outcomes: _cap_all_data_races_timed_out() returns False without touching
    either (the flag is its first statement). Base: the method is missing."""
    svc = scs.StructuredComparisonService()
    meth = getattr(svc, "_cap_all_data_races_timed_out", None)
    assert callable(meth), "S78-F8 D4: StructuredComparisonService._cap_all_data_races_timed_out is missing"
    reads = []
    for name in ("_early_specs_buffer", "_phase1_race_outcomes"):
        monkeypatch.setattr(scs.StructuredComparisonService, name,
                            _boom_property(name, reads), raising=False)
    assert meth() is False
    assert reads == []


# ================================================================ F5 (the flag reader table)
@pytest.mark.asyncio
@pytest.mark.parametrize("value", FLAG_ON_VALUES)
async def test_F5_on_truthy_values_flip_to_timeout(monkeypatch, caplog, value):
    """RED (TG1 flag-reader table): every house-truthy spelling (strip + lower, the
    true/1/yes/on set) turns the F1 seed into TIMEOUT with one D5 line. Base:
    INSUFFICIENT_DATA."""
    _set_flag(monkeypatch, value)
    svc = scs.StructuredComparisonService()
    _hang_impl(svc, monkeypatch, _seed_two_identities)
    body = await _run_rest(svc, caplog)
    _assert_timeout_body(body)
    assert _one_cap_groups(caplog) == (2, 0, 0)


@pytest.mark.asyncio
@pytest.mark.parametrize("value", FLAG_OFF_VALUES)
async def test_F5_off_falsy_values_keep_base_and_read_nothing(monkeypatch, caplog, value):
    """PIN (TG1 flag-reader table): unset / empty / false / 0 / no / off / garbage / 'tru e'
    keep the base INSUFFICIENT_DATA body, log no D5 line and never read the record."""
    _set_flag(monkeypatch, value)
    _NoReadDict.READS = []
    svc = scs.StructuredComparisonService()

    def _seed(s):
        _seed_two_identities(s)
        s._phase1_race_outcomes = _NoReadDict()
    _hang_impl(svc, monkeypatch, _seed)
    body = await _run_rest(svc, caplog)
    _assert_insufficient_body(body)
    assert _cap_any(caplog) == []
    assert _NoReadDict.READS == []


# ================================================================ F6
@pytest.mark.asyncio
async def test_F6_pin_specs_raised_keeps_insufficient_data(monkeypatch, caplog):
    """PIN (F6 verdict half, R4 / D7): specs RAISES RuntimeError, every other leaf times
    out: an errored data race keeps the base INSUFFICIENT_DATA body, the two base ERROR
    'Error fetching specs: RuntimeError' lines are logged, no D5 line (probe F6)."""
    _set_flag(monkeypatch)
    svc = scs.StructuredComparisonService()
    _install_real(svc, monkeypatch, specs=_raise_rt)
    body = await _run_rest(svc, caplog)
    _assert_insufficient_body(body)
    errs = [r for r in _records(caplog) if r.levelno == logging.ERROR
            and r.getMessage() == "Error fetching specs: RuntimeError"]
    assert len(errs) == 2
    assert _cap_any(caplog) == []


@pytest.mark.asyncio
async def test_F6_red_specs_raised_is_recorded_error(monkeypatch, caplog):
    """RED (F6 record half, R4): the raised specs race is recorded 'error', the price race
    'timeout', on both slots. Base: no record."""
    _set_flag(monkeypatch)
    svc = scs.StructuredComparisonService()
    _install_real(svc, monkeypatch, specs=_raise_rt)
    await _run_rest(svc, caplog)
    rec = _rec(svc)
    assert isinstance(rec, dict), "S78-F8 D3: no _phase1_race_outcomes record: %r" % (rec,)
    for slot in (0, 1):
        assert rec.get(slot, {}).get("specs") == "error", rec
        assert rec.get(slot, {}).get("price") == "timeout", rec


# ================================================================ F7
@pytest.mark.asyncio
@pytest.mark.parametrize("flag", [None, "true"], ids=["off", "on"])
async def test_F7_pin_parked_price_ships_partial(monkeypatch, caplog, flag):
    """PIN (F7 verdict half, both flag states): the price leaf parks a 9.5 BHD price then
    times out; _price_fallback_on_miss returns it, so the compare is a PARTIAL
    (success True, metadata.partial True) and the predicate is never consulted: no D5
    line (probe F7)."""
    _set_flag(monkeypatch, flag)
    svc = scs.StructuredComparisonService()
    _install_real(svc, monkeypatch, price=_parking_price(svc))
    body = await _run_rest(svc, caplog)
    assert body.get("success") is True, body.get("code")
    assert (body.get("metadata") or {}).get("partial") is True
    assert _cap_any(caplog) == []


@pytest.mark.asyncio
async def test_F7_red_parked_price_race_is_recorded_timeout(monkeypatch, caplog):
    """RED (F7 record half, flag ON): the price race itself timed out (the parked price is a
    fallback), so the record says price 'timeout' on both slots. Base: no record."""
    _set_flag(monkeypatch)
    svc = scs.StructuredComparisonService()
    _install_real(svc, monkeypatch, price=_parking_price(svc))
    await _run_rest(svc, caplog)
    rec = _rec(svc)
    assert isinstance(rec, dict), "S78-F8 D3: no _phase1_race_outcomes record: %r" % (rec,)
    assert rec.get(0, {}).get("price") == "timeout", rec
    assert rec.get(1, {}).get("price") == "timeout", rec


# ================================================================ F8a / F8b (the entry resets)
def _install_identity_pipeline(svc, monkeypatch, *, cap, slow=False):
    """The FY25 faked pipeline (tests.test_s75_fanout_identity._install) on monkeypatch."""
    monkeypatch.setattr(scs, "STREAM_HARD_CAP_SECONDS", cap)
    _install(monkeypatch, svc, _new_state(), slow=slow)


def _hang_fetch_specs_none(svc):
    async def _fetch(product_info, region, include_specs, include_reviews, nocache=False,
                     partial_slot=None):
        if partial_slot is not None and isinstance(svc._early_specs_buffer, list):
            svc._early_specs_buffer[partial_slot] = dict(IDENT(product_info["name"]), specs=None)
        await asyncio.sleep(30)
    return _fetch


@pytest.mark.asyncio
async def test_F8a_rest_entry_drops_a_stale_all_timeout_record(monkeypatch, caplog):
    """PIN: the REAL _compare_from_text_impl with _fetch_product_data replaced by a hang
    that registers a dict carrying specs=None; a STALE all-timeout record is planted before
    the call: the REST entry reset drops it, the mid-gather arm sees the landed specs key and
    the base INSUFFICIENT_DATA body ships with no D5 line. Passes at base (never read)."""
    _set_flag(monkeypatch)
    svc = scs.StructuredComparisonService()
    _install_identity_pipeline(svc, monkeypatch, cap=0.5)
    svc._fetch_product_data = _hang_fetch_specs_none(svc)
    svc._phase1_race_outcomes = {0: {"specs": "timeout", "price": "timeout"},
                                 1: {"specs": "timeout", "price": "timeout"}}
    caplog.set_level(logging.INFO, logger=SCS_LOGGER)
    body = await asyncio.wait_for(svc.compare_from_text(QUERY, region="bahrain", nocache=True), 30)
    _assert_insufficient_body(body)
    assert _cap_any(caplog) == []


@pytest.mark.asyncio
async def test_F8b_rest_entry_resets_the_record(monkeypatch, caplog):
    """RED: a stale record planted before a REST compare is reset to {} by the REST entry.
    Base: nothing resets it (the stale seed survives)."""
    _set_flag(monkeypatch)
    svc = scs.StructuredComparisonService()
    _install_identity_pipeline(svc, monkeypatch, cap=0.5)
    svc._fetch_product_data = _hang_fetch_specs_none(svc)
    svc._phase1_race_outcomes = {9: {"price": "timeout"}}
    caplog.set_level(logging.INFO, logger=SCS_LOGGER)
    await asyncio.wait_for(svc.compare_from_text(QUERY, region="bahrain", nocache=True), 30)
    assert _rec(svc) == {}, "S78-F8: the REST entry did not reset the record: %r" % (_rec(svc),)


@pytest.mark.asyncio
async def test_F8b_stream_entry_resets_the_record(monkeypatch):
    """RED: a stale record planted before a streaming compare (driven to its partial by the
    FY25 slow fetch) is reset to {} by the stream entry. Base: the stale seed survives."""
    _set_flag(monkeypatch)
    svc = scs.StructuredComparisonService()
    _install_identity_pipeline(svc, monkeypatch, cap=0.5, slow=True)
    svc._phase1_race_outcomes = {9: {"price": "timeout"}}
    events = []

    async def _drain():
        async for event in svc.compare_from_text_streaming(QUERY, region="bahrain", nocache=True):
            events.append(event)
    await asyncio.wait_for(_drain(), 30)
    assert events, "the stream yielded nothing"
    assert _rec(svc) == {}, "S78-F8: the stream entry did not reset the record: %r" % (_rec(svc),)


# ================================================================ F9
@pytest.mark.asyncio
async def test_F9_post_gather_stash_without_buffer_keeps_insufficient_data(monkeypatch, caplog):
    """PIN: the test_compare_timeout_graceful 144-165 seed (post-gather stash of specs None /
    price None dicts, early buffer never set, no record): the predicate fails closed (buffer
    not a list) and the base INSUFFICIENT_DATA body ships, no D5 line."""
    _set_flag(monkeypatch)
    svc = scs.StructuredComparisonService()

    def _seed(s):
        s._partial_product_data = [dict(IDENT("A"), specs=None, price=None),
                                   dict(IDENT("B"), specs=None, price=None)]
    _hang_impl(svc, monkeypatch, _seed)
    body = await _run_rest(svc, caplog)
    _assert_insufficient_body(body)
    assert _cap_any(caplog) == []


# ================================================================ F10 (the D3 classifier)
F10_ROWS = [
    ("asyncio_timeout", lambda: asyncio.TimeoutError(), "timeout"),
    ("builtin_timeout", lambda: TimeoutError(), "timeout"),
    ("runtime_error", lambda: RuntimeError("x"), "error"),
    ("cancelled", lambda: asyncio.CancelledError(), "error"),
    ("keyboard_interrupt", lambda: KeyboardInterrupt(), "error"),
    ("none", lambda: None, "ok"),
    ("empty_dict", lambda: {}, "ok"),
    ("price_dict", lambda: {"amount": 1.0}, "ok"),
    ("zero", lambda: 0, "ok"),
    ("false", lambda: False, "ok"),
    ("string", lambda: "x", "ok"),
]


@pytest.mark.parametrize("make,want", [(m, w) for _i, m, w in F10_ROWS],
                         ids=[i for i, _m, _w in F10_ROWS])
def test_F10_phase1_race_outcome_table(make, want):
    """RED (D3 classifier table): asyncio.TimeoutError / TimeoutError -> 'timeout'; any
    other BaseException (CancelledError, KeyboardInterrupt included) -> 'error'; any value
    (None, {}, a dict, 0, False, a string) -> 'ok'. Base: scs._phase1_race_outcome is
    missing."""
    fn = getattr(scs, "_phase1_race_outcome", None)
    assert callable(fn), "S78-F8 D3: scs._phase1_race_outcome is missing"
    assert fn(make()) == want


# ================================================================ F11 (the record block)
F11_ROWS = [
    ("slot0", {"partial_slot": 0},
     {0: {"specs": "ok", "price": "timeout", "reviews": "error", "image_url": "ok"}},
     ["specs", "price", "reviews", "image_url"]),
    ("slot1", {"partial_slot": 1},
     {1: {"specs": "ok", "price": "timeout", "reviews": "error", "image_url": "ok"}},
     ["specs", "price", "reviews", "image_url"]),
    ("slot_none", {"partial_slot": None}, {}, None),
    ("no_reviews", {"partial_slot": 0, "include_reviews": False},
     {0: {"specs": "ok", "price": "timeout", "image_url": "ok"}},
     ["specs", "price", "image_url"]),
    ("no_specs", {"partial_slot": 0, "include_specs": False},
     {0: {"price": "timeout", "reviews": "error", "image_url": "ok"}},
     ["price", "reviews", "image_url"]),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("kwargs,want,order", [(k, w, o) for _i, k, w, o in F11_ROWS],
                         ids=[i for i, _k, _w, _o in F11_ROWS])
async def test_F11_record_block_after_the_loop(monkeypatch, kwargs, want, order):
    """RED: flag ON, one direct _fetch_product_data (specs returns a dict, price times out,
    reviews raises RuntimeError, image returns None; a fresh instance per row): the record
    holds every race that ran, keyed by the slot, in phase1_keys order; partial_slot None
    records nothing. Base: no record (getattr reads None)."""
    _set_flag(monkeypatch)
    svc = scs.StructuredComparisonService()
    await _fetch_direct(svc, monkeypatch, **kwargs)
    rec = _rec(svc)
    assert isinstance(rec, dict), "S78-F8 D3: no _phase1_race_outcomes record: %r" % (rec,)
    assert rec == want
    if order is not None:
        slot = kwargs["partial_slot"]
        assert list(rec[slot]) == order


# ================================================================ F12 (include_specs False)
@pytest.mark.asyncio
@pytest.mark.parametrize("include_reviews", [True, False], ids=["a_reviews_on", "b_reviews_off"])
async def test_F12_include_specs_false_price_alone_decides(monkeypatch, caplog, include_reviews):
    """RED: include_specs=False (and, in (b), include_reviews=False), every leaf times out:
    the price race alone decides -> TIMEOUT, the records carry no specs key, D5 groups
    (2, 2, 2). Base: INSUFFICIENT_DATA (probe F12)."""
    _set_flag(monkeypatch)
    svc = scs.StructuredComparisonService()
    _install_real(svc, monkeypatch)
    body = await _run_rest(svc, caplog, include_specs=False, include_reviews=include_reviews)
    _assert_timeout_body(body)
    rec = _rec(svc)
    assert isinstance(rec, dict) and set(rec) == {0, 1}, rec
    for slot in (0, 1):
        assert "specs" not in rec[slot] and rec[slot].get("price") == "timeout", rec
    assert _one_cap_groups(caplog) == (2, 2, 2)


# ================================================================ F13 (FY25 with the flag ON)
def test_F13_fy25_digests_unmoved_with_the_flag_on(monkeypatch):
    """PIN: with ENABLE_ALL_TIMEOUT_CAP_AS_TIMEOUT=true the nine FY25 scenarios (REST / stream
    full, partial at gather, parse-fail, private marks; _scenario pops only its own UNIT_ENV,
    so the flag survives) produce the digests recorded in the FY25 fixture: flag ON moves no
    byte off the all-timeout branch."""
    _set_flag(monkeypatch)
    want = json.loads(FIXTURE.read_text(encoding="ascii"))["digests"]
    got = asyncio.run(_all_digests())
    moved = sorted(name for name in want if got.get(name) != want[name])
    assert moved == [], "S78-F8: FY25 scenarios moved with the flag ON: %r" % (moved,)


# ================================================================ F15 (the route end to end)
@pytest.mark.parametrize("flag,status,code", [("true", 503, "TIMEOUT"),
                                               (None, 400, "INSUFFICIENT_DATA")],
                         ids=["on", "off"])
def test_F15_route_end_to_end(monkeypatch, flag, status, code):
    """on = RED, off = PIN: GET and POST /api/v1/text/compare over a REAL service carrying the
    F1 hang (cap 0.2): flag ON maps the TIMEOUT body to HTTP 503 code TIMEOUT (the existing
    mapping); flag OFF keeps HTTP 400 INSUFFICIENT_DATA. Base: 400 in both states."""
    from fastapi.testclient import TestClient
    from app.main import app
    from app.middleware.rate_limiter import limiter
    try:
        limiter.reset()
    except Exception:  # noqa: BLE001
        pass
    _set_flag(monkeypatch, flag)
    svc = scs.StructuredComparisonService()
    _hang_impl(svc, monkeypatch, _seed_two_identities)
    client = TestClient(app)
    with patch("app.api.text_routes.get_comparison_service", lambda: svc):
        r_get = client.get("/api/v1/text/compare", params={"q": "A One vs B Two", "nocache": "true"})
        r_post = client.post("/api/v1/text/compare", json={"query": "A One vs B Two"})
    for resp in (r_get, r_post):
        assert resp.status_code == status, (resp.status_code, resp.text[:200])
        assert resp.json().get("code") == code


# ================================================================ F18 (the D4 decision table)
def _pd_price():
    return {"amount": 9.5, "currency": "BHD", "source_method": "converted_usd"}


ALL_T = {"specs": "timeout", "price": "timeout"}
F18_ROWS = [
    ("r01_buffer_none", lambda: None, {}, False),
    ("r02_buffer_empty_slots", lambda: [None, None], {0: dict(ALL_T), 1: dict(ALL_T)}, False),
    ("r03_identities_no_record", lambda: [IDENT("A"), IDENT("B")], {}, True),
    ("r04_landed_specs_key", lambda: [dict(IDENT("A"), specs=None), IDENT("B")], {}, False),
    ("r05_landed_price_key", lambda: [dict(IDENT("A"), price=None), IDENT("B")], {}, False),
    ("r06_specs_error", lambda: [IDENT("A"), IDENT("B")],
     {0: dict(ALL_T), 1: {"specs": "error", "price": "timeout"}}, False),
    ("r07_price_ok", lambda: [IDENT("A"), IDENT("B")],
     {0: dict(ALL_T), 1: {"specs": "timeout", "price": "ok"}}, False),
    ("r08_reviews_image_ok_ignored", lambda: [IDENT("A"), IDENT("B")],
     {0: {"specs": "timeout", "price": "timeout", "reviews": "ok", "image_url": "ok"},
      1: {"specs": "timeout", "price": "timeout", "reviews": "ok", "image_url": "ok"}}, True),
    ("r09_no_specs_race", lambda: [IDENT("A"), IDENT("B")],
     {0: {"price": "timeout"}, 1: {"price": "timeout"}}, True),
    ("r10_price_race_cut", lambda: [IDENT("A"), IDENT("B")],
     {0: {"specs": "timeout"}, 1: {"specs": "timeout"}}, True),
    ("r11_slot_index_not_compacted", lambda: [None, IDENT("B")],
     {0: {"price": "ok"}, 1: dict(ALL_T)}, True),
    ("r13_mixed_arms", lambda: [IDENT("A"), IDENT("B")], {0: dict(ALL4_TIMEOUT)}, True),
    ("r14_outcomes_not_a_dict", lambda: [IDENT("A"), IDENT("B")], None, True),
    ("r15_usable_price_present", lambda: [dict(IDENT("A"), price=_pd_price()), IDENT("B")],
     {0: dict(ALL4_TIMEOUT), 1: dict(ALL4_TIMEOUT)}, False),
    ("r16_eager_specs_error", lambda: [IDENT("A"), IDENT("B")], {0: {"specs": "error"}}, False),
    ("r17_eager_specs_ok", lambda: [IDENT("A"), IDENT("B")], {0: {"specs": "ok"}}, False),
    ("r18_price_timeout_only", lambda: [IDENT("A"), IDENT("B")],
     {0: {"price": "timeout"}, 1: {"price": "timeout"}}, True),
    ("r19_eager_price_error", lambda: [IDENT("A"), IDENT("B")], {0: {"price": "error"}}, False),
]


@pytest.mark.parametrize("make_buffer,outcomes,want", [(b, o, w) for _i, b, o, w in F18_ROWS],
                         ids=[i for i, _b, _o, _w in F18_ROWS])
def test_F18_predicate_decision_table(monkeypatch, make_buffer, outcomes, want):
    """RED (D4 decision table, as amended by R2 / R3): direct
    _cap_all_data_races_timed_out() on seeded state, flag ON. Base: the method is missing."""
    _set_flag(monkeypatch)
    svc = scs.StructuredComparisonService()
    meth = getattr(svc, "_cap_all_data_races_timed_out", None)
    assert callable(meth), "S78-F8 D4: StructuredComparisonService._cap_all_data_races_timed_out is missing"
    svc._early_specs_buffer = make_buffer()
    svc._phase1_race_outcomes = copy.deepcopy(outcomes)
    assert meth() is want


def test_F18_r12_new_built_instance_without_the_record_attribute(monkeypatch):
    """RED (F18 row 12): a __new__-built instance carrying only _early_specs_buffer (no
    _phase1_race_outcomes attribute, the Q6 test idiom) -> True, no AttributeError (every
    new read is a getattr with a default). Base: the method is missing."""
    _set_flag(monkeypatch)
    svc = scs.StructuredComparisonService.__new__(scs.StructuredComparisonService)
    meth = getattr(svc, "_cap_all_data_races_timed_out", None)
    assert callable(meth), "S78-F8 D4: StructuredComparisonService._cap_all_data_races_timed_out is missing"
    svc._early_specs_buffer = [IDENT("A"), IDENT("B")]
    assert "_phase1_race_outcomes" not in vars(svc)
    assert meth() is True


# ================================================================ F19 family (eager record, R2)
@pytest.mark.asyncio
async def test_F19_pin_specs_raised_price_cut_keeps_insufficient_data(monkeypatch, caplog):
    """PIN (F19 verdict half): specs RAISES RuntimeError, price hangs, reviews / image return,
    the 1.0 s cap cuts the gather: a raised data race keeps INSUFFICIENT_DATA (D7 in the
    mid-gather arm, R2), no D5 line. Passes at base (review probe R1)."""
    _set_flag(monkeypatch)
    svc = scs.StructuredComparisonService()
    _install_real(svc, monkeypatch, specs=_raise_rt, price=_hang, reviews=_reviews_ok,
                  image=_none)
    body = await _run_rest(svc, caplog)
    _assert_insufficient_body(body)
    assert _cap_any(caplog) == []


@pytest.mark.asyncio
async def test_F19_red_specs_raised_is_recorded_eagerly(monkeypatch, caplog):
    """RED (F19 record half): the raised specs race is recorded 'error' by the eager
    done-callback; the price race was cancelled by the cap and is NOT recorded. Base: no
    record."""
    _set_flag(monkeypatch)
    svc = scs.StructuredComparisonService()
    _install_real(svc, monkeypatch, specs=_raise_rt, price=_hang, reviews=_reviews_ok,
                  image=_none)
    await _run_rest(svc, caplog)
    rec = _rec(svc)
    assert isinstance(rec, dict), "S78-F8 R2: no eager _phase1_race_outcomes record: %r" % (rec,)
    for slot in (0, 1):
        assert rec.get(slot, {}).get("specs") == "error", rec
        assert "price" not in rec.get(slot, {}), rec


@pytest.mark.asyncio
async def test_F19b_pin_price_raised_specs_cut_keeps_insufficient_data(monkeypatch, caplog):
    """PIN (F19b verdict half): price RAISES RuntimeError, specs hangs, the cap cuts the
    gather: INSUFFICIENT_DATA, no D5 line. Passes at base (review probe R1b)."""
    _set_flag(monkeypatch)
    svc = scs.StructuredComparisonService()
    _install_real(svc, monkeypatch, specs=_hang, price=_raise_rt, reviews=_reviews_ok,
                  image=_none)
    body = await _run_rest(svc, caplog)
    _assert_insufficient_body(body)
    assert _cap_any(caplog) == []


@pytest.mark.asyncio
async def test_F19b_red_price_raised_is_recorded_eagerly(monkeypatch, caplog):
    """RED (F19b record half): the raised price race is recorded 'error'; the cancelled
    specs race is not recorded. Base: no record."""
    _set_flag(monkeypatch)
    svc = scs.StructuredComparisonService()
    _install_real(svc, monkeypatch, specs=_hang, price=_raise_rt, reviews=_reviews_ok,
                  image=_none)
    await _run_rest(svc, caplog)
    rec = _rec(svc)
    assert isinstance(rec, dict), "S78-F8 R2: no eager _phase1_race_outcomes record: %r" % (rec,)
    for slot in (0, 1):
        assert rec.get(slot, {}).get("price") == "error", rec
        assert "specs" not in rec.get(slot, {}), rec


@pytest.mark.asyncio
@pytest.mark.parametrize("flag", [None, "true"], ids=["off", "on"])
async def test_F19c_pin_specs_landed_price_cut_ships_partial(monkeypatch, caplog, flag):
    """PIN (F19c verdict half, both flag states): specs complete with a dict, price hangs,
    the cap cuts the gather: usable data -> the PARTIAL path (success True, metadata.partial
    True), no D5 line."""
    _set_flag(monkeypatch, flag)
    svc = scs.StructuredComparisonService()
    _install_real(svc, monkeypatch, specs=_specs_dict, price=_hang, reviews=_reviews_ok,
                  image=_none)
    body = await _run_rest(svc, caplog)
    assert body.get("success") is True, body.get("code")
    assert (body.get("metadata") or {}).get("partial") is True
    assert _cap_any(caplog) == []


@pytest.mark.asyncio
async def test_F19c_red_specs_landed_is_recorded_ok(monkeypatch, caplog):
    """RED (F19c record half, flag ON): the completed specs race is recorded 'ok' by the eager
    callback before the cap cut the gather. Base: no record."""
    _set_flag(monkeypatch)
    svc = scs.StructuredComparisonService()
    _install_real(svc, monkeypatch, specs=_specs_dict, price=_hang, reviews=_reviews_ok,
                  image=_none)
    await _run_rest(svc, caplog)
    rec = _rec(svc)
    assert isinstance(rec, dict), "S78-F8 R2: no eager _phase1_race_outcomes record: %r" % (rec,)
    assert rec.get(0, {}).get("specs") == "ok", rec
    assert rec.get(1, {}).get("specs") == "ok", rec


# ================================================================ F20 (7.2 in, R3)
@pytest.mark.asyncio
@pytest.mark.parametrize("flag", [None, "true"], ids=["off", "on"])
async def test_F20_partial_build_failure_with_a_parked_price_keeps_insufficient_data(
        monkeypatch, caplog, flag):
    """PIN (both flag states): the F7 parked-price shape with _build_partial_response
    raising: the handler falls through WITH usable data (a 9.5 BHD price), so the 7.2 check
    keeps INSUFFICIENT_DATA under the flag; no D5 line (review probe R2)."""
    _set_flag(monkeypatch, flag)
    svc = scs.StructuredComparisonService()
    _install_real(svc, monkeypatch, price=_parking_price(svc))

    def _boom(**_k):
        raise RuntimeError("s78f8-build")
    monkeypatch.setattr(svc, "_build_partial_response", _boom)
    body = await _run_rest(svc, caplog)
    assert body.get("code") == "INSUFFICIENT_DATA", body.get("code")
    assert _cap_any(caplog) == []
