"""Wave-1 — price-cache warmer preconditions: a Serper-budget guard.

The warmer burns PAID Serper continuously (each query warms 2 products at
~10-30 credits). Today the only spend control is the MAX_QUERIES_PER_RUN count
cap; there is no headroom check, so a run can drive the key straight into
overage. These pin a two-layer guard:
  - a PRE-RUN window trim: shrink the run to what the remaining Serper budget
    can afford (never grows it);
  - a PER-QUERY circuit: stop the loop the moment Serper is exhausted.
Both fail-OPEN (a Redis/budget outage must not block the warmer) — the hard
MAX_QUERIES_PER_RUN cap remains the Redis-down backstop.
"""
from __future__ import annotations

from unittest import mock

from scripts import cron_warm_price_cache as warmer


def _win(n):
    return [{"query": f"q{i}", "region": "bahrain"} for i in range(n)]


def test_budget_bounded_window_trims_to_affordable():
    # remaining=60 credits, ~30/query -> affords ~2 of 5.
    with mock.patch.object(warmer, "_serper_per_query_estimate", return_value=30), \
         mock.patch("app.services.api_budget_service.get_remaining", return_value=60):
        out = warmer._budget_bounded_window(_win(5))
    assert len(out) == 2


def test_budget_bounded_window_keeps_full_when_ample():
    with mock.patch.object(warmer, "_serper_per_query_estimate", return_value=30), \
         mock.patch("app.services.api_budget_service.get_remaining", return_value=10_000):
        out = warmer._budget_bounded_window(_win(5))
    assert len(out) == 5


def test_budget_bounded_window_fail_open_on_error():
    # get_remaining raising (Redis down) must NOT trim (fail-open) — the count
    # cap MAX_QUERIES_PER_RUN is the backstop.
    with mock.patch.object(warmer, "_serper_per_query_estimate", return_value=30), \
         mock.patch("app.services.api_budget_service.get_remaining",
                    side_effect=RuntimeError("redis down")):
        out = warmer._budget_bounded_window(_win(5))
    assert len(out) == 5


def test_budget_bounded_window_zero_when_no_headroom():
    with mock.patch.object(warmer, "_serper_per_query_estimate", return_value=30), \
         mock.patch("app.services.api_budget_service.get_remaining", return_value=10):
        out = warmer._budget_bounded_window(_win(5))
    assert out == []


def test_serper_exhausted_reflects_has_budget():
    with mock.patch("app.services.api_budget_service.has_budget", return_value=False):
        assert warmer._serper_exhausted() is True
    with mock.patch("app.services.api_budget_service.has_budget", return_value=True):
        assert warmer._serper_exhausted() is False


def test_serper_exhausted_fail_open_false_on_error():
    with mock.patch("app.services.api_budget_service.has_budget",
                    side_effect=RuntimeError("redis down")):
        assert warmer._serper_exhausted() is False
