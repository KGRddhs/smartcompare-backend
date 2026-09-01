"""M18 CD-interactions-02 — the region-currency guard must run BEFORE scoring.

ENABLE_REGION_CURRENCY_GUARD (M13-11, default OFF) pends a currency-mismatched
price only at the response chokepoint (response_builder.build_comparison_response),
which runs AFTER compute_scores has already picked a winner from the raw amount and
AFTER the SSE `prices` event has already streamed that amount to the client. So the
final payload shows `price: pending` next to a winner decided by the hidden
mismatched price (BHD 10 vs SAR 40 scores as 10 vs 40).

This file pins the pre-scoring half: a pure in-place pass
(price_service.apply_region_currency_guard) invoked by both orchestrator paths
immediately after reconcile_pair_fairness, so scoring, the verdict and the streamed
`prices` event all see the guarded price. Flag OFF stays byte-identical.

No network: the unit half is pure, the streaming half reuses the fully mocked
_mock_to_verdict harness from tests/test_m13_04_full_stream_deadline.py.
"""
import os
os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

import asyncio
import copy

import pytest

import app.services.structured_comparison_service as scs
from app.services.price_service import apply_region_currency_guard
from app.services.scoring_service import get_scoring_service

from tests.test_m13_04_full_stream_deadline import _mock_to_verdict


def _product(name, amount, cur):
    """Copied from tests/test_m13_region_currency_guard.py so the two guard halves
    exercise the same product shape."""
    return {
        "name": name, "full_name": name, "category": "electronics",
        "price": {
            "amount": amount, "currency": cur, "source_method": "local_bhd",
            "retailer": "noon", "url": "https://noon.com/p", "title": name,
            "in_stock": True,
        },
    }


def _event_type(ev):
    return ev[0] if isinstance(ev, tuple) and ev else None


async def _collect_until(gen, stop_type, timeout=15.0):
    """Drain the SSE generator until `stop_type` is seen (or the timeout), then
    close it. Keeps these tests off the hung-verdict tail entirely."""
    events = []

    async def _drain():
        async for ev in gen:
            events.append(ev)
            if _event_type(ev) == stop_type:
                return

    try:
        await asyncio.wait_for(_drain(), timeout=timeout)
    except asyncio.TimeoutError:
        events.append(("_collector_timeout", {}))
    finally:
        await gen.aclose()
    return events


def _showable_bhd_fetch(monkeypatch, service):
    """The shared _mock_to_verdict harness returns a bare
    ``{"amount": 10.0, "currency": "BHD", "estimated": False}``, which
    ``is_price_showable(..., enforce_correctness=True)`` already rejects — so the
    SSE `prices` projection pends it regardless of the region guard and the
    streamed amount is None even with the flag OFF. Re-patch the fetch with a price
    that PASSES the correctness gate, so the only thing that can pend it is the
    region-currency mismatch under test."""

    async def _fake_fetch(product, region, include_specs, include_reviews, nocache,
                          partial_slot=0, **kw):
        _name = f"{product.get('brand', 'X')} {product.get('name', 'Y')}".strip()
        return {
            "brand": product.get("brand", "X"),
            "name": product.get("name", "Y"),
            "full_name": _name,
            "specs": {"k": "v"},
            "price": {
                "amount": 10.0, "currency": "BHD", "estimated": False,
                "source_method": "local_bhd", "retailer": "noon",
                "url": "https://noon.com/p", "title": _name, "in_stock": True,
            },
            "best_price": 10.0,
            "retailer": "noon",
            "reviews": {"highlights": []},
            "fact_check": {"overall_confidence": "medium"},
            "image_url": None,
        }

    monkeypatch.setattr(service, "_fetch_product_data", _fake_fetch)


def _payload(events, ev_type):
    for ev in events:
        if _event_type(ev) == ev_type:
            return ev[1]
    return None


# ---------------------------------------------------------------- unit half


def test_flag_off_leaves_product_data_untouched(monkeypatch):
    monkeypatch.setenv("ENABLE_REGION_CURRENCY_GUARD", "false")
    pd = [_product("Alpha", 25.0, "BHD")]
    before = copy.deepcopy(pd)
    assert apply_region_currency_guard(pd, "saudi_arabia") is False
    assert pd == before


def test_flag_on_pends_mismatched_currency_in_place(monkeypatch):
    monkeypatch.setenv("ENABLE_REGION_CURRENCY_GUARD", "true")
    pd = [_product("Alpha", 25.0, "BHD")]
    # The chokepoint only nulls `retailer` when the key is PRESENT
    # (response_builder: `if "retailer" in pd_item`), and _product() carries the
    # retailer inside the price only — so seed a product-level one to exercise it.
    pd[0]["best_price"] = 25.0
    pd[0]["retailer"] = "noon"
    assert apply_region_currency_guard(pd, "saudi_arabia") is True
    assert pd[0]["price"]["amount"] is None
    assert pd[0]["price"]["currency"] == "SAR"
    assert pd[0]["price"]["unavailable"] is True
    assert pd[0]["price"]["reason"] == "pending_genuine"
    assert pd[0]["best_price"] is None
    assert pd[0]["retailer"] is None
    assert pd[0]["_region_guard_rejected"] == "region_currency_mismatch"


def test_flag_on_matching_currency_untouched(monkeypatch):
    monkeypatch.setenv("ENABLE_REGION_CURRENCY_GUARD", "true")
    pd = [_product("Beta", 250.0, "SAR")]
    assert apply_region_currency_guard(pd, "saudi_arabia") is False
    assert pd[0]["price"]["amount"] == 250.0
    assert "_region_guard_rejected" not in pd[0]


def test_flag_on_preserves_existing_pend_reason(monkeypatch):
    monkeypatch.setenv("ENABLE_REGION_CURRENCY_GUARD", "true")
    pd = [_product("Alpha", 25.0, "BHD")]
    pd[0]["price"] = {
        "amount": None, "currency": "BHD", "unavailable": True,
        "reason": "size_mismatch",
    }
    assert apply_region_currency_guard(pd, "saudi_arabia") is False
    assert pd[0]["price"]["reason"] == "size_mismatch"
    assert "_region_guard_rejected" not in pd[0]


@pytest.mark.parametrize("currency", [None, ""])
def test_flag_on_missing_currency_label_untouched(monkeypatch, currency):
    """Chokepoint parity (response_builder: `if _pcur and _pcur != _region_currency`)
    — an unlabelled currency is NOT a mismatch."""
    monkeypatch.setenv("ENABLE_REGION_CURRENCY_GUARD", "true")
    pd = [_product("Alpha", 25.0, currency)]
    assert apply_region_currency_guard(pd, "saudi_arabia") is False
    assert pd[0]["price"]["amount"] == 25.0
    assert "_region_guard_rejected" not in pd[0]


def test_unknown_region_defaults_to_bhd(monkeypatch):
    """get_region_currency's contract: falsy/unknown region -> BHD."""
    monkeypatch.setenv("ENABLE_REGION_CURRENCY_GUARD", "true")
    pd_bhd = [_product("Alpha", 25.0, "BHD")]
    assert apply_region_currency_guard(pd_bhd, "") is False
    assert pd_bhd[0]["price"]["amount"] == 25.0

    pd_usd = [_product("Alpha", 25.0, "USD")]
    assert apply_region_currency_guard(pd_usd, "") is True
    assert pd_usd[0]["price"]["amount"] is None
    assert pd_usd[0]["price"]["currency"] == "BHD"


def test_scores_take_missing_data_path_after_guard(monkeypatch):
    """The finding's own scenario, against the REAL scoring service: BHD 10 vs
    SAR 40 on a Saudi request. Raw, the BHD product wins the value dimension on a
    10-vs-40 numeric delta; guarded, its price is pending so value takes the
    neutral missing-data path and the winner flips."""
    monkeypatch.setenv("ENABLE_REGION_CURRENCY_GUARD", "true")
    pd = [_product("Alpha", 10.0, "BHD"), _product("Beta", 40.0, "SAR")]

    raw = get_scoring_service().compute_scores(copy.deepcopy(pd))
    raw_winner = raw["winner_index"]
    raw_value = raw["scores"]["product_0"]["breakdown"]["value_score"]

    assert apply_region_currency_guard(pd, "saudi_arabia") is True
    guarded = get_scoring_service().compute_scores(copy.deepcopy(pd))
    guarded_winner = guarded["winner_index"]
    guarded_value = guarded["scores"]["product_0"]["breakdown"]["value_score"]

    # Raw: the mismatched BHD amount buys product_0 the cheap-price value bonus.
    assert raw_value == 100.0, raw
    # Guarded: no amount -> the honest missing-data neutral, no cross-price delta.
    assert guarded_value == 50, guarded
    assert guarded_winner != raw_winner, (raw_winner, guarded_winner)


# ----------------------------------------------------------- streaming half


@pytest.mark.asyncio
async def test_streaming_prices_event_pends_mismatched_currency_when_flag_on(monkeypatch):
    """The harness's _fake_fetch returns BHD 10.0; region=saudi_arabia makes that a
    mismatch. Flag ON: the mid-stream `prices` event must already carry the pending
    shape, not the raw 10.0 that the final `complete` then retracts."""
    monkeypatch.setenv("ENABLE_REGION_CURRENCY_GUARD", "true")
    service = scs.get_comparison_service()
    _mock_to_verdict(monkeypatch, service)
    _showable_bhd_fetch(monkeypatch, service)

    gen = service.compare_from_text_streaming(query="A vs B", region="saudi_arabia")
    events = await _collect_until(gen, "prices")
    payload = _payload(events, "prices")

    assert payload is not None, [_event_type(e) for e in events]
    assert payload["product_0"]["price"]["amount"] is None, payload
    assert payload["product_0"]["price"]["unavailable"] is True, payload


@pytest.mark.asyncio
async def test_streaming_prices_event_unchanged_when_flag_off(monkeypatch):
    monkeypatch.delenv("ENABLE_REGION_CURRENCY_GUARD", raising=False)
    service = scs.get_comparison_service()
    _mock_to_verdict(monkeypatch, service)
    _showable_bhd_fetch(monkeypatch, service)

    gen = service.compare_from_text_streaming(query="A vs B", region="saudi_arabia")
    events = await _collect_until(gen, "prices")
    payload = _payload(events, "prices")

    assert payload is not None, [_event_type(e) for e in events]
    assert payload["product_0"]["price"]["amount"] == 10.0, payload


@pytest.mark.asyncio
@pytest.mark.parametrize("flag_on,expected", [(True, None), (False, 10.0)])
async def test_streaming_compute_scores_receives_guarded_product_data(
    monkeypatch, flag_on, expected
):
    """The winner/verdict half: compute_scores must be handed the GUARDED
    product_data, not the raw mismatched amount."""
    if flag_on:
        monkeypatch.setenv("ENABLE_REGION_CURRENCY_GUARD", "true")
    else:
        monkeypatch.delenv("ENABLE_REGION_CURRENCY_GUARD", raising=False)
    service = scs.get_comparison_service()
    _mock_to_verdict(monkeypatch, service)
    _showable_bhd_fetch(monkeypatch, service)
    scoring = scs.get_scoring_service()

    gen = service.compare_from_text_streaming(query="A vs B", region="saudi_arabia")
    events = await _collect_until(gen, "scores")

    assert scoring.compute_scores.call_args is not None, [
        _event_type(e) for e in events
    ]
    scored_pd = scoring.compute_scores.call_args[0][0]
    assert scored_pd[0]["price"]["amount"] == expected, scored_pd[0]["price"]


# ---------------------------------------------------------------------------
# Ported from the second session's duplicate #113 implementation. That commit was
# dropped in favour of main's (the two are functionally identical — same helper
# name, same product-level `_region_guard_rejected` stash, same ordering
# constraints), but these two cases had no counterpart in main's file.
# ---------------------------------------------------------------------------

def test_flag_on_non_dict_price_untouched(monkeypatch):
    """A non-dict price is the chokepoint's SIB-5 branch, not the guard's. The
    pre-scoring pass must skip it rather than crash or coerce it, so the two
    halves keep mirroring each other exactly."""
    monkeypatch.setenv("ENABLE_REGION_CURRENCY_GUARD", "true")
    pd = [{"name": "Alpha", "price": None}]
    assert apply_region_currency_guard(pd, "saudi_arabia") is False
    assert pd[0]["price"] is None


def test_metadata_guard_rejected_survives_an_upstream_pend(monkeypatch):
    """The diagnostic must survive the hand-off between the two halves.

    `response_builder`'s price-pending loop has an `unavailable is True`
    early-continue, which returns BEFORE the diag is appended — so once the
    PRE-scoring pass has already pended the price, `region_currency_mismatch`
    would silently vanish from `metadata.guard_rejected` unless the builder
    harvests the product-level `_region_guard_rejected` key first. Without this
    pin the guard still works but becomes unobservable, which is precisely what
    makes a canary read clean."""
    from app.services.response_builder import build_comparison_response

    monkeypatch.setenv("ENABLE_REGION_CURRENCY_GUARD", "true")
    pd = [{
        "name": "Alpha", "full_name": "Alpha", "category": "electronics",
        "price": {"amount": None, "currency": "SAR", "unavailable": True,
                  "reason": "pending_genuine"},
        "best_price": None, "retailer": None,
        "_region_guard_rejected": "region_currency_mismatch",
    }]
    resp = build_comparison_response(product_data=pd, region="saudi_arabia")
    assert {"product_index": 0, "reason": "region_currency_mismatch"} in \
        resp["metadata"]["guard_rejected"]
