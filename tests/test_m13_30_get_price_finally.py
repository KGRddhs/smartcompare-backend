"""M13-30 pin — _get_price cancels its speculative prefetch tasks on an outer cancel.

Failure scenario: _get_price had no try/finally around the body that creates ~18
speculative ensure_future tasks (4 discovery search_web calls + the direct adapter
gathers). Those are independent Tasks that survive the outer wait_for cancel and
run to completion unread. This pin drives _get_price to the point where the 4
discovery prefetch tasks are live and the coroutine is parked at the Tier-1
shopping await (BEFORE the discovery ownership-transfer at ~6230), then cancels
it and asserts every prefetch search_web task received CancelledError — i.e. the
finally converged on _cancel_prefetched_discovery().

All network is monkeypatched; zero live calls.
"""
import os
os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

import asyncio
import pytest


@pytest.mark.asyncio
async def test_outer_cancel_converges_on_prefetch_cleanup(monkeypatch):
    import app.services.structured_comparison_service as scs
    svc = scs.get_comparison_service()

    # Miss every cache/DB/validation gate so _get_price runs the live cascade and
    # reaches prefetch creation.
    monkeypatch.setattr(scs, "get_cached", lambda *a, **k: None)
    monkeypatch.setattr(scs, "get_negative_cache", lambda *a, **k: None, raising=False)
    monkeypatch.setattr(scs, "set_cached", lambda *a, **k: None)
    monkeypatch.setattr(scs, "validate_price_query", lambda *a, **k: True)
    monkeypatch.setattr(svc, "_save_price_to_db", lambda *a, **k: None, raising=False)

    async def _no_db_price(*a, **k):
        return None
    monkeypatch.setattr(
        "app.services.product_data_service.get_cached_price", _no_db_price,
        raising=False,
    )

    # _pf_eligible: not supplement (makeup) + no shopify/algolia sources -> the
    # 4 discovery search_web prefetch tasks are created.
    monkeypatch.setattr(scs, "get_shopify_sources_for_category", lambda c: [])
    monkeypatch.setattr(scs, "get_algolia_sources_for_category", lambda c: [])

    started = []

    async def hanging_search_web(q, *a, **k):
        marker = {"q": q, "cancelled": False}
        started.append(marker)
        try:
            await asyncio.sleep(3600)
        except asyncio.CancelledError:
            marker["cancelled"] = True
            raise
        return {"organic": []}

    # Park the coroutine at the Tier-1 shopping await (which is AFTER the discovery
    # prefetch creation and BEFORE the discovery ownership-transfer), so the still-
    # pending prefetch tasks live in _prefetched_discovery when we cancel.
    async def hanging_shopping(*a, **k):
        await asyncio.sleep(3600)
        return {"shopping": [], "organic": [], "shopping_region": "bahrain"}

    monkeypatch.setattr(scs, "search_web", hanging_search_web)
    monkeypatch.setattr(scs, "search_product_prices", hanging_shopping)

    task = asyncio.ensure_future(svc._get_price(
        brand="elf", name="SuperHydrate Moisturizer", variant=None,
        region="bahrain", search_query="elf SuperHydrate Moisturizer",
        nocache=True, category="makeup",
    ))
    # Let the prefetch tasks start and the coroutine park at the shopping await.
    for _ in range(20):
        await asyncio.sleep(0)
    await asyncio.sleep(0.05)

    assert not task.done(), "expected _get_price parked at the shopping await"
    assert started, "no discovery prefetch search_web tasks were created"

    # Outer cancel (what the Phase-1 wait_for does on the 15s deadline).
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    # Let the finally's cancellations propagate into the prefetch coroutines.
    for _ in range(20):
        await asyncio.sleep(0)

    orphaned = [m for m in started if not m["cancelled"]]
    assert not orphaned, (
        f"{len(orphaned)} of {len(started)} discovery prefetch tasks orphaned on "
        f"outer cancel (finally did not converge on cleanup): {orphaned!r}"
    )
