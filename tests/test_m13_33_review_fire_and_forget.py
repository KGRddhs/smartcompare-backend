"""M13-33 pin — the L2 reviews persist must be fire-and-forget WITH a done-callback.

Failure scenario: `get_reviews` persisted the completed extraction to the L2 DB
cache via a plain `asyncio.create_task(save_reviews(...))`. If `save_reviews`
raises (RLS denial, schema drift, Supabase 5xx) the exception is swallowed — the
L2 cache silently stops being written and every later request re-pays a Serper
search + GPT extract, with nothing in logs or Sentry. The repo bans plain
`create_task` in favour of `fire_and_forget(coro, label=...)`, whose done-callback
logs a WARNING on failure.
"""
import asyncio
import logging

import pytest

from app.services import review_service


@pytest.mark.asyncio
async def test_save_reviews_exception_is_logged_not_swallowed(monkeypatch, caplog):
    reviews_payload = {"reviews": [{"text": "great scent, lasts all day"}]}

    async def fake_extract_reviews(brand, name, variant, ctx, category="other"):
        return reviews_payload, {"total_tokens": 0}

    async def fake_search_web(q):
        return {"organic": []}

    async def boom_save_reviews(cache_key, brand, name, variant, reviews):
        raise RuntimeError("supabase 5xx from save_reviews")

    async def fake_get_cached_reviews(cache_key):
        return None

    # Cache miss on L1 + L2 so the extraction + persist path runs.
    monkeypatch.setattr(review_service, "get_cached", lambda key: None)
    monkeypatch.setattr(review_service, "set_cached", lambda *a, **k: None)
    monkeypatch.setattr(review_service, "search_web", fake_search_web)
    monkeypatch.setattr(review_service, "extract_reviews", fake_extract_reviews)
    # get_cached_reviews / save_reviews are imported INSIDE get_reviews from
    # product_data_service, so patch them at their source module.
    import app.services.product_data_service as pds
    monkeypatch.setattr(pds, "get_cached_reviews", fake_get_cached_reviews)
    monkeypatch.setattr(pds, "save_reviews", boom_save_reviews)

    caplog.set_level(logging.WARNING)

    await review_service.get_reviews(
        brand="Dior",
        name="Sauvage EDP",
        variant=None,
        search_query="Dior Sauvage EDP",
        nocache=False,
        category="fragrances",
    )
    # Let the fire-and-forget persist task run to completion so its
    # done-callback can fire.
    for _ in range(5):
        await asyncio.sleep(0)

    warned = [
        r for r in caplog.records
        if r.levelno == logging.WARNING and "save_reviews.l2" in r.getMessage()
    ]
    assert warned, (
        "save_reviews failure was swallowed — expected a fire-and-forget "
        "done-callback WARNING carrying label 'save_reviews.l2'; got: "
        + repr([r.getMessage() for r in caplog.records])
    )
