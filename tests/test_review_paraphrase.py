"""Phase 5.1 Task #6 — review paraphrase (synthesized praise, no citations).

Per Ahmed's D4 directive (MANIFEST): reviews become a SYNTHESIZED praise line,
NON-verbatim, with NO citations / NO source domains / NO [N] markers. Ratings
real-only (never fabricated). Contract 2: `review_praise` (string|null) on each
product.

`build_review_praise(reviews)` synthesizes from the REAL review sentiment the
pipeline already has (review_summary.consensus + positive highlights), strips ALL
"Per <domain>:" attributions and [N]/[snippet_N] markers, and returns a praise
line — or None when there is insufficient real positive signal.
"""

import pytest

from app.services.review_service import build_review_praise


# --------------------------------------------------- synthesizes praise ---

class TestBuildReviewPraise:
    def test_synthesizes_from_consensus(self):
        reviews = {
            "review_summary": {
                "overall_sentiment": "positive",
                "consensus": "Tom Ford Tobacco Vanille is widely praised for its warm and inviting scent profile, combining rich tobacco and sweet vanilla notes.",
                "highlights": [
                    {"point": "Per tomfordbeauty.com: A warm, iconic blend of tobacco and vanilla.", "sentiment": "positive"},
                ],
            }
        }
        praise = build_review_praise(reviews)
        assert isinstance(praise, str)
        assert len(praise) > 0

    def test_strips_per_domain_prefix(self):
        reviews = {
            "review_summary": {
                "overall_sentiment": "positive",
                "consensus": "",
                "highlights": [
                    {"point": "Per fragrantica.com: A deeply textural scent with tactile sensuality.", "sentiment": "positive"},
                    {"point": "Per reddit.com: A bright leather opening that mellows beautifully.", "sentiment": "positive"},
                ],
            }
        }
        praise = build_review_praise(reviews)
        assert praise is not None
        assert "Per " not in praise
        assert "fragrantica" not in praise.lower()
        assert "reddit" not in praise.lower()
        assert ".com" not in praise

    def test_strips_bracket_markers(self):
        reviews = {
            "review_summary": {
                "overall_sentiment": "positive",
                "consensus": "Great scent [2] that lasts all day [snippet_3].",
                "highlights": [],
            }
        }
        praise = build_review_praise(reviews)
        assert praise is not None
        assert "[2]" not in praise
        assert "[snippet_3]" not in praise
        assert "[" not in praise

    def test_no_verbatim_copy_of_a_highlight(self):
        # The praise must not be a verbatim copy of a raw highlight point (it is
        # SYNTHESIZED). We assert the "Per domain:" raw form never appears
        # verbatim; the de-attributed clause may be reused but not the citation.
        raw = "Per boots.com: Smells amazing and lasts for hours."
        reviews = {
            "review_summary": {
                "overall_sentiment": "positive",
                "consensus": "",
                "highlights": [{"point": raw, "sentiment": "positive"}],
            }
        }
        praise = build_review_praise(reviews)
        assert praise is not None
        assert raw not in praise

    def test_praise_only_ignores_negative_highlights(self):
        reviews = {
            "review_summary": {
                "overall_sentiment": "mixed",
                "consensus": "",
                "highlights": [
                    {"point": "Per boots.com: Lasts only a few hours, disappointing.", "sentiment": "negative"},
                    {"point": "Per reddit.com: The leather opening is gorgeous and unique.", "sentiment": "positive"},
                ],
            }
        }
        praise = build_review_praise(reviews)
        assert praise is not None
        # The negative point's distinctive words should not drive the praise.
        assert "disappointing" not in praise.lower()


# ----------------------------------------------- None on weak/no signal ---

class TestNoneOnInsufficientSignal:
    def test_empty_reviews_none(self):
        assert build_review_praise({}) is None
        assert build_review_praise(None) is None

    def test_no_summary_none(self):
        assert build_review_praise({"foo": "bar"}) is None

    def test_no_consensus_no_positive_highlights_none(self):
        reviews = {
            "review_summary": {
                "overall_sentiment": "negative",
                "consensus": "",
                "highlights": [
                    {"point": "Per x.com: Too weak.", "sentiment": "negative"},
                ],
            }
        }
        assert build_review_praise(reviews) is None

    def test_blank_consensus_and_empty_highlights_none(self):
        reviews = {"review_summary": {"consensus": "", "highlights": []}}
        assert build_review_praise(reviews) is None


# -------------------------------------------------------- no fabrication ---

class TestNoFabrication:
    def test_does_not_invent_when_only_negative(self):
        # An all-negative product yields None — we never manufacture praise.
        reviews = {
            "review_summary": {
                "overall_sentiment": "negative",
                "consensus": "Most reviewers were disappointed with the longevity and value.",
                "highlights": [
                    {"point": "Per a.com: Faded in an hour.", "sentiment": "negative"},
                ],
            }
        }
        # consensus is present but NEGATIVE — build_review_praise must not present
        # a negative consensus as "praise".
        praise = build_review_praise(reviews)
        assert praise is None


# --------------------------------------- copy-policy compliance (#6 send-back) ---
# Contract 2 (Ahmed's D4): review_praise MUST pass the copy fence. Real snippets
# carry banned evaluative vocab ("best camera", "excellent battery", "beats every
# rival") — the praise line must NOT parrot them. We assert against the SAME
# .copy-policy.json banned/scary lists the FE fence uses (one source of truth).

import json as _json
import os as _os
import re as _re

_COPY_POLICY_PATH = _os.path.join(
    _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))),
    "SmartCompareApp", "src", "i18n", ".copy-policy.json",
)


def _banned_patterns():
    with open(_COPY_POLICY_PATH, encoding="utf-8") as f:
        cp = _json.load(f)
    pats = [b["pattern"] for b in cp.get("banned_en", [])]
    pats += [_re.escape(w) for w in cp.get("scary_vocab_en", [])]
    return [_re.compile(p, _re.IGNORECASE) for p in pats]


def _assert_policy_clean(text):
    assert text is not None
    for rx in _banned_patterns():
        assert not rx.search(text), f"review_praise '{text}' contains banned vocab /{rx.pattern}/"


class TestReviewPraiseCopyPolicy:
    def test_superlative_laden_highlights_scrubbed(self):
        # The exact send-back repro: best/excellent/beats in real snippets must
        # NOT leak into the praise line. The line is either policy-CLEAN or None
        # (Contract 2 allows null) — but NEVER a line carrying banned vocab.
        reviews = {
            "review_summary": {
                "overall_sentiment": "positive",
                "consensus": "",
                "highlights": [
                    {"point": "Per amazon.com: best camera in this price range and excellent battery.", "sentiment": "positive"},
                    {"point": "Per reddit.com: it beats every rival for value.", "sentiment": "positive"},
                ],
            }
        }
        praise = build_review_praise(reviews)
        if praise is not None:
            _assert_policy_clean(praise)

    def test_excellent_in_consensus_scrubbed(self):
        reviews = {
            "review_summary": {
                "overall_sentiment": "positive",
                "consensus": "An excellent scent that beats the competition; the best value around.",
                "highlights": [],
            }
        }
        praise = build_review_praise(reviews)
        # Either a clean line or None — never a line carrying banned vocab.
        if praise is not None:
            _assert_policy_clean(praise)

    def test_clean_praise_still_produced_when_clause_is_clean(self):
        # When a POSITIVE highlight is already clean (no banned vocab), a clean
        # aggregate line IS produced (we don't nuke clean signal) — neutral
        # aspect-aggregation, not a superlative echo.
        reviews = {
            "review_summary": {
                "overall_sentiment": "positive",
                "consensus": "",
                "highlights": [
                    {"point": "Per amazon.com: the battery comfortably lasts a full day of heavy use.", "sentiment": "positive"},
                    {"point": "Per reddit.com: the camera handles low light impressively well.", "sentiment": "positive"},
                ],
            }
        }
        praise = build_review_praise(reviews)
        assert praise is not None
        _assert_policy_clean(praise)
        low = praise.lower()
        assert "camera" in low or "battery" in low

    def test_all_categories_sample_clean(self):
        # A spread of category-flavored superlative snippets all come back clean.
        samples = [
            "Per x.com: best longevity and excellent projection.",          # fragrance
            "Per y.com: the best moisturizer, beats everything for dry skin.",  # skincare
            "Per z.com: excellent flavor, the best value snack.",           # grocery
        ]
        for snip in samples:
            reviews = {"review_summary": {"overall_sentiment": "positive", "consensus": "",
                                          "highlights": [{"point": snip, "sentiment": "positive"}]}}
            praise = build_review_praise(reviews)
            if praise is not None:
                _assert_policy_clean(praise)


# ----------------------------------------- response integration (Contract 2) ---

class TestReviewPraiseInResponse:
    def _pd(self, name, consensus, sentiment="positive", review_count=1000):
        return {
            "brand": "Tom Ford", "name": name,
            "price": {"amount": 100.0, "currency": "BHD", "source_method": "page_scrape_jsonld"},
            "specs": {"scent_family": "Amber"},
            "review_count": review_count,
            "reviews": {
                "review_summary": {
                    "overall_sentiment": sentiment,
                    "consensus": consensus,
                    "highlights": [
                        {"point": f"Per fragrantica.com: {consensus}", "sentiment": "positive"},
                    ],
                },
            },
        }

    def test_review_praise_and_rating_count_on_products(self):
        from app.services.response_builder import build_comparison_response
        product_data = [
            self._pd("Tobacco Vanille", "A warm, inviting tobacco and vanilla scent loved by many."),
            self._pd("Ombre Leather", "A unique leather profile with great projection."),
        ]
        comparison = {"winner_index": 0, "winner_declaration": "Tobacco Vanille",
                      "winner_reason": "x", "specs_comparison": {}}
        resp = build_comparison_response(
            query="Tobacco Vanille vs Ombre Leather",
            product_data=product_data, comparison=comparison,
            scoring_result={}, category_used="fragrances", region="bahrain",
            elapsed_seconds=1.0, api_calls=0, total_cost=0.0, gpt_calls=0, serper_calls=0,
        )
        for p in resp["products"]:
            assert "review_praise" in p
            assert isinstance(p["review_praise"], str) and len(p["review_praise"]) > 0
            # No citations / domains leaked into the praise.
            assert "Per " not in p["review_praise"]
            assert ".com" not in p["review_praise"]
            assert "rating_count" in p
            assert p["rating_count"] == 1000

    def test_review_praise_none_when_no_signal(self):
        from app.services.response_builder import build_comparison_response
        pd = {
            "brand": "X", "name": "Y",
            "price": {"amount": 100.0, "currency": "BHD", "source_method": "page_scrape_jsonld"},
            "specs": {}, "review_count": 0,
            "reviews": {"review_summary": {"overall_sentiment": "negative", "consensus": "", "highlights": []}},
        }
        comparison = {"winner_index": 0, "winner_declaration": "Y", "winner_reason": "x", "specs_comparison": {}}
        resp = build_comparison_response(
            query="Y vs Y2", product_data=[pd, dict(pd)], comparison=comparison,
            scoring_result={}, category_used="other", region="bahrain",
            elapsed_seconds=1.0, api_calls=0, total_cost=0.0, gpt_calls=0, serper_calls=0,
        )
        for p in resp["products"]:
            assert p["review_praise"] is None
