"""M13-34 — one clamp for every genuine-BH adapter's inner fetch timeout.

Eleven divergent hardcoded ceilings lived across the adapter modules (woocommerce
10, salla 12, occ 12, magento-gql 12, unbxd 8, rest_json 12, noon 8, brightdata
20). Four exceeded the per-source `_timeout_none` wrap in
`structured_comparison_service._ADAPTER_TIMEOUT` (10s), so that wrap returned None
at 10s while the thread stayed parked in `curl.perform()` on the shared executor;
Bright Data's 20s even sat above the 15s `_PRICE_RACE_TIMEOUT`, so the Serper-
depletion fallback could only ever return AFTER the race had already cancelled.

`adapter_timeout(default)` clamps any adapter ceiling strictly under the per-source
wrap (which is itself under the 15s race). This module imports nothing from `app`,
so the adapter modules can route their constants through it with no import cycle
(scs -> adapters -> adapter_timeouts, never back).
"""
from __future__ import annotations

import os

# Mirror of structured_comparison_service._ADAPTER_TIMEOUT — the per-source
# _timeout_none wrap every adapter fetch runs inside. Kept as a literal here (not
# imported) to avoid the scs -> adapter -> scs import cycle; a test pins that this
# equals scs._ADAPTER_TIMEOUT so the two can never silently drift.
_ADAPTER_WRAP_TIMEOUT = 10.0

# Margin between an adapter's inner curl/httpx ceiling and the wrap, so the inner
# fetch abandons its socket BEFORE the wrap returns None (no parked thread).
_INNER_MARGIN = 1.0


def _price_race_timeout() -> float:
    """The Phase-1 price-race deadline (env PRICE_RACE_TIMEOUT, default 15.0) —
    read the same way structured_comparison_service reads it, so a warmer that
    raises it does not shrink the ceiling below the wrap."""
    try:
        return float(os.getenv("PRICE_RACE_TIMEOUT", "15.0"))
    except (TypeError, ValueError):
        return 15.0


def adapter_inner_ceiling() -> float:
    """The maximum inner fetch timeout an adapter may use: one margin under the
    smaller of the per-source wrap and the price race."""
    return max(1.0, min(_ADAPTER_WRAP_TIMEOUT, _price_race_timeout()) - _INNER_MARGIN)


def adapter_timeout(default: float) -> float:
    """Clamp an adapter's requested inner fetch timeout under the per-source wrap.

    A fast source is unaffected (it resolves in well under a second); the clamp
    only bites a SLOW fetch, and there the outer `_timeout_none` wrap already
    returned None at the wrap deadline — so the clamp changes no returned result,
    it only stops the underlying socket from parking past the wrap.
    """
    return min(float(default), adapter_inner_ceiling())
