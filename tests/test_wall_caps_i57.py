"""I5.7 (Bundle B S2) — wall-cap tightening (PRE-AUTHORIZED, Decision D).

Two pre-authorized latency caps tightened together (Decision D: "fan_out 15s→12s
pre-authorized"; the price-race cap follows to ~14-15s so the outer per-product
price wall keeps a sane margin over the now-12s inner fan_out race):

  1. The Tier-1.5 fan_out price race (`fan_out_price_lookup`, ssc ~2819) is bounded
     by asyncio.wait_for — tightened 15.0s → 12.0s. Cloudflare-protected scrapes
     that blow the budget now fall through to Tier 2 sooner.
  2. The Phase-1 per-product price race cap (`_PHASE1_TIMEOUTS["price"]`) — tightened
     18.0s → 15.0s. This OUTER cap wraps the whole _get_price path (Tier 1 +
     escalation decision + the 12s fan_out race + Tier 3 estimate), so it stays
     above the inner fan_out cap with ~3s headroom.

Escalation TRIGGERING (`_should_escalate_price_scrape`) is UNTOUCHED — these caps
bound how long scrapers RUN, not WHETHER escalation fires (never blind the
instrument). Pinned via source inspection, matching the established method-scoped
constant pattern in test_phase1_per_race_timeouts.py.
"""
import inspect

from app.services.structured_comparison_service import StructuredComparisonService


def test_fan_out_price_race_capped_at_12s():
    """The fan_out_price_lookup race must be bounded by a 12s budget by default.

    S3-genuine Approach A part 2 split the single fan_out into a curl wave + a
    render wave that SHARE one deadline; each wave's wait_for gets the remaining
    budget. WS3/D5 (genuine-bh latency bundle) then made that shared budget
    ENV-CONFIGURABLE: `_FAN_OUT_BUDGET = _fan_out_budget_seconds()`, which reads
    FAN_OUT_BUDGET_SECONDS (default "12.0"). LIVE traffic keeps the sacred 12s
    default; the off-clock warmer raises it to 35s. The 12s live cap is
    preserved — it's just sourced from a helper instead of a hard literal.
    """
    source = inspect.getsource(StructuredComparisonService._get_price)
    assert "fan_out_price_lookup" in source, "fan_out race call missing"
    # WS3/D5 — the budget is now the env-config helper, not a hard literal.
    assert "_FAN_OUT_BUDGET = _fan_out_budget_seconds()" in source, (
        "WS3/D5: the Tier-1.5 fan_out budget must come from "
        "_fan_out_budget_seconds() (env-config, default 12.0; shared across "
        "the curl+render waves)"
    )
    # Behavioral intent pin: the helper's LIVE default (env unset) is 12.0s, so
    # live traffic still gets the sacred 12s cap. Guards a future edit that
    # changes the default away from 12.0.
    import os as _os

    from app.services.structured_comparison_service import _fan_out_budget_seconds
    _prior = _os.environ.pop("FAN_OUT_BUDGET_SECONDS", None)
    try:
        assert _fan_out_budget_seconds() == 12.0, (
            "WS3/D5: the LIVE default fan_out budget (env unset) must stay 12.0s"
        )
    finally:
        if _prior is not None:
            _os.environ["FAN_OUT_BUDGET_SECONDS"] = _prior
    # The fan_out waits use the remaining shared budget.
    assert "timeout=_remaining" in source, (
        "the two waves must each wait_for the remaining shared budget"
    )
    # The old 15s cap must be gone from the fan_out race so the tightening is real.
    assert "timeout=15.0" not in source, (
        "I5.7: the stale 15.0s fan_out cap must be removed from _get_price"
    )


def test_phase1_price_race_capped_at_15s():
    """The Phase-1 per-product price race cap must be 15.0s (was 18.0s), and must
    stay strictly above the 12s inner fan_out race so the outer wall doesn't cut
    a fan_out race that's still within its own budget.

    Fix A made the cap a module-level constant (_PRICE_RACE_TIMEOUT, default 15.0,
    test-patchable) wired into _PHASE1_TIMEOUTS['price'] — so the cap VALUE is
    pinned on the constant, and the dict is pinned to reference it.
    """
    import app.services.structured_comparison_service as _scs
    assert _scs._PRICE_RACE_TIMEOUT == 15.0, (
        "I5.7: the outer price-race cap must be 15.0 (tightened from 18.0)"
    )
    source = inspect.getsource(StructuredComparisonService._fetch_product_data)
    assert "_PHASE1_TIMEOUTS" in source, "per-race timeout map missing"
    assert "_PRICE_RACE_TIMEOUT" in source, (
        "_PHASE1_TIMEOUTS['price'] must reference the _PRICE_RACE_TIMEOUT constant"
    )
    assert ("\"price\": 18.0" not in source and "'price': 18.0" not in source), (
        "I5.7: the stale 18.0s price cap must be gone"
    )


def test_price_outer_cap_exceeds_inner_fan_out_cap():
    """Invariant: the outer per-product price cap (15s) must exceed the inner
    fan_out race cap (12s) so the outer wait_for never cuts a fan_out race that's
    still within budget. This guards against a future edit dropping them out of
    order."""
    import app.services.structured_comparison_service as _scs
    fetch_src = inspect.getsource(StructuredComparisonService._fetch_product_data)
    price_src = inspect.getsource(StructuredComparisonService._get_price)
    # Outer cap = _PRICE_RACE_TIMEOUT (15.0), wired into _PHASE1_TIMEOUTS['price'].
    assert "_PRICE_RACE_TIMEOUT" in fetch_src
    outer = _scs._PRICE_RACE_TIMEOUT
    # The inner fan_out budget is SHARED across the curl+render waves (Approach A
    # part 2) and, since WS3/D5, sourced from _fan_out_budget_seconds() (env
    # default 12.0). So the LIVE total Tier-1.5 scrape still can't exceed 12s,
    # preserving the 15s-outer > 12s-inner invariant (no two-wave 24s blowout).
    assert "_FAN_OUT_BUDGET = _fan_out_budget_seconds()" in price_src
    # outer (15.0) > inner LIVE default (12.0) — headroom for Tier 1 + Tier 3.
    import os as _os

    from app.services.structured_comparison_service import _fan_out_budget_seconds
    _prior = _os.environ.pop("FAN_OUT_BUDGET_SECONDS", None)
    try:
        inner_live_default = _fan_out_budget_seconds()
    finally:
        if _prior is not None:
            _os.environ["FAN_OUT_BUDGET_SECONDS"] = _prior
    assert inner_live_default == 12.0
    assert outer > inner_live_default


def test_reviews_trim_context_and_tokens():
    """I5 reviews-trim (Decision D, I4 A/B quality-cleared): extract_reviews
    context [:4000]->[:2500] and max_tokens 1000->600. Other call sites untouched."""
    import inspect
    from app.services import extraction_service as es
    source = inspect.getsource(es.extract_reviews)
    assert "search_context[:2500]" in source, "reviews context must be trimmed to 2500"
    assert "search_context[:4000]" not in source, "stale 4000 context must be gone"
    assert "max_tokens=600" in source, "reviews max_tokens must be 600"
    assert "max_tokens=1000" not in source, "stale 1000 tokens must be gone from extract_reviews"
