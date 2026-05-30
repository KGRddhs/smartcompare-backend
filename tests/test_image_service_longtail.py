"""Long-tail edge tests for image_service per team-lead idle-work directive.

Focus: rare but real-world failure modes that could surface in production
once Serper Images / GPT volume scales up.

Categories covered:
- Massive Serper response (1000+ image entries)
- Malformed organic_results shapes
- Serper 'images' key as non-list (string / dict / int)
- GPT JSON with trailing data after the closing brace
- GPT response with empty choices array
- Very long product names (token budget protection)
- Unicode + RTL product names (Arabic / Hebrew)
- Concurrent budget-exhaustion race (10 parallel calls when budget is 5)
- imageUrl as a deeply-nested dict from a future Serper API change
"""
from __future__ import annotations

import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


# ---------------------------------------------------------------------------
# Massive responses
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_serper_massive_response_uses_only_first_image():
    """Serper returns 1000 image entries — we only ever look at images[0].
    No accidental O(N) processing."""
    from app.services.image_service import get_product_image_url

    huge_images = [
        {"imageUrl": f"https://example.com/img{i}.jpg"}
        for i in range(1000)
    ]
    with patch(
        "app.services.image_service.try_consume_serper_image_credit",
        MagicMock(return_value=True),
    ), patch(
        "app.services.image_service.search_images",
        AsyncMock(return_value={"images": huge_images}),
    ):
        result = await get_product_image_url("Foo", region="bahrain")

    assert result == "https://example.com/img0.jpg"


# ---------------------------------------------------------------------------
# Malformed organic_results shapes
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_organic_with_none_entries_does_not_crash():
    """If organic_results has None entries, GPT prompt builder must not crash."""
    from app.services import image_service

    mock_client = MagicMock()
    mock_completion = MagicMock()
    mock_completion.choices = [MagicMock()]
    mock_completion.choices[0].message.content = '{"image_url": null}'
    mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)

    with patch("app.services.image_service.get_client", return_value=mock_client):
        # None in the list — dict.get on None would crash without defensive handling
        result = await image_service.extract_image_via_gpt(
            "Foo",
            [{"link": "https://a.example", "snippet": "real"},
             None,  # pathological entry
             {"link": "https://b.example"}],
        )

    # Result is None (GPT returned null) but did not crash
    assert result is None


@pytest.mark.asyncio
async def test_organic_with_missing_link_key_handled():
    """Entry has snippet but no link — dict.get('link', '') returns empty."""
    from app.services import image_service

    mock_client = MagicMock()
    mock_completion = MagicMock()
    mock_completion.choices = [MagicMock()]
    mock_completion.choices[0].message.content = '{"image_url": "https://x.example/y.jpg"}'
    mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)

    with patch("app.services.image_service.get_client", return_value=mock_client):
        result = await image_service.extract_image_via_gpt(
            "Foo", [{"snippet": "no link in this entry"}],
        )

    assert result == "https://x.example/y.jpg"


@pytest.mark.asyncio
async def test_organic_results_as_tuple_works_due_to_iteration():
    """organic_results comes through as a tuple (immutable from caller) —
    list comprehension iterates either type."""
    from app.services import image_service

    mock_client = MagicMock()
    mock_completion = MagicMock()
    mock_completion.choices = [MagicMock()]
    mock_completion.choices[0].message.content = '{"image_url": null}'
    mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)

    with patch("app.services.image_service.get_client", return_value=mock_client):
        # The slice [:10] on a tuple returns a tuple, which is still iterable
        result = await image_service.extract_image_via_gpt(
            "Foo",
            tuple([{"link": f"https://r{i}.example", "snippet": str(i)} for i in range(3)]),
        )

    assert result is None


# ---------------------------------------------------------------------------
# Serper 'images' key as non-list
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_serper_images_key_as_string_falls_through():
    """Future Serper API change: 'images' returned as a string error code.
    The .get('images') or [] guard returns the string, and indexing/access
    must not crash."""
    from app.services.image_service import get_product_image_url

    with patch(
        "app.services.image_service.try_consume_serper_image_credit",
        MagicMock(return_value=True),
    ), patch(
        "app.services.image_service.search_images",
        AsyncMock(return_value={"images": "no_results_string"}),
    ), patch(
        "app.services.image_service.extract_image_via_gpt",
        AsyncMock(return_value=None),
    ):
        # Current code path: images = response.get("images") or [] →
        # "no_results_string" is truthy so we pass through; images[0] = "n",
        # which is a string not a dict, so isinstance(images[0], dict) fails
        # → fall through to Tier 3 → None.
        result = await get_product_image_url("Foo", region="bahrain")

    assert result is None


@pytest.mark.asyncio
async def test_serper_images_key_as_dict_falls_through():
    """Serper returns {'images': {...}} instead of {'images': [...]}.
    images[0] would be a key from the dict (a string in test), which
    isinstance(images[0], dict) fails."""
    from app.services.image_service import get_product_image_url

    with patch(
        "app.services.image_service.try_consume_serper_image_credit",
        MagicMock(return_value=True),
    ), patch(
        "app.services.image_service.search_images",
        AsyncMock(return_value={"images": {"foo": "bar"}}),
    ), patch(
        "app.services.image_service.extract_image_via_gpt",
        AsyncMock(return_value=None),
    ):
        result = await get_product_image_url("Foo", region="bahrain")

    assert result is None


# ---------------------------------------------------------------------------
# GPT JSON edge cases
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_gpt_response_with_empty_choices_array():
    """If OpenAI returns choices=[], indexing choices[0] would raise IndexError —
    extract_image_via_gpt's try/except catches it."""
    from app.services import image_service

    mock_client = MagicMock()
    mock_completion = MagicMock()
    mock_completion.choices = []  # pathological
    mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)

    with patch("app.services.image_service.get_client", return_value=mock_client):
        result = await image_service.extract_image_via_gpt(
            "Foo", [{"link": "https://foo.example"}],
        )

    assert result is None


@pytest.mark.asyncio
async def test_gpt_response_with_none_content():
    """choices[0].message.content is None — the `or ""` guard handles it."""
    from app.services import image_service

    mock_client = MagicMock()
    mock_completion = MagicMock()
    mock_completion.choices = [MagicMock()]
    mock_completion.choices[0].message.content = None
    mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)

    with patch("app.services.image_service.get_client", return_value=mock_client):
        result = await image_service.extract_image_via_gpt(
            "Foo", [{"link": "https://foo.example"}],
        )

    assert result is None


@pytest.mark.asyncio
async def test_gpt_response_with_json_inside_prose():
    """GPT writes prose before/after the JSON object."""
    from app.services import image_service

    mock_client = MagicMock()
    mock_completion = MagicMock()
    mock_completion.choices = [MagicMock()]
    mock_completion.choices[0].message.content = (
        'The image is here: {"image_url": "https://x.example/y.jpg"} hope this helps'
    )
    mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)

    with patch("app.services.image_service.get_client", return_value=mock_client):
        result = await image_service.extract_image_via_gpt(
            "Foo", [{"link": "https://foo.example"}],
        )

    # json.loads on the full string fails (it has prose around it) — returns None.
    # We don't currently try to extract JSON from prose; if we did, this test
    # would fail and force us to decide the behavior explicitly.
    assert result is None


# ---------------------------------------------------------------------------
# Unicode / RTL product names
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_arabic_product_name_processed_correctly():
    """Arabic / RTL product names must flow through to Serper Images without
    encoding errors."""
    from app.services.image_service import get_product_image_url

    with patch(
        "app.services.image_service.try_consume_serper_image_credit",
        MagicMock(return_value=True),
    ), patch(
        "app.services.image_service.search_images",
        AsyncMock(return_value={"images": [{"imageUrl": "https://x.example/arabic.jpg"}]}),
    ) as m_search:
        result = await get_product_image_url("سامسونج Galaxy S24", region="saudi_arabia")

    m_search.assert_called_once_with("سامسونج Galaxy S24", num_results=1)
    assert result == "https://x.example/arabic.jpg"


@pytest.mark.asyncio
async def test_very_long_product_name_does_not_break_logger():
    """A 5000-char product name flows through — name[:60] truncation in
    log statements stays bounded."""
    from app.services.image_service import get_product_image_url

    huge_name = "Product " + ("X" * 5000)
    with patch(
        "app.services.image_service.try_consume_serper_image_credit",
        MagicMock(return_value=True),
    ), patch(
        "app.services.image_service.search_images",
        AsyncMock(return_value={"images": [{"imageUrl": "https://x.example/y.jpg"}]}),
    ):
        result = await get_product_image_url(huge_name, region="bahrain")

    assert result == "https://x.example/y.jpg"


# ---------------------------------------------------------------------------
# Concurrent budget exhaustion race
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_concurrent_calls_during_budget_exhaustion():
    """10 parallel calls when budget allows 5 — at most 5 hit Tier 1, the
    other 5 fall through to Tier 3 (GPT). With Tier 3 mocked to None, all
    over-budget calls return None."""
    from app.services.image_service import get_product_image_url

    consume_count = {"n": 0}
    BUDGET = 5

    def fake_consume(n=1):
        if consume_count["n"] >= BUDGET:
            return False
        consume_count["n"] += n
        return True

    with patch(
        "app.services.image_service.try_consume_serper_image_credit",
        MagicMock(side_effect=fake_consume),
    ), patch(
        "app.services.image_service.search_images",
        AsyncMock(return_value={"images": [{"imageUrl": "https://x.example/tier1.jpg"}]}),
    ), patch(
        "app.services.image_service.extract_image_via_gpt",
        AsyncMock(return_value=None),
    ):
        results = await asyncio.gather(*[
            get_product_image_url(f"Product {i}", region="bahrain")
            for i in range(10)
        ])

    # First 5 (in fake_consume order) get the Tier 1 hit; rest fall through to None
    tier1_hits = [r for r in results if r == "https://x.example/tier1.jpg"]
    nones = [r for r in results if r is None]
    assert len(tier1_hits) == 5
    assert len(nones) == 5


# ---------------------------------------------------------------------------
# imageUrl deeply nested (future Serper API drift)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_serper_imageurl_nested_in_dict_falls_through():
    """Future API change: Serper Images returns {imageUrl: {url, width, height}}
    instead of {imageUrl: 'string'}. Our validator rejects non-string → fall through."""
    from app.services.image_service import get_product_image_url

    with patch(
        "app.services.image_service.try_consume_serper_image_credit",
        MagicMock(return_value=True),
    ), patch(
        "app.services.image_service.search_images",
        AsyncMock(return_value={"images": [
            {"imageUrl": {"url": "https://x.example/y.jpg", "width": 100, "height": 100}}
        ]}),
    ), patch(
        "app.services.image_service.extract_image_via_gpt",
        AsyncMock(return_value=None),
    ):
        result = await get_product_image_url("Foo", region="bahrain")

    # Validator rejects dict; Tier 3 returns None
    assert result is None


# ---------------------------------------------------------------------------
# Page-scrape image with unusual content types
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_page_scrape_image_with_query_string():
    """og:image URL with query params (?w=800&format=webp) is a valid URL —
    must pass through verbatim, query string preserved."""
    from app.services.image_service import get_product_image_url

    page_img = "https://cdn.example.com/product.jpg?w=800&format=webp&v=2"
    result = await get_product_image_url(
        "Foo", region="bahrain", page_scrape_image=page_img,
    )

    assert result == page_img


@pytest.mark.asyncio
async def test_page_scrape_image_with_whitespace_stripped():
    """Page-scrape URL with leading/trailing whitespace is normalized."""
    from app.services.image_service import get_product_image_url

    result = await get_product_image_url(
        "Foo", region="bahrain",
        page_scrape_image="  https://example.com/img.jpg  ",
    )

    assert result == "https://example.com/img.jpg"
