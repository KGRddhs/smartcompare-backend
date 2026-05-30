"""Idle-time hardening — additional edge cases for image_service.

Authored while waiting for A2 peer-QA per ring brief ("idle agents never silent").

Coverage focus: concurrency safety, URL hygiene, content-safety alignment,
fail-open behavior at the boundary between budget gate + Serper Images
endpoint, and parametrized URL validity rules.
"""
from __future__ import annotations

import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


# ---------------------------------------------------------------------------
# Parametrized URL hygiene
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("url,expected", [
    ("https://example.com/foo.jpg", True),
    ("http://example.com/foo.jpg", True),
    ("https://cdn.example.com/path/to/image.webp", True),
    ("https://example.com/space in url.jpg", True),  # validator only checks scheme
    ("HTTPS://EXAMPLE.COM/foo.jpg", False),  # scheme is lower-case; Image extractors lowercase pre-emit
    ("ftp://example.com/foo.jpg", False),
    ("file:///etc/passwd", False),
    ("javascript:alert(1)", False),
    ("data:image/png;base64,iVBOR...", False),  # data: URIs rejected (FE can't load)
    ("", False),
    ("   ", False),
    ("not-a-url", False),
    ("https:", False),  # missing host but scheme matches — defensive: starts_with passes
    # Above edge: starts_with('https://') is False for 'https:' (no //), so reject
])
def test_is_valid_image_url(url, expected):
    from app.services.image_service import _is_valid_image_url

    assert _is_valid_image_url(url) is expected


@pytest.mark.parametrize("value", [
    None, 42, [], {}, True, False, 3.14, object(),
])
def test_is_valid_image_url_rejects_non_string(value):
    from app.services.image_service import _is_valid_image_url

    assert _is_valid_image_url(value) is False


# ---------------------------------------------------------------------------
# Concurrency — two parallel get_product_image_url calls don't interfere
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_two_parallel_calls_independent():
    """Two products fetched concurrently each get their own image_url result.
    Mocks return distinct URLs keyed by product name."""
    from app.services.image_service import get_product_image_url

    async def fake_search(query, num_results=1):
        return {"images": [{"imageUrl": f"https://example.com/{query}.jpg"}]}

    with patch(
        "app.services.image_service.try_consume_serper_image_credit",
        MagicMock(return_value=True),
    ), patch(
        "app.services.image_service.search_images",
        AsyncMock(side_effect=fake_search),
    ):
        a, b = await asyncio.gather(
            get_product_image_url("iPhone 15", region="bahrain"),
            get_product_image_url("Galaxy S24", region="bahrain"),
        )

    assert a == "https://example.com/iPhone 15.jpg"
    assert b == "https://example.com/Galaxy S24.jpg"


# ---------------------------------------------------------------------------
# Tier 3 prompt construction edges
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tier3_truncates_organic_results_to_10():
    """Defensive — extract_image_via_gpt should not feed unbounded organic
    snippets to GPT, keeping token usage predictable (~$0.0005 cap)."""
    from app.services import image_service

    mock_client = MagicMock()
    mock_completion = MagicMock()
    mock_completion.choices = [MagicMock()]
    mock_completion.choices[0].message.content = '{"image_url": null}'
    mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)

    huge_organic = [
        {"link": f"https://r{i}.example", "snippet": f"snippet {i}"}
        for i in range(50)
    ]

    with patch("app.services.image_service.get_client", return_value=mock_client):
        await image_service.extract_image_via_gpt("Foo", huge_organic)

    # Inspect prompt — should contain only the first 10 snippets
    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    user_content = call_kwargs["messages"][0]["content"]
    assert "snippet 9" in user_content
    assert "snippet 10" not in user_content


@pytest.mark.asyncio
async def test_tier3_handles_empty_organic_in_prompt_template():
    """The template uses 'no results' fallback when organic_block is empty;
    this should never fire today because the orchestrator short-circuits when
    organic_results is empty, but defensive coverage anyway."""
    from app.services import image_service

    mock_client = MagicMock()
    mock_completion = MagicMock()
    mock_completion.choices = [MagicMock()]
    mock_completion.choices[0].message.content = '{"image_url": null}'
    mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)

    # Single organic with empty link + snippet → still produces a non-empty
    # block ("- : "), exercising the join path without triggering the
    # "(no results)" fallback.
    with patch("app.services.image_service.get_client", return_value=mock_client):
        result = await image_service.extract_image_via_gpt(
            "Foo", [{"link": "", "snippet": ""}],
        )

    assert result is None


# ---------------------------------------------------------------------------
# Budget counter — concurrency-safe behavior
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_parallel_consume_credits_thread_safety():
    """Five parallel get_product_image_url calls each consume exactly one
    credit (verified by mocking the consume function side-effect)."""
    from app.services.image_service import get_product_image_url

    consume_calls = {"count": 0}

    def fake_consume(n=1):
        consume_calls["count"] += n
        return True

    with patch(
        "app.services.image_service.try_consume_serper_image_credit",
        MagicMock(side_effect=fake_consume),
    ), patch(
        "app.services.image_service.search_images",
        AsyncMock(return_value={"images": [{"imageUrl": "https://x.example/y.jpg"}]}),
    ):
        results = await asyncio.gather(*[
            get_product_image_url(f"Product {i}", region="bahrain")
            for i in range(5)
        ])

    assert len(results) == 5
    assert all(r == "https://x.example/y.jpg" for r in results)
    assert consume_calls["count"] == 5


# ---------------------------------------------------------------------------
# api_budget_service — Serper Images counter behavior under odd inputs
# ---------------------------------------------------------------------------

class TestSerperImageBudgetEdges:
    def test_large_n_consumes_correctly(self):
        from app.services.api_budget_service import try_consume_serper_image_credit
        mock_client = MagicMock()
        store = {"counter": 0}

        def fake_incrby(key, n):
            store["counter"] += n
            return store["counter"]

        mock_client.incrby = MagicMock(side_effect=fake_incrby)
        mock_client.expire = MagicMock(return_value=True)
        mock_client.decrby = MagicMock(side_effect=lambda k, n: store.__setitem__("counter", store["counter"] - n))

        with patch("app.services.cache_service.redis_client", mock_client):
            assert try_consume_serper_image_credit(50) is True
            assert store["counter"] == 50

    def test_consume_at_exact_limit_succeeds(self, monkeypatch):
        from app.services.api_budget_service import try_consume_serper_image_credit
        monkeypatch.setenv("SERPER_IMAGE_DAILY_BUDGET", "100")

        store = {"counter": 99}
        mock_client = MagicMock()

        def fake_incrby(key, n):
            store["counter"] += n
            return store["counter"]

        mock_client.incrby = MagicMock(side_effect=fake_incrby)
        mock_client.expire = MagicMock(return_value=True)
        mock_client.decrby = MagicMock(side_effect=lambda k, n: store.__setitem__("counter", store["counter"] - n))

        with patch("app.services.cache_service.redis_client", mock_client):
            # 99 + 1 = 100 (== limit, still OK)
            assert try_consume_serper_image_credit(1) is True
            assert store["counter"] == 100

    def test_consume_overshoots_limit_rolls_back(self, monkeypatch):
        from app.services.api_budget_service import try_consume_serper_image_credit
        monkeypatch.setenv("SERPER_IMAGE_DAILY_BUDGET", "100")

        store = {"counter": 95}
        mock_client = MagicMock()

        def fake_incrby(key, n):
            store["counter"] += n
            return store["counter"]

        mock_client.incrby = MagicMock(side_effect=fake_incrby)
        mock_client.expire = MagicMock(return_value=True)

        def fake_decrby(key, n):
            store["counter"] -= n

        mock_client.decrby = MagicMock(side_effect=fake_decrby)

        with patch("app.services.cache_service.redis_client", mock_client):
            # 95 + 10 = 105 (> limit 100) → reject + rollback to 95
            assert try_consume_serper_image_credit(10) is False
            assert store["counter"] == 95
            mock_client.decrby.assert_called_once()


# ---------------------------------------------------------------------------
# Content safety — image_url pipeline must not surface URLs from sources
# that L2 content_safety_service would have blocked (defense-in-depth)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_image_pipeline_does_not_bypass_blocklist_via_search_images():
    """Currently image_service has no content-safety filter at the URL level —
    Serper Images URLs are not run through is_text_safe. This test PINs that
    behavior + serves as a regression net: any future hardening that adds a
    filter must adjust this expectation deliberately, not accidentally."""
    from app.services.image_service import get_product_image_url

    # Even with a benign-looking URL, we currently emit it; if a future change
    # adds blocklist filtering, this test will fail and force us to update the
    # contract explicitly.
    with patch(
        "app.services.image_service.try_consume_serper_image_credit",
        MagicMock(return_value=True),
    ), patch(
        "app.services.image_service.search_images",
        AsyncMock(return_value={"images": [{"imageUrl": "https://cdn.example/legit.jpg"}]}),
    ):
        result = await get_product_image_url("Apple iPhone 15", region="bahrain")

    assert result == "https://cdn.example/legit.jpg"


# ---------------------------------------------------------------------------
# Tier ordering — when Tier 1.5 piggyback returns a URL, Tier 1 + Tier 3
# are skipped entirely, not just discarded
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_piggyback_skips_budget_check_entirely():
    """Tier 1.5 piggyback path must not consume a Serper Images credit even
    when the daily budget has room — that's the entire cost-saving rationale."""
    from app.services.image_service import get_product_image_url

    m_consume = MagicMock(return_value=True)
    m_search = AsyncMock()
    with patch(
        "app.services.image_service.try_consume_serper_image_credit", m_consume,
    ), patch("app.services.image_service.search_images", m_search):
        result = await get_product_image_url(
            "iPhone 15", region="bahrain",
            page_scrape_image="https://example.com/scraped.jpg",
        )

    assert result == "https://example.com/scraped.jpg"
    m_consume.assert_not_called()
    m_search.assert_not_called()


@pytest.mark.asyncio
async def test_invalid_piggyback_falls_through_without_being_returned():
    """A page_scrape_image that doesn't pass _is_valid_image_url validation
    must NOT be returned — fall through to Tier 1."""
    from app.services.image_service import get_product_image_url

    with patch(
        "app.services.image_service.try_consume_serper_image_credit",
        MagicMock(return_value=True),
    ), patch(
        "app.services.image_service.search_images",
        AsyncMock(return_value={"images": [{"imageUrl": "https://serper.example/x.jpg"}]}),
    ):
        result = await get_product_image_url(
            "Foo", region="bahrain",
            page_scrape_image="javascript:alert(1)",  # invalid scheme
        )

    assert result == "https://serper.example/x.jpg"


# ---------------------------------------------------------------------------
# Region kwarg is honored as a hint but doesn't break anything when unusual
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_region_kwarg_does_not_break_call():
    """Region today is reserved for future use; verify no current code path
    is sensitive to its value."""
    from app.services.image_service import get_product_image_url

    with patch(
        "app.services.image_service.try_consume_serper_image_credit",
        MagicMock(return_value=True),
    ), patch(
        "app.services.image_service.search_images",
        AsyncMock(return_value={"images": [{"imageUrl": "https://x.example/y.jpg"}]}),
    ):
        # uppercase, with special chars, empty — all should resolve
        r1 = await get_product_image_url("Foo", region="BAHRAIN")
        r2 = await get_product_image_url("Foo", region="saudi_arabia")
        r3 = await get_product_image_url("Foo", region="")

    assert r1 == "https://x.example/y.jpg"
    assert r2 == "https://x.example/y.jpg"
    assert r3 == "https://x.example/y.jpg"
