"""S2 I2.5 — review-content consultation from usage="review" registry sources.

`fetch_review_source_snippets()` runs ONE Serper site-filtered search across
the category's review sources (the Arabic GCC sources for beauty/fashion).
Budget-gated, cached 14d, returns [] on miss — never raises, never
critical-path.
"""

import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

import pytest
from unittest.mock import AsyncMock, patch

from app.services.review_service import (
    consult_review_sources,
    fetch_review_source_snippets,
    passive_review_snippets,
    review_source_consult_mode,
)


@pytest.mark.asyncio
async def test_consult_records_serper_budget_exactly_once():
    """F4 (G2): search_web records the serper budget meter internally — the
    consult path must NOT add a second manual record_usage (that double-counted
    AND counted failures). We spy on record_usage (NOT mock it away) and have
    the search_web stub call it ONCE to mimic serper_service's internal record;
    total must stay 1, proving the consult adds zero."""
    from unittest.mock import MagicMock
    import app.services.review_service as rs

    record_spy = MagicMock()

    async def fake_search_web(query, num_results=6):
        # Mimic serper_service.search_web: it records the meter ONCE on success.
        rs.record_usage("serper")
        return {"organic": [{"link": "https://sayidaty.net/a",
                             "snippet": "A sufficiently long editorial review snippet about wear."}]}

    with patch("app.services.review_service.search_web", new=AsyncMock(side_effect=fake_search_web)), \
         patch("app.services.review_service.get_cached", return_value=None), \
         patch("app.services.review_service.set_cached", return_value=True), \
         patch("app.services.review_service.has_budget", return_value=True), \
         patch("app.services.review_service.record_usage", new=record_spy):
        snippets = await rs.fetch_review_source_snippets("Maybelline", "Fit Me", None, "makeup")

    assert len(snippets) == 1
    # EXACTLY one serper record — search_web's internal one, none added by consult.
    serper_records = [c for c in record_spy.call_args_list if c.args and c.args[0] == "serper"]
    assert len(serper_records) == 1, (
        f"expected exactly 1 serper budget record, got {len(serper_records)} "
        "(double-count regressed)"
    )


@pytest.mark.asyncio
async def test_returns_snippets_from_review_sources():
    async def fake_search_web(query, num_results=6):
        # The query must target the Arabic review sources for a makeup product.
        assert "site:sayidaty.net" in query or "site:gulfnews.com" in query
        return {
            "organic": [
                {
                    "title": "Best foundations for Gulf summer",
                    "snippet": "This foundation held up through a humid Bahrain afternoon without sliding.",
                    "link": "https://www.sayidaty.net/beauty/foundations",
                }
            ]
        }

    with patch(
        "app.services.review_service.search_web",
        new=AsyncMock(side_effect=fake_search_web),
    ), patch(
        "app.services.review_service.get_cached", return_value=None,
    ), patch(
        "app.services.review_service.set_cached", return_value=True,
    ), patch(
        "app.services.review_service.has_budget", return_value=True,
    ), patch(
        "app.services.review_service.record_usage", return_value=None,
    ):
        snippets = await fetch_review_source_snippets(
            "Maybelline", "Fit Me Foundation", None, "makeup"
        )

    assert len(snippets) == 1
    assert snippets[0]["domain"] == "sayidaty.net"
    assert "humid" in snippets[0]["text"]


@pytest.mark.asyncio
async def test_empty_for_category_without_review_sources():
    """electronics has no usage='review' registry source → no Serper call,
    returns []."""
    search_mock = AsyncMock()
    with patch("app.services.review_service.search_web", new=search_mock):
        snippets = await fetch_review_source_snippets(
            "Apple", "iPhone 15", None, "electronics"
        )
    assert snippets == []
    search_mock.assert_not_called()  # never spends a Serper credit


@pytest.mark.asyncio
async def test_empty_when_budget_exhausted():
    """Budget guard: no Serper call when serper budget is exhausted."""
    search_mock = AsyncMock()
    with patch(
        "app.services.review_service.get_cached", return_value=None,
    ), patch(
        "app.services.review_service.has_budget", return_value=False,
    ), patch("app.services.review_service.search_web", new=search_mock):
        snippets = await fetch_review_source_snippets(
            "Dior", "Sauvage", None, "fragrances"
        )
    assert snippets == []
    search_mock.assert_not_called()


@pytest.mark.asyncio
async def test_serper_failure_returns_empty_never_raises():
    async def boom(query, num_results=6):
        raise RuntimeError("serper down")

    with patch(
        "app.services.review_service.search_web", new=AsyncMock(side_effect=boom),
    ), patch(
        "app.services.review_service.get_cached", return_value=None,
    ), patch(
        "app.services.review_service.has_budget", return_value=True,
    ):
        snippets = await fetch_review_source_snippets(
            "Chanel", "No 5", None, "fragrances"
        )
    assert snippets == []  # graceful — never raises


@pytest.mark.asyncio
async def test_cache_hit_skips_serper():
    search_mock = AsyncMock()
    cached = {"snippets": [{"domain": "gulfnews.com", "text": "A long enough cached review snippet here."}]}
    with patch(
        "app.services.review_service.get_cached", return_value=cached,
    ), patch("app.services.review_service.search_web", new=search_mock):
        snippets = await fetch_review_source_snippets(
            "L'Oreal", "True Match", None, "makeup"
        )
    assert snippets == cached["snippets"]
    search_mock.assert_not_called()


@pytest.mark.asyncio
async def test_short_snippets_filtered_out():
    async def fake_search_web(query, num_results=6):
        return {
            "organic": [
                {"snippet": "Too short.", "link": "https://gulfnews.com/x"},
                {
                    "snippet": "A sufficiently detailed editorial note about long-wear performance in heat.",
                    "link": "https://gulfnews.com/beauty",
                },
            ]
        }

    with patch(
        "app.services.review_service.search_web",
        new=AsyncMock(side_effect=fake_search_web),
    ), patch(
        "app.services.review_service.get_cached", return_value=None,
    ), patch(
        "app.services.review_service.set_cached", return_value=True,
    ), patch(
        "app.services.review_service.has_budget", return_value=True,
    ), patch(
        "app.services.review_service.record_usage", return_value=None,
    ):
        snippets = await fetch_review_source_snippets(
            "NARS", "Foundation", None, "makeup"
        )
    assert len(snippets) == 1
    assert "long-wear" in snippets[0]["text"]


# ---------------------------------------------------------------------------
# Flag + mode dispatcher (ENABLE_REVIEW_SOURCE_CONSULT)
# ---------------------------------------------------------------------------

def test_mode_off_by_default(monkeypatch):
    monkeypatch.delenv("ENABLE_REVIEW_SOURCE_CONSULT", raising=False)
    assert review_source_consult_mode() is None


@pytest.mark.parametrize("val,expected", [
    # F3 (G2): ONLY explicit "active" selects the Serper-burning active mode.
    ("active", "active"),
    # Generic truthy flips default to the SAFE passive mode (zero extra Serper).
    ("true", "passive"), ("1", "passive"), ("on", "passive"), ("passive", "passive"),
    # Falsy / unknown → OFF.
    ("", None), ("nope", None), ("off", None), ("false", None),
])
def test_mode_parsing(monkeypatch, val, expected):
    monkeypatch.setenv("ENABLE_REVIEW_SOURCE_CONSULT", val)
    assert review_source_consult_mode() == expected


def test_truthy_flip_does_not_select_active(monkeypatch):
    """F3 regression: a careless `=true` must NOT start burning Serper — it
    selects passive (zero-extra-Serper), never active."""
    for truthy in ("true", "1", "on", "TRUE", "On"):
        monkeypatch.setenv("ENABLE_REVIEW_SOURCE_CONSULT", truthy)
        assert review_source_consult_mode() == "passive"


@pytest.mark.asyncio
async def test_consult_off_returns_empty_no_serper(monkeypatch):
    monkeypatch.delenv("ENABLE_REVIEW_SOURCE_CONSULT", raising=False)
    search_mock = AsyncMock()
    with patch("app.services.review_service.search_web", new=search_mock):
        out = await consult_review_sources(
            "Dior", "Sauvage", None, "fragrances",
            {"organic": [{"link": "https://gulfnews.com/x", "snippet": "x" * 40}]},
        )
    assert out == []
    search_mock.assert_not_called()  # OFF spends nothing


@pytest.mark.asyncio
async def test_consult_passive_reads_existing_organic(monkeypatch):
    monkeypatch.setenv("ENABLE_REVIEW_SOURCE_CONSULT", "passive")
    search_mock = AsyncMock()
    organic = {
        "organic": [
            {"link": "https://amazon.ae/p", "snippet": "A retailer listing, not a review source."},
            {"link": "https://www.gulfnews.com/beauty/article",
             "snippet": "Editorial: this foundation survived a humid Gulf afternoon beautifully."},
        ]
    }
    with patch("app.services.review_service.search_web", new=search_mock):
        out = await consult_review_sources(
            "Maybelline", "Fit Me", None, "makeup", organic,
        )
    assert len(out) == 1
    assert out[0]["domain"] == "gulfnews.com"  # only the review-source hit
    search_mock.assert_not_called()  # passive = zero extra Serper


def test_passive_helper_ignores_non_review_domains():
    organic = {"organic": [
        {"link": "https://noon.com/p", "snippet": "Retailer snippet long enough to pass."},
        {"link": "https://sayidaty.net/x", "snippet": "Review-source editorial snippet here."},
    ]}
    out = passive_review_snippets(organic, "makeup")
    assert len(out) == 1
    assert out[0]["domain"] == "sayidaty.net"


def test_passive_empty_for_non_review_category():
    organic = {"organic": [{"link": "https://gulfnews.com/x", "snippet": "x" * 40}]}
    # electronics has no usage="review" sources -> []
    assert passive_review_snippets(organic, "electronics") == []


@pytest.mark.asyncio
async def test_consult_active_dispatches_dedicated_call(monkeypatch):
    monkeypatch.setenv("ENABLE_REVIEW_SOURCE_CONSULT", "active")

    async def fake_search_web(query, num_results=6):
        return {"organic": [{"link": "https://sayidaty.net/a",
                             "snippet": "Active-mode dedicated fetch review snippet, long enough."}]}

    with patch(
        "app.services.review_service.search_web", new=AsyncMock(side_effect=fake_search_web),
    ), patch(
        "app.services.review_service.get_cached", return_value=None,
    ), patch(
        "app.services.review_service.set_cached", return_value=True,
    ), patch(
        "app.services.review_service.has_budget", return_value=True,
    ), patch(
        "app.services.review_service.record_usage", return_value=None,
    ):
        out = await consult_review_sources(
            "Maybelline", "Fit Me", None, "makeup", None,
        )
    assert len(out) == 1
    assert out[0]["domain"] == "sayidaty.net"


@pytest.mark.asyncio
async def test_consult_active_timeout_yields_empty(monkeypatch):
    monkeypatch.setenv("ENABLE_REVIEW_SOURCE_CONSULT", "active")

    async def slow_fetch(*a, **k):
        import asyncio as _a
        await _a.sleep(5)
        return [{"domain": "x", "text": "y"}]

    with patch(
        "app.services.review_service.fetch_review_source_snippets", new=slow_fetch,
    ):
        out = await consult_review_sources(
            "X", "Y", None, "makeup", None, timeout=0.05,
        )
    assert out == []  # capped, never blocks


# ---------------------------------------------------------------------------
# F3 (G2 re-review) — get_reviews persists the extraction BEFORE the consult
# ---------------------------------------------------------------------------
# These call get_reviews itself (the 16 other consult tests don't) so a future
# refactor moving set_cached/save_reviews back BELOW the consult — which would
# reintroduce the extraction-loss-on-cancel mechanism — is caught with a test.


@pytest.mark.asyncio
async def test_get_reviews_persists_extraction_before_consult(monkeypatch):
    """ORDER pin: in active mode, set_cached + save_reviews (the extraction
    persist) MUST be invoked BEFORE consult_review_sources."""
    import app.services.review_service as rs
    monkeypatch.setenv("ENABLE_REVIEW_SOURCE_CONSULT", "active")

    order = []

    def _set_cached(key, value, ttl):
        order.append("set_cached")
        return True

    async def _save_reviews(*a, **k):
        order.append("save_reviews")

    async def _consult(*a, **k):
        order.append("consult")
        return [{"domain": "sayidaty.net", "text": "An editorial review snippet, long enough."}]

    async def _extract(brand, name, variant, ctx, category="other"):
        return ({"review_summary": {"highlights": []}}, {"total_tokens": 10})

    with patch("app.services.review_service.get_cached", return_value=None), \
         patch("app.services.review_service.set_cached", side_effect=_set_cached), \
         patch("app.services.review_service.extract_reviews", new=AsyncMock(side_effect=_extract)), \
         patch("app.services.review_service.consult_review_sources", new=AsyncMock(side_effect=_consult)), \
         patch("app.services.product_data_service.get_cached_reviews", new=AsyncMock(return_value=None)), \
         patch("app.services.product_data_service.save_reviews", new=AsyncMock(side_effect=_save_reviews)):
        reviews = await rs.get_reviews(
            "Maybelline", "Fit Me", None, "Maybelline Fit Me",
            nocache=True, category="makeup",
            search_results={"organic": []},
        )

    # The extraction persist (set_cached + save_reviews task creation) precedes
    # the consult. (save_reviews is fire-and-forget; the create_task call which
    # schedules it happens before consult — we assert set_cached ordering as the
    # synchronous, deterministic marker.)
    assert "set_cached" in order and "consult" in order
    assert order.index("set_cached") < order.index("consult"), (
        f"extraction must persist BEFORE consult; got order {order}"
    )
    # The enriched key lands on the returned reviews.
    assert reviews.get("review_source_quotes")


@pytest.mark.asyncio
async def test_get_reviews_extraction_persisted_even_if_consult_cancels(monkeypatch):
    """CANCEL safety: a consult that is cancelled (cap fires mid-consult) must
    still leave the extraction persisted — set_cached ran before the consult."""
    import asyncio
    import app.services.review_service as rs
    monkeypatch.setenv("ENABLE_REVIEW_SOURCE_CONSULT", "active")

    set_cached_calls = []

    async def _consult_cancels(*a, **k):
        raise asyncio.CancelledError()

    async def _extract(brand, name, variant, ctx, category="other"):
        return ({"review_summary": {"highlights": []}}, {"total_tokens": 10})

    with patch("app.services.review_service.get_cached", return_value=None), \
         patch("app.services.review_service.set_cached",
               side_effect=lambda k, v, t: set_cached_calls.append(k)), \
         patch("app.services.review_service.extract_reviews", new=AsyncMock(side_effect=_extract)), \
         patch("app.services.review_service.consult_review_sources", new=AsyncMock(side_effect=_consult_cancels)), \
         patch("app.services.product_data_service.get_cached_reviews", new=AsyncMock(return_value=None)), \
         patch("app.services.product_data_service.save_reviews", new=AsyncMock()):
        # The CancelledError from the consult propagates (it's not a generic
        # Exception), simulating the outer race cancelling mid-consult — but the
        # extraction was already persisted before the consult began.
        with pytest.raises(asyncio.CancelledError):
            await rs.get_reviews(
                "Maybelline", "Fit Me", None, "Maybelline Fit Me",
                nocache=True, category="makeup",
                search_results={"organic": []},
            )

    assert set_cached_calls, "extraction was NOT persisted before the consult cancelled"
