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
    """The fan_out_price_lookup race must be bounded by a 12s wait_for (was 15s)."""
    source = inspect.getsource(StructuredComparisonService._get_price)
    assert "fan_out_price_lookup" in source, "fan_out race call missing"
    assert "timeout=12.0" in source, (
        "I5.7: the fan_out_price_lookup race must be bounded by "
        "asyncio.wait_for(timeout=12.0) — tightened from 15.0 (Decision D)"
    )
    # The old 15s cap must be gone from the fan_out race so the tightening is real.
    # (15.0 may still appear elsewhere — assert the fan_out race itself no longer
    # carries it by checking the 12.0 cap sits in the same method.)
    assert "timeout=15.0" not in source, (
        "I5.7: the stale 15.0s fan_out cap must be removed from _get_price"
    )


def test_phase1_price_race_capped_at_15s():
    """The Phase-1 per-product price race cap must be 15.0s (was 18.0s), and must
    stay strictly above the 12s inner fan_out race so the outer wall doesn't cut
    a fan_out race that's still within its own budget."""
    source = inspect.getsource(StructuredComparisonService._fetch_product_data)
    assert "_PHASE1_TIMEOUTS" in source, "per-race timeout map missing"
    assert ("\"price\": 15.0" in source or "'price': 15.0" in source), (
        "I5.7: _PHASE1_TIMEOUTS['price'] must be 15.0 (tightened from 18.0)"
    )
    assert ("\"price\": 18.0" not in source and "'price': 18.0" not in source), (
        "I5.7: the stale 18.0s price cap must be gone"
    )


def test_price_outer_cap_exceeds_inner_fan_out_cap():
    """Invariant: the outer per-product price cap (15s) must exceed the inner
    fan_out race cap (12s) so the outer wait_for never cuts a fan_out race that's
    still within budget. This guards against a future edit dropping them out of
    order."""
    fetch_src = inspect.getsource(StructuredComparisonService._fetch_product_data)
    price_src = inspect.getsource(StructuredComparisonService._get_price)
    assert ("\"price\": 15.0" in fetch_src or "'price': 15.0" in fetch_src)
    assert "timeout=12.0" in price_src
    # 15.0 (outer) > 12.0 (inner) — headroom for Tier 1 + Tier 3 estimate work.
    assert 15.0 > 12.0


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
