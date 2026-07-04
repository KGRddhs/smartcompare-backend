"""Wave-1 — price-cache warmer preconditions: a per-run Serper-credit cap.

The warmer burns PAID Serper continuously (each query warms 2 products at
~10-30 credits). It is bounded by the MAX_QUERIES_PER_RUN count cap plus a
per-RUN credit ceiling (_budget_bounded_window) that is TIER-INDEPENDENT: it
does NOT consult api_budget_service's lifetime counter, which is capped at the
free-tier config ceiling (serper monthly_limit=2200) and would WRONGLY disable
the warmer on a healthy paid key once lifetime burn passes 2200 (adversarial
sweep MED). The fixed cap + count cap are the whole bound; a truly-depleted real
account just rejects calls (handled gracefully by _warm_one).
"""
from __future__ import annotations

from unittest import mock

from scripts import cron_warm_price_cache as warmer


def _win(n):
    return [{"query": f"q{i}", "region": "bahrain"} for i in range(n)]


def test_budget_bounded_window_trims_to_per_run_credit_cap():
    # cap=60 credits, ~30/query -> affords 2 of 5.
    out = warmer._budget_bounded_window(_win(5), per_query=30, max_credits=60)
    assert len(out) == 2


def test_budget_bounded_window_keeps_full_when_cap_ample():
    out = warmer._budget_bounded_window(_win(5), per_query=30, max_credits=10_000)
    assert len(out) == 5


def test_budget_bounded_window_disabled_when_cap_zero():
    # max_credits<=0 disables the credit trim (count cap MAX_QUERIES_PER_RUN remains).
    out = warmer._budget_bounded_window(_win(5), per_query=30, max_credits=0)
    assert len(out) == 5


def test_budget_bounded_window_disabled_when_per_query_zero():
    out = warmer._budget_bounded_window(_win(5), per_query=0, max_credits=900)
    assert len(out) == 5


def test_budget_bounded_window_zero_when_cap_below_one_query():
    out = warmer._budget_bounded_window(_win(5), per_query=30, max_credits=10)
    assert out == []


def test_budget_bounded_window_is_tier_independent_no_budget_calls():
    # It must NOT consult get_remaining/has_budget — those reflect the free-tier
    # ceiling and would falsely disable the warmer on a healthy paid key.
    with mock.patch("app.services.api_budget_service.get_remaining") as gr, \
         mock.patch("app.services.api_budget_service.has_budget") as hb:
        warmer._budget_bounded_window(_win(5), per_query=30, max_credits=900)
        gr.assert_not_called()
        hb.assert_not_called()


def test_defaults_are_sane(monkeypatch):
    # Isolate from any ambient WARMER_* env so the defaults are what we assert.
    monkeypatch.delenv("WARMER_SERPER_CREDITS_PER_QUERY", raising=False)
    monkeypatch.delenv("WARMER_MAX_SERPER_CREDITS_PER_RUN", raising=False)
    assert warmer._serper_per_query_estimate() == 30
    assert warmer._serper_max_credits_per_run() == 900
    # Default cap affords the default MAX_QUERIES_PER_RUN(25) window (900/30=30 >= 25).
    assert warmer._serper_max_credits_per_run() // warmer._serper_per_query_estimate() >= 25


def test_main_skips_run_when_budget_trims_window_to_empty(monkeypatch):
    # The budget-guard early-return in main(): a trimmed-to-empty window skips the
    # run (returns None) WITHOUT warming a single query.
    import asyncio
    monkeypatch.setattr(warmer, "_flag_on", lambda: True)
    monkeypatch.setattr(warmer, "load_gold_truth", lambda *a, **k: {"queries": []})
    monkeypatch.setattr(warmer, "select_queries", lambda *a, **k: _win(5))
    monkeypatch.setattr(warmer, "load_warmer_catalog", lambda *a, **k: [])
    monkeypatch.setattr(warmer, "_budget_bounded_window", lambda w, **k: [])
    warmed = {"n": 0}

    async def _no_warm(record):
        warmed["n"] += 1
        return {"genuine": 0, "converted": 0, "estimated": 0, "none": 0}

    monkeypatch.setattr(warmer, "_warm_one", _no_warm)
    result = asyncio.get_event_loop().run_until_complete(warmer.main())
    assert result is None
    assert warmed["n"] == 0  # never warmed anything
