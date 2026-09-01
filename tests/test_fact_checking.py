"""Tests for fact-checking logic: spec citation verification, shopping cross-validation,
review sentiment cross-check, price verification, and overall fact_check assembly.

All mocked — these test the verification logic with constructed data.
Run: python -m pytest tests/test_fact_checking.py -v
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from app.services.structured_comparison_service import StructuredComparisonService
from app.services.extraction_service import _normalize_review_response


@pytest.fixture
def service():
    return StructuredComparisonService()


# =====================================================
# Review summary normalization (_normalize_review_response)
# =====================================================

class TestNormalizeReviewResponseSummary:
    def test_review_summary_defaults_when_missing(self):
        """Missing review_summary gets populated with defaults."""
        data = {"average_rating": 4.0}
        result = _normalize_review_response(data)
        assert result["review_summary"]["overall_sentiment"] == "mixed"
        assert result["review_summary"]["consensus"] == ""
        assert result["review_summary"]["highlights"] == []
        assert result["review_summary"]["review_volume"] == "minimal"
        assert result["review_summary"]["agreement_level"] == "moderate"

    def test_review_summary_preserves_existing(self):
        """Existing review_summary fields are preserved."""
        data = {
            "review_summary": {
                "overall_sentiment": "positive",
                "consensus": "Great product.",
                "highlights": [{"point": "Fast", "sentiment": "positive"}],
                "review_volume": "high",
                "agreement_level": "strong",
            },
        }
        result = _normalize_review_response(data)
        assert result["review_summary"]["overall_sentiment"] == "positive"
        assert result["review_summary"]["consensus"] == "Great product."
        assert len(result["review_summary"]["highlights"]) == 1

    def test_backward_compat_common_praises_from_highlights(self):
        """common_praises populated from positive highlights for backward compat."""
        data = {
            "review_summary": {
                "highlights": [
                    {"point": "Great camera quality", "sentiment": "positive"},
                    {"point": "Poor battery", "sentiment": "negative"},
                ],
            },
        }
        result = _normalize_review_response(data)
        assert len(result["common_praises"]) == 1
        assert "camera" in result["common_praises"][0]
        assert len(result["common_complaints"]) == 1
        assert "battery" in result["common_complaints"][0]

    def test_empty_review_summary(self):
        """Empty review_summary dict gets populated with defaults."""
        data = {"review_summary": {}}
        result = _normalize_review_response(data)
        assert result["review_summary"]["overall_sentiment"] == "mixed"
        assert result["review_summary"]["highlights"] == []


# =====================================================
# Spec citation verification (_verify_spec_citations)
# =====================================================

class TestVerifySpecCitations:
    def test_verified_citation_matches_snippet(self, service):
        """snippet text contains spec value terms -> 'verified'."""
        specs = {
            "battery": "4422 mAh",
            "battery_source": "snippet_1",
        }
        snippets = ["The iPhone 16 Pro features a 4422 mAh battery capacity."]
        result = service._verify_spec_citations(specs, snippets)
        assert result["battery"] == "verified"

    def test_unverified_when_no_citation(self, service):
        """No _source field -> 'unverified'."""
        specs = {
            "battery": "4422 mAh",
            # no battery_source
        }
        snippets = ["Some snippet text."]
        result = service._verify_spec_citations(specs, snippets)
        assert result["battery"] == "unverified"

    def test_unverified_when_training_source(self, service):
        """Source is 'training' -> 'unverified'."""
        specs = {
            "battery": "4422 mAh",
            "battery_source": "training",
        }
        snippets = ["The battery is 4422 mAh."]
        result = service._verify_spec_citations(specs, snippets)
        assert result["battery"] == "unverified"

    def test_likely_when_partial_match(self, service):
        """Some terms match snippet but not enough for 'verified' -> 'likely'."""
        specs = {
            "processor": "Apple A18 Pro Bionic chip",
            "processor_source": "snippet_1",
        }
        # Snippet has "Apple" and "Pro" but not "A18" or "Bionic" or "chip"
        snippets = ["Apple unveils new Pro lineup with improved performance and efficiency."]
        result = service._verify_spec_citations(specs, snippets)
        assert result["processor"] == "likely"

    def test_unverified_when_snippet_index_out_of_range(self, service):
        """Snippet index beyond list length -> 'unverified'."""
        specs = {
            "storage": "256GB",
            "storage_source": "snippet_10",
        }
        snippets = ["Only one snippet here."]
        result = service._verify_spec_citations(specs, snippets)
        assert result["storage"] == "unverified"

    def test_skips_meta_keys(self, service):
        """brand, model, variant, category are skipped."""
        specs = {
            "brand": "Apple",
            "model": "iPhone 16",
            "category": "electronics",
            "battery": "4422 mAh",
            "battery_source": "training",
        }
        snippets = []
        result = service._verify_spec_citations(specs, snippets)
        assert "brand" not in result
        assert "model" not in result
        assert "category" not in result
        assert "battery" in result

    # =====================================================
    # Issue #108 — unit-aware citation rubric with a reachable
    # "flagged" outcome (ENABLE_CITATION_RUBRIC_V2, default OFF)
    # =====================================================

    FLAG = "ENABLE_CITATION_RUBRIC_V2"

    def test_unit_mismatch_is_not_verified(self, service, monkeypatch):
        """A cited value whose UNIT disagrees with the snippet must not verify.

        Today only the bare digits are compared ("128" in snippet), so a
        fabricated 128 TB verifies against a 128 GB snippet.
        """
        monkeypatch.setenv(self.FLAG, "true")
        specs = {"storage": "128 TB", "storage_source": "snippet_1"}
        snippets = ["Ships with 128 GB of storage."]
        result = service._verify_spec_citations(specs, snippets)
        assert result["storage"] != "verified"

    def test_contradicted_numeric_value_is_flagged(self, service, monkeypatch):
        """A cited value contradicted by a same-unit number in its OWN cited
        snippet must come back 'flagged' — the outcome that today is counted
        in build_fact_check and weighted 0.0 in _score_reliability but is
        produced nowhere."""
        monkeypatch.setenv(self.FLAG, "true")
        specs = {"battery": "5000 mAh", "battery_source": "snippet_1"}
        snippets = ["The handset packs a 3582 mAh battery."]
        result = service._verify_spec_citations(specs, snippets)
        assert result["battery"] == "flagged"

    def test_numeric_field_citing_number_free_snippet_is_unverified(self, service, monkeypatch):
        """A numeric field citing a snippet with NO comparable number is not
        evidence — it must land on 'unverified' (0.3), not 'likely' (0.7),
        so a fabricated citation cannot outscore an honest 'training'."""
        monkeypatch.setenv(self.FLAG, "true")
        specs = {"battery": "5000 mAh", "battery_source": "snippet_1"}
        snippets = ["All-day battery life with fast charging."]
        result = service._verify_spec_citations(specs, snippets)
        assert result["battery"] == "unverified"

    def test_thousands_separator_matches_both_directions(self, service, monkeypatch):
        """'5,000' and '5000' must match each other in BOTH directions."""
        monkeypatch.setenv(self.FLAG, "true")
        r1 = service._verify_spec_citations(
            {"battery": "5000 mAh", "battery_source": "snippet_1"},
            ["5,000 mAh battery"],
        )
        assert r1["battery"] == "verified"
        r2 = service._verify_spec_citations(
            {"battery": "5,000 mAh", "battery_source": "snippet_1"},
            ["5000 mAh battery"],
        )
        assert r2["battery"] == "verified"

    def test_spaced_and_glued_unit_spellings_are_equal(self, service, monkeypatch):
        """'128 GB' and '128GB' must be the same token on both sides."""
        monkeypatch.setenv(self.FLAG, "true")
        r1 = service._verify_spec_citations(
            {"storage": "128 GB", "storage_source": "snippet_1"},
            ["128GB model"],
        )
        assert r1["storage"] == "verified"
        r2 = service._verify_spec_citations(
            {"storage": "128GB", "storage_source": "snippet_1"},
            ["128 GB model"],
        )
        assert r2["storage"] == "verified"

    def test_flag_off_reproduces_all_four_defects(self, service, monkeypatch):
        """Flag unset -> today's exact values for cases 1, 2, 4 and 6.

        This is the per-function flag-OFF identity pin required by the issue's
        gates (scripts/verify_flag_byte_identity.py does not cover this module).
        """
        monkeypatch.delenv(self.FLAG, raising=False)
        # Case 1: unit swap verifies (defect a)
        r1 = service._verify_spec_citations(
            {"storage": "128 TB", "storage_source": "snippet_1"},
            ["Ships with 128 GB of storage."],
        )
        assert r1["storage"] == "verified"
        # Case 2: contradiction earns 'likely' (defect b)
        r2 = service._verify_spec_citations(
            {"battery": "5000 mAh", "battery_source": "snippet_1"},
            ["The handset packs a 3582 mAh battery."],
        )
        assert r2["battery"] == "likely"
        # Case 4: separator spelling fails to verify (defect d)
        r4 = service._verify_spec_citations(
            {"battery": "5000 mAh", "battery_source": "snippet_1"},
            ["5,000 mAh battery"],
        )
        assert r4["battery"] == "likely"
        # Case 6: model-number digit upgrades ram to verified (defect c)
        r6 = service._cross_validate_specs_with_shopping(
            {"ram": "16 GB", "brand": "Apple"},
            [{"title": "Apple iPhone 16 128GB Black", "description": ""}],
            "Apple iPhone 16",
        )
        assert r6.get("ram") == "verified"


# =====================================================
# Spec shopping cross-validation (_cross_validate_specs_with_shopping)
# =====================================================

class TestCrossValidateSpecsWithShopping:
    def test_shopping_confirms_storage_spec(self, service):
        """'128GB' in shopping title confirms storage spec."""
        specs = {"storage": "128GB"}
        shopping_items = [
            {"title": "Samsung Galaxy S24 128GB Phantom Black", "description": ""},
        ]
        result = service._cross_validate_specs_with_shopping(specs, shopping_items)
        assert result.get("storage") == "verified"

    def test_no_shopping_returns_empty(self, service):
        """Empty shopping_items -> empty dict."""
        specs = {"storage": "128GB"}
        result = service._cross_validate_specs_with_shopping(specs, [])
        assert result == {}

    def test_numbers_in_shopping_titles(self, service):
        """Numeric cross-check works for multiple specs."""
        specs = {"storage": "256GB", "ram": "8GB"}
        shopping_items = [
            {"title": "iPhone 16 Pro 256GB 8GB RAM", "description": ""},
        ]
        result = service._cross_validate_specs_with_shopping(specs, shopping_items)
        assert result.get("storage") == "verified"

    def test_na_value_skipped(self, service):
        """Spec value 'N/A' is skipped."""
        specs = {"storage": "N/A"}
        shopping_items = [
            {"title": "Some product 256GB", "description": ""},
        ]
        result = service._cross_validate_specs_with_shopping(specs, shopping_items)
        assert "storage" not in result

    def test_non_checkable_field_ignored(self, service):
        """Fields not in checkable list are not cross-validated."""
        specs = {"color": "Black"}
        shopping_items = [
            {"title": "Product in Black color", "description": ""},
        ]
        result = service._cross_validate_specs_with_shopping(specs, shopping_items)
        assert "color" not in result

    # =====================================================
    # Issue #108 — identity fence on the shopping cross-validation
    # (ENABLE_CITATION_RUBRIC_V2, default OFF)
    # =====================================================

    FLAG = "ENABLE_CITATION_RUBRIC_V2"

    def test_shopping_crossval_ignores_model_number_digit(self, service, monkeypatch):
        """A digit that is part of the product's own name ('iPhone 16') must
        not upgrade a fabricated ram spec ('16 GB') to verified."""
        monkeypatch.setenv(self.FLAG, "true")
        specs = {"ram": "16 GB", "brand": "Apple"}
        shopping_items = [{"title": "Apple iPhone 16 128GB Black", "description": ""}]
        result = service._cross_validate_specs_with_shopping(
            specs, shopping_items, "Apple iPhone 16"
        )
        assert result.get("ram") != "verified"

    def test_shopping_crossval_still_upgrades_genuine_match(self, service, monkeypatch):
        """A genuine unit-adjacent occurrence ('16GB RAM') still verifies —
        pins that the identity fence did not over-reject."""
        monkeypatch.setenv(self.FLAG, "true")
        specs = {"ram": "16 GB", "brand": "Apple"}
        shopping_items = [{"title": "Apple iPhone 16 16GB RAM 128GB Black", "description": ""}]
        result = service._cross_validate_specs_with_shopping(
            specs, shopping_items, "Apple iPhone 16"
        )
        assert result.get("ram") == "verified"


# =====================================================
# Review sentiment verification (_verify_review_sentiment)
# =====================================================

class TestVerifyReviewSentiment:
    def test_consistent_when_ratings_close(self, service):
        """GPT 4.5 vs Serper 4.3 -> consistent (within 0.8 tolerance)."""
        reviews = {"average_rating": 4.5}
        source_ratings = [
            {"rating": 4.3, "review_count": 500},
            {"rating": 4.4, "review_count": 300},
        ]
        result = service._verify_review_sentiment(reviews, source_ratings)
        assert result["sentiment_consistent"] is True
        assert result["gpt_rating"] == 4.5
        assert result["serper_avg_rating"] is not None
        assert result["deviation"] is not None
        assert result["deviation"] <= 0.8

    def test_inconsistent_when_ratings_diverge(self, service):
        """GPT 4.8 vs Serper 3.2 -> inconsistent."""
        reviews = {"average_rating": 4.8}
        source_ratings = [
            {"rating": 3.2, "review_count": 1000},
        ]
        result = service._verify_review_sentiment(reviews, source_ratings)
        assert result["sentiment_consistent"] is False
        assert result["deviation"] > 0.8

    def test_none_when_no_source_ratings(self, service):
        """No source_ratings -> sentiment_consistent is None."""
        reviews = {"average_rating": 4.5}
        result = service._verify_review_sentiment(reviews, [])
        assert result["sentiment_consistent"] is None

    def test_none_when_gpt_rating_missing(self, service):
        """No GPT average_rating -> sentiment_consistent is None."""
        reviews = {}
        source_ratings = [{"rating": 4.3, "review_count": 500}]
        result = service._verify_review_sentiment(reviews, source_ratings)
        assert result["sentiment_consistent"] is None
        assert result["gpt_rating"] is None

    def test_weighted_average_calculation(self, service):
        """Serper average should be weighted by review_count."""
        reviews = {"average_rating": 4.0}
        source_ratings = [
            {"rating": 4.0, "review_count": 900},   # 90% weight
            {"rating": 5.0, "review_count": 100},    # 10% weight
        ]
        result = service._verify_review_sentiment(reviews, source_ratings)
        # Weighted avg: (4.0*900 + 5.0*100) / 1000 = 4.1
        assert result["serper_avg_rating"] == pytest.approx(4.1, abs=0.01)

    def test_non_numeric_ratings_skipped(self, service):
        """Source ratings with non-numeric rating values are ignored."""
        reviews = {"average_rating": 4.0}
        source_ratings = [
            {"rating": "N/A", "review_count": 500},
            {"rating": 4.0, "review_count": 200},
        ]
        result = service._verify_review_sentiment(reviews, source_ratings)
        assert result["sentiment_consistent"] is True
        assert result["serper_avg_rating"] == 4.0

    def test_none_review_count_defaults_to_one(self, service):
        """review_count of None defaults to weight of 1."""
        reviews = {"average_rating": 4.0}
        source_ratings = [
            {"rating": 4.0, "review_count": None},
            {"rating": 4.2, "review_count": None},
        ]
        result = service._verify_review_sentiment(reviews, source_ratings)
        # Weighted avg: (4.0*1 + 4.2*1) / 2 = 4.1
        assert result["serper_avg_rating"] == pytest.approx(4.1, abs=0.01)
        assert result["sentiment_consistent"] is True

    def test_exact_boundary_0_8_is_consistent(self, service):
        """Deviation of exactly 0.8 is within tolerance -> consistent."""
        reviews = {"average_rating": 4.8}
        source_ratings = [
            {"rating": 4.0, "review_count": 1000},
        ]
        result = service._verify_review_sentiment(reviews, source_ratings)
        assert result["deviation"] == 0.8
        assert result["sentiment_consistent"] is True

    def test_single_source_rating(self, service):
        """Single source_rating works correctly."""
        reviews = {"average_rating": 4.5}
        source_ratings = [
            {"rating": 4.3, "review_count": 5000},
        ]
        result = service._verify_review_sentiment(reviews, source_ratings)
        assert result["serper_avg_rating"] == 4.3
        assert result["deviation"] == 0.2
        assert result["sentiment_consistent"] is True

    def test_all_ratings_non_numeric_returns_none(self, service):
        """If all source ratings are non-numeric, sentiment_consistent is None."""
        reviews = {"average_rating": 4.0}
        source_ratings = [
            {"rating": "N/A", "review_count": 500},
            {"rating": None, "review_count": 200},
        ]
        result = service._verify_review_sentiment(reviews, source_ratings)
        assert result["sentiment_consistent"] is None
        assert result["serper_avg_rating"] is None

    def test_zero_review_count_defaults_to_one(self, service):
        """review_count of 0 defaults to weight of 1 (0 is falsy)."""
        reviews = {"average_rating": 4.5}
        source_ratings = [
            {"rating": 4.0, "review_count": 0},
        ]
        result = service._verify_review_sentiment(reviews, source_ratings)
        assert result["serper_avg_rating"] == 4.0
        assert result["deviation"] == 0.5
        assert result["sentiment_consistent"] is True


# =====================================================
# Price verification (_verify_price)
# =====================================================

class TestVerifyPrice:
    def test_verified_when_within_30pct(self, service):
        """Price within 30% of median -> verified."""
        price = {"amount": 110, "currency": "BHD", "estimated": False}
        shopping_items = [
            {"price": 95},
            {"price": 105},
            {"price": 100},
        ]
        result = service._verify_price(price, shopping_items)
        assert result["price_verified"] is True
        assert result["deviation_pct"] is not None
        assert result["deviation_pct"] <= 30
        assert result["source_count"] == 3

    def test_not_verified_when_estimated(self, service):
        """Estimated price -> not verified even if within range."""
        price = {"amount": 100, "currency": "BHD", "estimated": True}
        shopping_items = [
            {"price": 100},
            {"price": 105},
        ]
        result = service._verify_price(price, shopping_items)
        assert result["price_verified"] is False

    def test_not_verified_when_deviation_high(self, service):
        """50% deviation -> not verified."""
        price = {"amount": 150, "currency": "BHD", "estimated": False}
        shopping_items = [
            {"price": 90},
            {"price": 100},
            {"price": 110},
        ]
        result = service._verify_price(price, shopping_items)
        assert result["price_verified"] is False
        assert result["deviation_pct"] > 30

    def test_no_price_returns_not_verified(self, service):
        """No price dict -> not verified."""
        result = service._verify_price(None, [{"price": 100}])
        assert result["price_verified"] is False

    def test_no_shopping_items(self, service):
        """No shopping items -> verified only if not estimated."""
        price = {"amount": 100, "currency": "BHD", "estimated": False}
        result = service._verify_price(price, [])
        assert result["price_verified"] is True  # not estimated, just no cross-check data
        assert result["source_count"] == 0

    def test_string_prices_parsed(self, service):
        """Shopping items with string prices (e.g. '$99.99') are parsed."""
        price = {"amount": 100, "currency": "BHD", "estimated": False}
        shopping_items = [
            {"price": "$95.00"},
            {"price": "$105.00"},
            {"price": "$100.00"},
        ]
        result = service._verify_price(price, shopping_items)
        assert result["source_count"] == 3
        assert result["price_verified"] is True

    def test_price_amount_zero(self, service):
        """Price amount of 0 -> not verified."""
        price = {"amount": 0, "currency": "BHD", "estimated": False}
        shopping_items = [{"price": 100}]
        result = service._verify_price(price, shopping_items)
        assert result["price_verified"] is False

    def test_price_amount_none(self, service):
        """Price amount of None -> not verified."""
        price = {"amount": None, "currency": "BHD", "estimated": False}
        shopping_items = [{"price": 100}]
        result = service._verify_price(price, shopping_items)
        assert result["price_verified"] is False

    def test_all_invalid_shopping_prices(self, service):
        """All shopping items have invalid prices -> no cross-check."""
        price = {"amount": 100, "currency": "BHD", "estimated": False}
        shopping_items = [
            {"price": "N/A"},
            {"price": ""},
            {"price": None},
        ]
        result = service._verify_price(price, shopping_items)
        assert result["price_verified"] is True  # not estimated, just no valid prices to compare
        assert result["source_count"] == 0
        assert result["deviation_pct"] is None

    def test_comma_separated_string_prices(self, service):
        """String prices with commas like '1,299.99' are parsed correctly."""
        price = {"amount": 1300, "currency": "BHD", "estimated": False}
        shopping_items = [
            {"price": "1,299.99"},
            {"price": "1,350.00"},
        ]
        result = service._verify_price(price, shopping_items)
        assert result["source_count"] == 2
        # Median is 1299.99 (sorted: [1299.99, 1350.0], middle index = 1 -> 1350.0)
        # Actually median of 2 items: sorted[1] = 1350.0 (integer division: 2//2 = 1)
        assert result["deviation_pct"] is not None

    def test_single_shopping_item(self, service):
        """Single shopping item: median = that item."""
        price = {"amount": 100, "currency": "BHD", "estimated": False}
        shopping_items = [{"price": 100}]
        result = service._verify_price(price, shopping_items)
        assert result["price_verified"] is True
        assert result["deviation_pct"] == 0.0
        assert result["source_count"] == 1

    def test_empty_price_dict(self, service):
        """Empty dict (no amount key) -> not verified."""
        price = {"currency": "BHD"}
        shopping_items = [{"price": 100}]
        result = service._verify_price(price, shopping_items)
        assert result["price_verified"] is False

    def test_boundary_exactly_30_pct(self, service):
        """Deviation of exactly 30% is within threshold -> verified."""
        price = {"amount": 130, "currency": "BHD", "estimated": False}
        shopping_items = [{"price": 100}]
        result = service._verify_price(price, shopping_items)
        assert result["deviation_pct"] == 30.0
        assert result["price_verified"] is True

    def test_just_over_30_pct(self, service):
        """Deviation of 31% is above threshold -> not verified."""
        price = {"amount": 131, "currency": "BHD", "estimated": False}
        shopping_items = [{"price": 100}]
        result = service._verify_price(price, shopping_items)
        assert result["deviation_pct"] == 31.0
        assert result["price_verified"] is False

    def test_negative_prices_excluded(self, service):
        """Negative shopping prices are filtered out."""
        price = {"amount": 100, "currency": "BHD", "estimated": False}
        shopping_items = [
            {"price": -50},
            {"price": 100},
        ]
        result = service._verify_price(price, shopping_items)
        assert result["source_count"] == 1
        assert result["price_verified"] is True

    # =====================================================
    # Issue #106 — currency normalization before the cross-check
    # (ENABLE_FACTCHECK_CURRENCY_NORMALIZATION, default OFF)
    # =====================================================

    FLAG = "ENABLE_FACTCHECK_CURRENCY_NORMALIZATION"
    AED_ROWS = [
        {"price": "AED 1,399.00"},
        {"price": "AED 1,399.00"},
        {"price": "AED 1,450.00"},
    ]

    def test_raw_foreign_amount_stamped_bhd_is_not_verified(self, service, monkeypatch):
        """A raw AED amount stamped BHD must NOT be verified by AED rows.

        Today the check is currency-blind: the AED numerals match the wrong
        BHD-stamped amount at 0.0% deviation and the defect is endorsed.
        """
        monkeypatch.setenv(self.FLAG, "true")
        price = {"amount": 1399, "currency": "BHD", "estimated": False}
        result = service._verify_price(price, list(self.AED_ROWS))
        assert result["price_verified"] is False
        assert result["deviation_pct"] > 30

    def test_correct_conversion_against_foreign_rows_is_verified(self, service, monkeypatch):
        """The CORRECT BHD conversion of the AED rows must be verified.

        142.9 BHD ~= AED 1,399 (rate 0.1024); today it is flagged at ~89.8%.
        """
        monkeypatch.setenv(self.FLAG, "true")
        price = {"amount": 142.9, "currency": "BHD", "estimated": False}
        result = service._verify_price(price, list(self.AED_ROWS))
        assert result["price_verified"] is True
        assert result["deviation_pct"] <= 30

    def test_usd_rows_converted_before_median(self, service, monkeypatch):
        """USD shopping rows are converted to BHD before the median is taken."""
        monkeypatch.setenv(self.FLAG, "true")
        price = {"amount": 150.4, "currency": "BHD", "estimated": False}
        shopping_items = [
            {"price": "$399.00"},
            {"price": "$405.00"},
            {"price": "$395.00"},
        ]
        result = service._verify_price(price, shopping_items)
        assert result["price_verified"] is True

    def test_unresolvable_mixed_currencies_returns_none_verdict(self, service, monkeypatch):
        """Rows with unresolvable currency tokens -> NO verdict, not a wrong one."""
        monkeypatch.setenv(self.FLAG, "true")
        price = {"amount": 50, "currency": "BHD", "estimated": False}
        shopping_items = [{"price": "ab 12"}, {"price": "cd 99"}]
        result = service._verify_price(price, shopping_items)
        assert result["price_verified"] is None
        assert result["deviation_pct"] is None
        assert result["source_count"] == 2

    def test_numeric_price_rows_unchanged(self, service, monkeypatch):
        """Numeric rows (no string to inspect) behave exactly as today, BOTH modes."""
        price = {"amount": 110, "currency": "BHD", "estimated": False}
        shopping_items = [{"price": 95}, {"price": 105}, {"price": 100}]

        monkeypatch.delenv(self.FLAG, raising=False)
        off = service._verify_price(price, list(shopping_items))
        monkeypatch.setenv(self.FLAG, "true")
        on = service._verify_price(price, list(shopping_items))

        expected = {"price_verified": True, "deviation_pct": 10.0, "source_count": 3}
        assert off == expected
        assert on == expected

    def test_thousands_and_decimal_separators_parse_correctly(self, service, monkeypatch):
        """BHD rows parse via parse_price_string, not re.findall on comma-stripped text.

        Canonical parser (M13-10 canon): on a BHD label BOTH "BHD 12,500" and
        "BHD 12.500" read as 12.5 (3-digit tail on a minor-unit-3 currency).
        Flag OFF today the comma row is read as 12500.0 by re.findall.
        NOTE: issue #106's prediction of 12500.0 for the comma row contradicts
        parse_price_string itself and the shipped M13-10 fix; the canonical
        parser is authoritative here.
        """
        monkeypatch.setenv(self.FLAG, "true")
        price = {"amount": 12.5, "currency": "BHD", "estimated": False}

        # Each row asserted explicitly via a single-row median.
        r_dot = service._verify_price(dict(price), [{"price": "BHD 12.500"}])
        assert r_dot["deviation_pct"] == 0.0
        assert r_dot["price_verified"] is True

        r_comma = service._verify_price(dict(price), [{"price": "BHD 12,500"}])
        assert r_comma["deviation_pct"] == 0.0  # 12.5, NOT 12500.0
        assert r_comma["price_verified"] is True

    @pytest.mark.parametrize(
        "price,shopping_items,expected",
        [
            pytest.param(
                {"amount": 1399, "currency": "BHD", "estimated": False},
                [{"price": "AED 1,399.00"}, {"price": "AED 1,399.00"}, {"price": "AED 1,450.00"}],
                {"price_verified": True, "deviation_pct": 0.0, "source_count": 3},
                id="case1-raw-aed-stamped-bhd",
            ),
            pytest.param(
                {"amount": 142.9, "currency": "BHD", "estimated": False},
                [{"price": "AED 1,399.00"}, {"price": "AED 1,399.00"}, {"price": "AED 1,450.00"}],
                {"price_verified": False, "deviation_pct": 89.8, "source_count": 3},
                id="case2-correct-conversion",
            ),
            pytest.param(
                {"amount": 150.4, "currency": "BHD", "estimated": False},
                [{"price": "$399.00"}, {"price": "$405.00"}, {"price": "$395.00"}],
                {"price_verified": False, "deviation_pct": 62.3, "source_count": 3},
                id="case3-usd-rows",
            ),
            pytest.param(
                {"amount": 50, "currency": "BHD", "estimated": False},
                [{"price": "ab 12"}, {"price": "cd 99"}],
                {"price_verified": False, "deviation_pct": 49.5, "source_count": 2},
                id="case4-unresolvable-rows",
            ),
            pytest.param(
                {"amount": 110, "currency": "BHD", "estimated": False},
                [{"price": 95}, {"price": 105}, {"price": 100}],
                {"price_verified": True, "deviation_pct": 10.0, "source_count": 3},
                id="case5-numeric-rows",
            ),
            pytest.param(
                {"amount": 12.5, "currency": "BHD", "estimated": False},
                [{"price": "BHD 12,500"}, {"price": "BHD 12.500"}],
                {"price_verified": False, "deviation_pct": 99.9, "source_count": 2},
                id="case6-separator-rows",
            ),
        ],
    )
    def test_flag_off_is_byte_identical(self, service, monkeypatch, price, shopping_items, expected):
        """Flag unset -> the returned dict is EXACTLY today's, for every #106 input.

        This is the per-function flag-OFF identity pin required by the issue's
        gates (scripts/verify_flag_byte_identity.py does not cover this module).
        """
        monkeypatch.delenv(self.FLAG, raising=False)
        result = service._verify_price(price, shopping_items)
        assert result == expected


# =====================================================
# Fact-check assembly (_build_fact_check)
# =====================================================

class TestBuildFactCheck:
    def test_high_confidence_all_verified(self, service):
        """All specs verified + price verified -> 'high'."""
        product = {
            "_spec_confidence": {
                "battery": "verified",
                "storage": "verified",
                "ram": "verified",
                "display": "verified",
            },
            "_review_verification": {
                "sentiment_consistent": True,
                "gpt_rating": 4.5,
                "serper_avg_rating": 4.4,
                "deviation": 0.1,
            },
            "_price_verification": {
                "price_verified": True,
                "deviation_pct": 5.0,
                "source_count": 3,
            },
        }
        result = service._build_fact_check(product)
        # Bundle E § Decision 7: overall_confidence pill dropped — per-field
        # signals are the new source of truth.
        assert "overall_confidence" not in result
        assert result["specs_verified"] == 4
        assert result["specs_flagged"] == 0
        assert result["price_verified"] is True
        assert result["review_sentiment_consistent"] is True

    def test_low_confidence_when_flagged(self, service):
        """Flagged specs -> 'low'."""
        product = {
            "_spec_confidence": {
                "battery": "flagged",
                "storage": "verified",
            },
            "_review_verification": {
                "sentiment_consistent": True,
                "deviation": 0.1,
            },
            "_price_verification": {
                "price_verified": True,
                "deviation_pct": 5.0,
                "source_count": 3,
            },
        }
        result = service._build_fact_check(product)
        # Bundle E § Decision 7: overall_confidence dropped — flagged specs
        # are now visible per-dimension via bar opacity instead.
        assert "overall_confidence" not in result
        assert result["specs_flagged"] == 1

    def test_low_confidence_when_sentiment_inconsistent(self, service):
        """Inconsistent sentiment -> 'low'."""
        product = {
            "_spec_confidence": {
                "battery": "verified",
                "storage": "verified",
            },
            "_review_verification": {
                "sentiment_consistent": False,
                "deviation": 1.5,
            },
            "_price_verification": {
                "price_verified": True,
                "deviation_pct": 5.0,
                "source_count": 3,
            },
        }
        result = service._build_fact_check(product)
        # Bundle E § Decision 7: overall_confidence dropped.
        assert "overall_confidence" not in result

    def test_medium_confidence_mixed(self, service):
        """Mix of verified and unverified -> 'medium'."""
        product = {
            "_spec_confidence": {
                "battery": "verified",
                "storage": "unverified",
                "ram": "likely",
                "display": "unverified",
                "processor": "unverified",
            },
            "_review_verification": {
                "sentiment_consistent": True,
                "deviation": 0.3,
            },
            "_price_verification": {
                "price_verified": False,
                "deviation_pct": 35.0,
                "source_count": 2,
            },
        }
        result = service._build_fact_check(product)
        # Bundle E § Decision 7: overall_confidence dropped.
        assert "overall_confidence" not in result

    def test_internal_keys_popped(self, service):
        """_spec_confidence, _review_verification, _price_verification are removed from product."""
        product = {
            "_spec_confidence": {"battery": "verified"},
            "_review_verification": {"sentiment_consistent": None},
            "_price_verification": {"price_verified": True, "deviation_pct": None, "source_count": 0},
        }
        service._build_fact_check(product)
        assert "_spec_confidence" not in product
        assert "_review_verification" not in product
        assert "_price_verification" not in product

    def test_empty_verifications(self, service):
        """No verification data at all -> medium confidence."""
        product = {}
        result = service._build_fact_check(product)
        # Bundle E § Decision 7: overall_confidence dropped.
        assert "overall_confidence" not in result
        assert result["specs_verified"] == 0
        assert result["specs_flagged"] == 0
        assert result["price_verified"] is False
        assert result["review_sentiment_consistent"] is None

    def test_fact_check_has_all_required_fields(self, service):
        """Fact check dict has all expected keys."""
        product = {
            "_spec_confidence": {"battery": "verified"},
            "_review_verification": {"sentiment_consistent": True, "deviation": 0.2},
            "_price_verification": {"price_verified": True, "deviation_pct": 5.0, "source_count": 3},
        }
        result = service._build_fact_check(product)
        # Bundle E § Decision 7: overall_confidence dropped from the contract.
        expected_keys = {
            "specs_verified", "specs_likely", "specs_flagged", "specs_unverified",
            "price_verified", "price_deviation_pct",
            "review_sentiment_consistent", "review_rating_deviation",
        }
        assert set(result.keys()) == expected_keys


# =====================================================
# Issue #108 — reliability weighting of the new 'flagged' outcome
# =====================================================

class TestFlaggedReliabilityWeighting:
    FLAG = "ENABLE_CITATION_RUBRIC_V2"

    def test_flagged_scores_below_unverified_in_reliability(self):
        """'flagged' (0.0) must score strictly below 'unverified' (0.3) —
        pins that the new output lands on the intended weight."""
        from app.services.scoring_service import ScoringService
        s = ScoringService()
        flagged_score = s._score_reliability(
            {"specs_verified": 0, "specs_likely": 0, "specs_flagged": 1, "specs_unverified": 0}
        )
        unverified_score = s._score_reliability(
            {"specs_verified": 0, "specs_likely": 0, "specs_flagged": 0, "specs_unverified": 1}
        )
        assert flagged_score < unverified_score

    def test_fabricated_citation_no_longer_outscores_training(self, service, monkeypatch):
        """End-to-end: product A cites battery to a number-free snippet,
        product B honestly answers 'training'. A must not outscore B.

        Today A earns 'likely' (0.7) and B 'unverified' (0.3) — the
        reliability dimension actively pays the model to invent a citation.
        """
        from app.services.scoring_service import ScoringService
        monkeypatch.setenv(self.FLAG, "true")
        snippets = ["All-day battery life with fast charging."]

        conf_a = service._verify_spec_citations(
            {"battery": "5000 mAh", "battery_source": "snippet_1"}, snippets
        )
        fc_a = service._build_fact_check({"_spec_confidence": conf_a})

        conf_b = service._verify_spec_citations(
            {"battery": "5000 mAh", "battery_source": "training"}, snippets
        )
        fc_b = service._build_fact_check({"_spec_confidence": conf_b})

        s = ScoringService()
        assert s._score_reliability(fc_a) <= s._score_reliability(fc_b)
