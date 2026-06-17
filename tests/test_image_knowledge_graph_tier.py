"""Walk-fix #21 — fragrance product images null.

On-device walk: fragrance cards show placeholders (products[i].image_url null on
a fresh nocache pull). The image_service cascade is:
  Tier 1.5 piggyback page-scrape image (FREE, but rides the price-scrape →
           ABSENT when the fragrance price PENDS), then
  Tier 1   Serper Images (paid, gated by the 500/day image budget), then
  Tier 3   GPT-from-organic.
So a fragrance null = no page-scrape image (price pended) + Serper Images missed
or budget-exhausted + GPT missed → placeholder.

Fix: add a FREE, price-scrape-INDEPENDENT, budget-FREE tier that reads an image
the pipeline ALREADY fetched — the unified Serper search's knowledgeGraph.imageUrl
(branded products like perfumes almost always have a Google Knowledge Graph card)
and, failing that, an organic result's own image field. This runs BEFORE the
budget-gated Serper-Images tier, so it neither depends on the price-scrape nor
burns the daily image budget. Real-URL-only (never fabricated); None on miss.
"""

import asyncio

import pytest

from app.services.image_service import (
    extract_image_from_search,
    get_product_image_url,
)


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ----------------------------------------- extract_image_from_search (pure) ---

class TestExtractImageFromSearch:
    def test_knowledge_graph_imageurl(self):
        search = {"knowledgeGraph": {"title": "Tom Ford Tobacco Vanille",
                                     "imageUrl": "https://img.example.com/tf.jpg"}}
        assert extract_image_from_search(search) == "https://img.example.com/tf.jpg"

    def test_knowledge_graph_snake_case_variant(self):
        # Tolerate the snake_case shape some Serper paths/normalizers use.
        search = {"knowledge_graph": {"imageUrl": "https://img.example.com/a.png"}}
        assert extract_image_from_search(search) == "https://img.example.com/a.png"

    def test_knowledge_graph_image_field_variant(self):
        search = {"knowledgeGraph": {"image": "https://img.example.com/b.jpg"}}
        assert extract_image_from_search(search) == "https://img.example.com/b.jpg"

    def test_falls_back_to_organic_image(self):
        # No KG image → use an organic result's own image field.
        search = {
            "knowledgeGraph": {"title": "x"},  # no image
            "organic": [
                {"link": "https://a.com", "snippet": "s"},  # no image
                {"link": "https://sephora.com/p", "imageUrl": "https://img.example.com/o.jpg"},
            ],
        }
        assert extract_image_from_search(search) == "https://img.example.com/o.jpg"

    def test_organic_thumbnail_variant(self):
        search = {"organic": [{"link": "https://x.com", "thumbnailUrl": "https://img.example.com/t.webp"}]}
        assert extract_image_from_search(search) == "https://img.example.com/t.webp"

    def test_invalid_url_rejected(self):
        search = {"knowledgeGraph": {"imageUrl": "not-a-url"}}
        assert extract_image_from_search(search) is None

    def test_none_on_no_image_anywhere(self):
        search = {"knowledgeGraph": {"title": "x"}, "organic": [{"link": "https://a.com"}]}
        assert extract_image_from_search(search) is None

    def test_none_safe_inputs(self):
        assert extract_image_from_search(None) is None
        assert extract_image_from_search({}) is None
        assert extract_image_from_search({"organic": "weird"}) is None  # drift-tolerant

    def test_never_fabricates(self):
        # Only returns a URL actually present in the data.
        out = extract_image_from_search({"knowledgeGraph": {"imageUrl": "https://real.com/x.jpg"}})
        assert out == "https://real.com/x.jpg"


# ----------------------------- cascade: free tier fires before paid Serper ---

class TestCascadeUsesFreeSearchImage:
    def test_kg_image_used_without_burning_serper_budget(self):
        # With NO page-scrape image (price pended) but a KG image in the search
        # payload, get_product_image_url returns it WITHOUT calling the paid
        # Serper-Images tier (budget untouched).
        from unittest.mock import patch, AsyncMock
        search = {"knowledgeGraph": {"imageUrl": "https://img.example.com/kg.jpg"},
                  "organic": [{"link": "https://x.com", "snippet": "s"}]}
        with patch("app.services.image_service.try_consume_serper_image_credit") as m_budget, \
             patch("app.services.image_service.search_images", new=AsyncMock(return_value={})) as m_serper:
            url = _run(get_product_image_url(
                "Tom Ford Tobacco Vanille",
                page_scrape_image=None,           # price pended → no piggyback
                organic_results=search["organic"],
                search_payload=search,            # NEW: the unified search payload
            ))
        assert url == "https://img.example.com/kg.jpg"
        m_budget.assert_not_called()   # free tier short-circuited before paid Serper
        m_serper.assert_not_called()

    def test_piggyback_still_wins_over_search_image(self):
        # A real page-scrape image (Tier 1.5) still takes precedence (higher
        # fidelity) over the KG image.
        search = {"knowledgeGraph": {"imageUrl": "https://img.example.com/kg.jpg"}}
        url = _run(get_product_image_url(
            "Tom Ford Tobacco Vanille",
            page_scrape_image="https://page.example.com/hero.jpg",
            organic_results=None,
            search_payload=search,
        ))
        assert url == "https://page.example.com/hero.jpg"

    def test_falls_through_to_paid_when_no_free_image(self):
        # No page-scrape, no KG/organic image → the paid Serper tier still runs
        # (backward-compatible). Mock it to return a hit.
        from unittest.mock import patch, AsyncMock
        with patch("app.services.image_service.try_consume_serper_image_credit", return_value=True), \
             patch("app.services.image_service.search_images",
                   new=AsyncMock(return_value={"images": [{"imageUrl": "https://serper.example.com/s.jpg"}]})):
            url = _run(get_product_image_url(
                "Sony WH-1000XM5",
                page_scrape_image=None,
                organic_results=[{"link": "https://x.com"}],
                search_payload={"organic": [{"link": "https://x.com"}]},  # no image
            ))
        assert url == "https://serper.example.com/s.jpg"

    def test_backward_compat_without_search_payload(self):
        # Old call sites that don't pass search_payload still work (None default).
        url = _run(get_product_image_url(
            "X", page_scrape_image="https://page.example.com/h.jpg",
        ))
        assert url == "https://page.example.com/h.jpg"
