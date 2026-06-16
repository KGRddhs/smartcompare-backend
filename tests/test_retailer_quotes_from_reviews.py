"""ITEM 1 — retailer_quotes built from REAL review material (esp. fragrances).

The FE Reviews accordion renders `reviews.products[i].retailer_quotes`
(`{retailer, text, rating?}`) as compact per-source lines. For fragrances the
backend previously emitted only `review_summary.{consensus,highlights}`, so the
FE fell back instead of showing the designed `AMAZON ★★★★★ "quote"` lines.

`build_retailer_quotes_from_reviews(reviews, search_results)` surfaces up to 3
cleaned review snippets WITH their mapped source domain — drawn from the SAME
organic Serper material the review pipeline already has (zero extra API calls):
  - `retailer` = the real source domain the snippet came from (snippet_source_map).
  - `text`     = the real organic snippet text (NOT a synthesized sentence).
  - `rating`   = OMITTED (never fabricated; ratings are never AI-generated). Only
                 present if a real numeric rating for that source is available.

Run: pytest tests/test_retailer_quotes_from_reviews.py -v
"""
import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

import pytest

from app.services.review_service import build_retailer_quotes_from_reviews


def _organic(domain: str, snippet: str, **extra) -> dict:
    base = {"link": f"https://www.{domain}/x", "snippet": snippet, "title": "t"}
    base.update(extra)
    return base


# A realistic FRAGRANCE review payload: review_summary with highlights that cite
# [snippet_N], over a set of organic search results that carry the real text.
FRAGRANCE_SEARCH = [
    _organic("fragrantica.com", "Ombre Leather opens with a smoky leather accord that lasts all day on skin."),
    _organic("basenotes.net", "Projection is moderate but the longevity is excellent, easily 8+ hours."),
    _organic("amazon.com", "Authentic bottle, fast shipping, the scent is rich and warm for autumn."),
    _organic("reddit.com", "A bit too sweet for me but my partner loves it; great sillage in cold weather."),
]

FRAGRANCE_REVIEWS = {
    "average_rating": None,
    "review_summary": {
        "overall_sentiment": "positive",
        "consensus": "Reviewers praise a smoky leather scent with strong longevity.",
        "highlights": [
            {"point": "[snippet_1] Smoky leather accord that lasts all day", "sentiment": "positive"},
            {"point": "[snippet_2] Excellent longevity, 8+ hours", "sentiment": "positive"},
            {"point": "[snippet_3] Authentic and warm for autumn", "sentiment": "positive"},
            {"point": "[snippet_4] A touch sweet but great sillage", "sentiment": "negative"},
        ],
        "review_volume": "moderate",
        "agreement_level": "moderate",
    },
}


class TestRetailerQuotesPopulated:
    def test_fragrance_emits_quotes(self):
        quotes = build_retailer_quotes_from_reviews(FRAGRANCE_REVIEWS, FRAGRANCE_SEARCH)
        assert isinstance(quotes, list)
        assert 1 <= len(quotes) <= 3  # capped at 3

    def test_cap_at_three(self):
        quotes = build_retailer_quotes_from_reviews(FRAGRANCE_REVIEWS, FRAGRANCE_SEARCH)
        assert len(quotes) <= 3

    def test_retailer_is_real_source_domain(self):
        quotes = build_retailer_quotes_from_reviews(FRAGRANCE_REVIEWS, FRAGRANCE_SEARCH)
        domains = {q["retailer"] for q in quotes}
        # Every retailer is one of the real organic domains (not fabricated).
        assert domains.issubset(
            {"fragrantica.com", "basenotes.net", "amazon.com", "reddit.com"}
        )
        for q in quotes:
            assert q["retailer"]  # non-empty

    def test_text_is_real_snippet_not_synthesized(self):
        quotes = build_retailer_quotes_from_reviews(FRAGRANCE_REVIEWS, FRAGRANCE_SEARCH)
        real_snippets = {o["snippet"] for o in FRAGRANCE_SEARCH}
        for q in quotes:
            assert isinstance(q["text"], str) and q["text"]
            # text MUST be a verbatim real organic snippet — NOT the GPT-
            # synthesized highlight "point".
            assert q["text"] in real_snippets

    def test_no_fabricated_rating(self):
        quotes = build_retailer_quotes_from_reviews(FRAGRANCE_REVIEWS, FRAGRANCE_SEARCH)
        for q in quotes:
            # rating is NEVER fabricated — when no real numeric rating exists for
            # the source, the key is OMITTED entirely (FE renders no stars).
            assert "rating" not in q

    def test_quote_shape_keys(self):
        quotes = build_retailer_quotes_from_reviews(FRAGRANCE_REVIEWS, FRAGRANCE_SEARCH)
        for q in quotes:
            assert set(q.keys()) <= {"retailer", "text", "rating"}
            assert "retailer" in q and "text" in q

    def test_dedupes_by_source_domain(self):
        # Two highlights citing snippets that share the SAME domain → only one
        # quote per domain (no duplicate AMAZON lines).
        search = [
            _organic("amazon.com", "First amazon review snippet about the leather scent quality."),
            _organic("amazon.com", "Second amazon review snippet that is different but same site."),
        ]
        reviews = {
            "review_summary": {
                "highlights": [
                    {"point": "[snippet_1] foo", "sentiment": "positive"},
                    {"point": "[snippet_2] bar", "sentiment": "positive"},
                ],
            }
        }
        quotes = build_retailer_quotes_from_reviews(reviews, search)
        retailers = [q["retailer"] for q in quotes]
        assert len(retailers) == len(set(retailers))  # no dup domains


class TestRetailerQuotesGraceful:
    def test_no_highlights_returns_empty(self):
        assert build_retailer_quotes_from_reviews({"review_summary": {}}, FRAGRANCE_SEARCH) == []

    def test_no_search_results_returns_empty(self):
        assert build_retailer_quotes_from_reviews(FRAGRANCE_REVIEWS, []) == []

    def test_none_inputs_safe(self):
        assert build_retailer_quotes_from_reviews(None, None) == []
        assert build_retailer_quotes_from_reviews({}, None) == []

    def test_bare_numeric_citation_also_mapped(self):
        # Highlights sometimes cite by bare [N] rather than [snippet_N].
        reviews = {
            "review_summary": {
                "highlights": [
                    {"point": "Lasts all day [2]", "sentiment": "positive"},
                ],
            }
        }
        quotes = build_retailer_quotes_from_reviews(reviews, FRAGRANCE_SEARCH)
        assert len(quotes) == 1
        assert quotes[0]["retailer"] == "basenotes.net"  # snippet 2 → basenotes
        assert quotes[0]["text"] == FRAGRANCE_SEARCH[1]["snippet"]

    def test_uncited_highlight_skipped(self):
        # A highlight with NO citation cannot be source-attributed → skipped
        # (we never invent a retailer for an uncited claim).
        reviews = {
            "review_summary": {
                "highlights": [
                    {"point": "Great scent overall", "sentiment": "positive"},
                ],
            }
        }
        assert build_retailer_quotes_from_reviews(reviews, FRAGRANCE_SEARCH) == []

    def test_short_snippet_skipped(self):
        # Snippet too short to be a meaningful quote → skipped.
        search = [_organic("amazon.com", "Nice.")]
        reviews = {"review_summary": {"highlights": [{"point": "[snippet_1] x"}]}}
        assert build_retailer_quotes_from_reviews(reviews, search) == []

    def test_real_rating_preserved_when_present(self):
        # If a snippet carries a REAL numeric rating (from the source data), it
        # IS surfaced — that is NOT fabrication, it's a real value.
        search = [
            _organic(
                "amazon.com",
                "Excellent leather fragrance with great longevity and projection.",
                rating=4.5,
            )
        ]
        reviews = {"review_summary": {"highlights": [{"point": "[snippet_1] great"}]}}
        quotes = build_retailer_quotes_from_reviews(reviews, search)
        assert len(quotes) == 1
        assert quotes[0].get("rating") == 4.5

    def test_richsnippet_rating_preserved(self):
        # Serper richSnippet rating (same shape fetch_retailer_quotes reads) is a
        # REAL rating → surfaced.
        search = [
            _organic(
                "amazon.com",
                "Authentic and long lasting, a great autumn leather scent overall.",
                richSnippet={"top": {"detected_extensions": {"rating": 5}}},
            )
        ]
        reviews = {"review_summary": {"highlights": [{"point": "[snippet_1] great"}]}}
        quotes = build_retailer_quotes_from_reviews(reviews, search)
        assert len(quotes) == 1
        assert quotes[0].get("rating") == 5.0
