"""M20 #113 (M18 CD-interactions-02) — the region-currency guard must run BEFORE
scoring, so the streamed price and the verdict use the guarded price.

`ENABLE_REGION_CURRENCY_GUARD` (M13-11, default OFF) exists to stop a BHD price
being served to a Saudi user as if it were SAR — "the 10x-wrong product wins".
As shipped it pends only in the FINAL projection, after `compute_scores` already
decided `winner_index` from the mismatched amounts and after the SSE `prices`
event already streamed the raw foreign amount. A final-payload canary therefore
reads clean while the winner is still decided by the hidden price. This is a
HARD PRECONDITION on ever flipping that flag.

The guard flag stays DEFAULT OFF. Nothing here activates it; flag OFF must leave
`product_data` untouched on every path.
"""
import copy

import pytest

import app.services.structured_comparison_service as scs
from app.services.response_builder import build_comparison_response


def apply_region_currency_guard(product_data, region):
    """Lazy accessor so the module still IMPORTS at 17cb981 (where the helper
    does not exist yet) and each unit case can be observed RED on its own,
    rather than the whole file erroring out at collection."""
    from app.services.price_service import apply_region_currency_guard as _fn
    return _fn(product_data, region)


def _product(name, amount, cur):
    return {
        "name": name, "full_name": name, "category": "electronics",
        "price": {
            "amount": amount, "currency": cur, "source_method": "local_bhd",
            "retailer": "noon", "url": "https://noon.com/p", "title": name,
            "in_stock": True,
        },
        "best_price": amount,
        "retailer": "noon",
    }


# ---------------------------------------------------------------------------
# Unit half — the in-place pre-scoring pass
# ---------------------------------------------------------------------------

def test_flag_off_leaves_product_data_untouched(monkeypatch):
    monkeypatch.setenv("ENABLE_REGION_CURRENCY_GUARD", "false")
    pd = [_product("Alpha", 25.0, "BHD")]
    before = copy.deepcopy(pd)
    assert apply_region_currency_guard(pd, "saudi_arabia") is False
    assert pd == before


def test_flag_on_pends_mismatched_currency_in_place(monkeypatch):
    monkeypatch.setenv("ENABLE_REGION_CURRENCY_GUARD", "true")
    pd = [_product("Alpha", 25.0, "BHD")]
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
    pd = [_product("Alpha", None, "BHD")]
    pd[0]["price"] = {"amount": None, "currency": "BHD", "unavailable": True,
                      "reason": "size_mismatch"}
    assert apply_region_currency_guard(pd, "saudi_arabia") is False
    assert pd[0]["price"]["reason"] == "size_mismatch"
    assert "_region_guard_rejected" not in pd[0]


@pytest.mark.parametrize("currency", [None, ""])
def test_flag_on_missing_currency_label_untouched(monkeypatch, currency):
    """Chokepoint parity: an unlabelled price is not a MISmatch."""
    monkeypatch.setenv("ENABLE_REGION_CURRENCY_GUARD", "true")
    pd = [_product("Alpha", 25.0, currency)]
    assert apply_region_currency_guard(pd, "saudi_arabia") is False
    assert pd[0]["price"]["amount"] == 25.0


def test_unknown_region_defaults_to_bhd(monkeypatch):
    monkeypatch.setenv("ENABLE_REGION_CURRENCY_GUARD", "true")
    ok = [_product("Alpha", 25.0, "BHD")]
    assert apply_region_currency_guard(ok, "") is False
    assert ok[0]["price"]["amount"] == 25.0

    bad = [_product("Gamma", 30.0, "USD")]
    assert apply_region_currency_guard(bad, "") is True
    assert bad[0]["price"]["currency"] == "BHD"
    assert bad[0]["price"]["amount"] is None


def test_flag_on_non_dict_price_untouched(monkeypatch):
    monkeypatch.setenv("ENABLE_REGION_CURRENCY_GUARD", "true")
    pd = [{"name": "Alpha", "price": None}]
    assert apply_region_currency_guard(pd, "saudi_arabia") is False
    assert pd[0]["price"] is None


def test_scores_take_missing_data_path_after_guard(monkeypatch):
    """The finding's own scenario, through the REAL scoring service: BHD 10 vs
    SAR 40 on a Saudi request scores as 10 vs 40 and the wrong product wins.
    RED at 17cb981 — no pre-scoring pass exists, so both scorings are identical."""
    monkeypatch.setenv("ENABLE_REGION_CURRENCY_GUARD", "true")
    pd = [_product("Alpha", 10.0, "BHD"), _product("Beta", 40.0, "SAR")]

    scoring = scs.get_scoring_service()
    raw = scoring.compute_scores(copy.deepcopy(pd))
    raw_winner = raw["winner_index"]

    assert apply_region_currency_guard(pd, "saudi_arabia") is True
    guarded = scoring.compute_scores(copy.deepcopy(pd))

    # The guarded product's price dimension takes the honest missing-data path.
    _bd = (guarded.get("scores", {}).get("product_0", {}) or {}).get("breakdown", {}) or {}
    assert _bd.get("price_score") in (None, 50, 50.0), _bd
    assert guarded["winner_index"] != raw_winner, (raw_winner, guarded["winner_index"])


# ---------------------------------------------------------------------------
# Streaming half — the SSE `prices` event and what compute_scores receives
# ---------------------------------------------------------------------------

def _mock_to_verdict(monkeypatch, service):
    """Copied from tests/test_m13_04_full_stream_deadline.py:41-76. Every network
    call is stubbed; `_fake_fetch` returns a BHD price, so driving the stream with
    region='saudi_arabia' produces the BHD-on-SAR mismatch with no harness edit."""
    from unittest.mock import AsyncMock, MagicMock

    monkeypatch.setattr(
        scs, "parse_product_query",
        AsyncMock(return_value=(
            {"products": [{"brand": "A", "name": "1"}, {"brand": "B", "name": "2"}],
             "comparison_type": "value"},
            {},
        )),
    )

    async def _fake_fetch(product, region, include_specs, include_reviews, nocache,
                          partial_slot=0, **kw):
        return {
            "brand": product.get("brand", "X"),
            "name": product.get("name", "Y"),
            "specs": {"k": "v"},
            "price": {"amount": 10.0, "currency": "BHD", "estimated": False},
            "reviews": {"highlights": []},
            "fact_check": {"overall_confidence": "medium"},
            "image_url": None,
        }
    monkeypatch.setattr(service, "_fetch_product_data", _fake_fetch)

    scoring = MagicMock()
    scoring.compute_scores.return_value = {
        "scores": {"product_0": {"breakdown": {"value_score": 60}},
                   "product_1": {"breakdown": {"value_score": 50}}},
        "winner_index": 0, "win_margin": 5, "dimension_winners": {}, "price_tiers": {},
    }
    scoring.build_scores_summary.return_value = ""
    scoring.compute_confidence.return_value = 0.5
    scoring.compute_value_badge.return_value = ""
    scoring.compute_tradeoff_pairs.return_value = []
    monkeypatch.setattr(scs, "get_scoring_service", lambda: scoring)
    monkeypatch.setattr(scs, "reconcile_pair_fairness", lambda *a, **k: None)
    # The harness price carries no retailer/url, so the exact-SKU correctness
    # gate (ENABLE_EXACT_PRICE_GATE, default ON) would pend it in the `prices`
    # projection for a reason that has nothing to do with this unit. Force it
    # showable so the ONLY pend under test is the region-currency guard.
    monkeypatch.setattr(scs, "is_price_showable", lambda *a, **k: True)
    return scoring


async def _prices_event(monkeypatch):
    service = scs.StructuredComparisonService()
    scoring = _mock_to_verdict(monkeypatch, service)
    payload = None
    async for event_type, data in service.compare_from_text_streaming(
        query="A vs B", region="saudi_arabia"
    ):
        if event_type == "prices" and payload is None:
            payload = data
        if event_type in ("verdict", "complete"):
            break
    return payload, scoring


@pytest.mark.asyncio
async def test_streaming_prices_event_pends_mismatched_currency_when_flag_on(monkeypatch):
    """RED at 17cb981: the raw 10.0 BHD is streamed to a Saudi client, then
    retracted by the final `complete` payload."""
    monkeypatch.setenv("ENABLE_REGION_CURRENCY_GUARD", "true")
    payload, _ = await _prices_event(monkeypatch)
    assert payload["product_0"]["price"]["amount"] is None
    assert payload["product_0"]["price"]["unavailable"] is True


@pytest.mark.asyncio
async def test_streaming_prices_event_unchanged_when_flag_off(monkeypatch):
    """GREEN today and after — flag OFF streams the raw amount, as at 17cb981."""
    monkeypatch.delenv("ENABLE_REGION_CURRENCY_GUARD", raising=False)
    payload, _ = await _prices_event(monkeypatch)
    assert payload["product_0"]["price"]["amount"] == 10.0


@pytest.mark.asyncio
async def test_streaming_compute_scores_receives_guarded_product_data(monkeypatch):
    """RED at 17cb981 on the flag-ON leg: compute_scores sees the raw amount."""
    monkeypatch.setenv("ENABLE_REGION_CURRENCY_GUARD", "true")
    _, scoring = await _prices_event(monkeypatch)
    seen = scoring.compute_scores.call_args[0][0]
    assert seen[0]["price"]["amount"] is None

    monkeypatch.delenv("ENABLE_REGION_CURRENCY_GUARD", raising=False)
    _, scoring_off = await _prices_event(monkeypatch)
    seen_off = scoring_off.compute_scores.call_args[0][0]
    assert seen_off[0]["price"]["amount"] == 10.0


# ---------------------------------------------------------------------------
# The chokepoint backstop keeps its metadata diagnostic
# ---------------------------------------------------------------------------

def test_m13_11_metadata_guard_rejected_survives_an_upstream_pend(monkeypatch):
    """RED at 17cb981: the `unavailable is True` early-continue in
    response_builder returns BEFORE the diag is appended, so an upstream pend
    silently drops `region_currency_mismatch` from metadata.guard_rejected."""
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
