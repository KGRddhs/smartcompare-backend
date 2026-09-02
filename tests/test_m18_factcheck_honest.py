"""M18 factcheck-honest unit — fact-check must report ABSENCE honestly.

Findings covered (docs/investigations/2026-09-01-m18-verified.json):

* PO-fact-check-07 — ``verify_price`` fabricated ``price_verified=True`` from
  the ABSENCE of evidence (no shopping rows / no parseable rows =>
  ``not estimated`` read as confirmed, source_count=0, +0.1 reliability
  bonus downstream). Flag-ON (``ENABLE_FACTCHECK_HONEST_ABSENCE``) the
  empty-evidence verdict is ``None`` (unknown) for a non-estimated price and
  stays ``False`` for an estimate (an estimate is definitionally not a
  verified price — that negative is honest, not fabricated). Flag OFF is
  byte-identical legacy.
* PO-fact-check-09 — ``verify_review_sentiment`` raised TypeError on a string
  ``average_rating`` (``abs('4.5' - 4.3)``) at an unguarded call site, losing
  the whole compare. Coerced at BOTH layers (fact-check + extract-time
  normalize), unflagged: legitimate numeric traffic is unchanged and the
  string case previously CRASHED, so there is no legacy behaviour to preserve.
* PO-fact-check-10 — Bundle E Decision 7's ``is_data_freshness_shaky`` had
  zero producers. Now attached (additively) as
  ``metadata.data_freshness_shaky`` by the orchestrator on every
  build_comparison_response result.
* PO-fact-check-11 — "Ratings are NEVER AI-generated" was prompt-trusted only:
  ``data.setdefault("source_ratings", [])`` KEPT a model-emitted list and the
  real-ratings overwrite never fires on the live path (retailer_ratings=None
  in Phase 1). ``_normalize_review_response`` now hard-clears it, unflagged
  (an obedient model emits none, so legitimate traffic is byte-identical).

Run: python -m pytest tests/test_m18_factcheck_honest.py -q
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import inspect

import pytest

from app.services.fact_check_service import (
    build_fact_check,
    verify_price,
    verify_review_sentiment,
)
from app.services.extraction_service import _normalize_review_response


FLAG = "ENABLE_FACTCHECK_HONEST_ABSENCE"


# =====================================================================
# PO-fact-check-07 — verify_price absence honesty (flag-gated)
# =====================================================================

class TestVerifyPriceHonestAbsence:
    def test_flag_on_no_shopping_items_returns_unknown(self, monkeypatch):
        """Zero evidence + non-estimated price -> None (unknown), never True."""
        monkeypatch.setenv(FLAG, "true")
        price = {"amount": 1399, "currency": "BHD", "estimated": False}
        result = verify_price(price, [])
        assert result["price_verified"] is None
        assert result["source_count"] == 0
        assert result["deviation_pct"] is None

    def test_flag_on_no_parseable_rows_returns_unknown(self, monkeypatch):
        """Rows exist but none parses to a number -> None (unknown)."""
        monkeypatch.setenv(FLAG, "true")
        price = {"amount": 100, "currency": "BHD", "estimated": False}
        shopping_items = [{"price": "N/A"}, {"price": ""}, {"price": None}]
        result = verify_price(price, shopping_items)
        assert result["price_verified"] is None
        assert result["source_count"] == 0

    def test_flag_on_estimated_with_no_evidence_stays_false(self, monkeypatch):
        """An estimate is definitionally not verified — honest False, not None."""
        monkeypatch.setenv(FLAG, "true")
        price = {"amount": 100, "currency": "BHD", "estimated": True}
        result = verify_price(price, [])
        assert result["price_verified"] is False
        assert result["source_count"] == 0

    def test_flag_on_none_price_stays_false(self, monkeypatch):
        """No price dict at all -> False (unchanged: nothing was fabricated)."""
        monkeypatch.setenv(FLAG, "true")
        result = verify_price(None, [{"price": 100}])
        assert result["price_verified"] is False

    def test_flag_on_real_evidence_verdicts_unchanged(self, monkeypatch):
        """With actual rows the 30%-median verdict is untouched by the flag."""
        monkeypatch.setenv(FLAG, "true")
        price = {"amount": 110, "currency": "BHD", "estimated": False}
        ok = verify_price(price, [{"price": 95}, {"price": 105}, {"price": 100}])
        assert ok["price_verified"] is True
        assert ok["source_count"] == 3
        far = verify_price(
            {"amount": 150, "currency": "BHD", "estimated": False},
            [{"price": 90}, {"price": 100}, {"price": 110}],
        )
        assert far["price_verified"] is False

    def test_flag_off_legacy_fabrication_preserved(self, monkeypatch):
        """Flag OFF is byte-identical legacy: empty evidence reads verified."""
        monkeypatch.delenv(FLAG, raising=False)
        price = {"amount": 1399, "currency": "BHD", "estimated": False}
        assert verify_price(price, [])["price_verified"] is True
        assert (
            verify_price(price, [{"price": "N/A"}])["price_verified"] is True
        )

    def test_flag_on_with_currency_normalization_zero_rows(self, monkeypatch):
        """#106 flag-ON zero-rows branch also degrades to None under the flag."""
        monkeypatch.setenv(FLAG, "true")
        monkeypatch.setenv("ENABLE_FACTCHECK_CURRENCY_NORMALIZATION", "true")
        price = {"amount": 100, "currency": "BHD", "estimated": False}
        result = verify_price(price, [])
        assert result["price_verified"] is None
        assert result["source_count"] == 0

    def test_build_fact_check_passes_none_through(self):
        """The unknown verdict must survive fact_check assembly (not coerce to
        False/True) so downstream #109 identity tests see it as no-signal."""
        product = {
            "_spec_confidence": {},
            "_review_verification": {"sentiment_consistent": None},
            "_price_verification": {
                "price_verified": None,
                "deviation_pct": None,
                "source_count": 0,
            },
        }
        fc = build_fact_check(product)
        assert fc["price_verified"] is None


# =====================================================================
# PO-fact-check-09 — verify_review_sentiment string-rating crash
# =====================================================================

class TestVerifyReviewSentimentStringRating:
    RATINGS = [{"rating": 4.3, "review_count": 500}]

    def test_string_rating_is_coerced_not_crashed(self):
        """'4.5' (quoted number from JSON-mode model) must compute, not raise."""
        result = verify_review_sentiment({"average_rating": "4.5"}, self.RATINGS)
        assert result["gpt_rating"] == 4.5
        assert result["sentiment_consistent"] is True
        assert result["deviation"] == 0.2

    def test_unparseable_string_degrades_to_none_shape(self):
        result = verify_review_sentiment({"average_rating": "great"}, self.RATINGS)
        assert result["sentiment_consistent"] is None
        assert result["gpt_rating"] is None
        assert result["deviation"] is None

    def test_non_scalar_rating_degrades_to_none_shape(self):
        result = verify_review_sentiment(
            {"average_rating": {"value": 4.5}}, self.RATINGS
        )
        assert result["sentiment_consistent"] is None
        assert result["gpt_rating"] is None

    def test_numeric_rating_unchanged(self):
        result = verify_review_sentiment({"average_rating": 4.5}, self.RATINGS)
        assert result["sentiment_consistent"] is True
        assert result["gpt_rating"] == 4.5


# =====================================================================
# PO-fact-check-09/-11 — extract-time normalization
# =====================================================================

class TestNormalizeReviewResponseHardening:
    def test_model_emitted_source_ratings_dropped(self):
        """PO-fact-check-11: 'Ratings are NEVER AI-generated' is structural —
        a disobedient model's source_ratings are cleared at parse time (real
        retailer ratings are injected AFTER this, by review_service)."""
        raw = {"source_ratings": [{"source": "Amazon", "rating": 4.5}]}
        assert _normalize_review_response(raw)["source_ratings"] == []

    def test_source_ratings_default_still_empty(self):
        assert _normalize_review_response({})["source_ratings"] == []

    def test_string_average_rating_coerced_to_float(self):
        result = _normalize_review_response({"average_rating": "4.5"})
        assert result["average_rating"] == 4.5
        assert isinstance(result["average_rating"], float)

    def test_junk_average_rating_nulled(self):
        assert _normalize_review_response({"average_rating": "n/a"})[
            "average_rating"
        ] is None

    def test_numeric_average_rating_untouched(self):
        assert _normalize_review_response({"average_rating": 4.0})[
            "average_rating"
        ] == 4.0

    def test_missing_average_rating_stays_absent_shape(self):
        # No key -> normalize must not invent one (downstream uses .get()).
        result = _normalize_review_response({})
        assert result.get("average_rating") is None


# =====================================================================
# PO-fact-check-10 — the Decision 7 notice finally has a producer
# =====================================================================

class TestDataFreshnessNoticeWiring:
    def _result(self, fc_a, fc_b):
        return {
            "metadata": {
                "fact_check": {"product_0": fc_a, "product_1": fc_b},
            }
        }

    def test_all_bad_signals_sets_true(self):
        from app.services.structured_comparison_service import (
            attach_data_freshness_notice,
        )
        bad = {
            "specs_verified": 0,
            "specs_likely": 0,
            "price_verified": False,
            "review_sentiment_consistent": None,
        }
        result = attach_data_freshness_notice(self._result(bad, dict(bad)))
        assert result["metadata"]["data_freshness_shaky"] is True

    def test_healthy_signals_set_false(self):
        from app.services.structured_comparison_service import (
            attach_data_freshness_notice,
        )
        good = {
            "specs_verified": 4,
            "specs_likely": 2,
            "price_verified": True,
            "review_sentiment_consistent": True,
        }
        result = attach_data_freshness_notice(self._result(good, dict(good)))
        assert result["metadata"]["data_freshness_shaky"] is False

    def test_defensive_on_missing_metadata(self):
        from app.services.structured_comparison_service import (
            attach_data_freshness_notice,
        )
        assert attach_data_freshness_notice({}) == {}
        assert attach_data_freshness_notice({"metadata": {}}) == {"metadata": {}}

    def test_every_build_site_attaches_the_notice(self):
        """All three build_comparison_response call sites in the orchestrator
        (partial salvage, sync, streaming) must feed through the attach helper
        — the M18 finding was exactly that the predicate had zero producers."""
        import app.services.structured_comparison_service as scs
        src = inspect.getsource(scs)
        build_calls = src.count("= build_comparison_response(")
        attach_calls = src.count("attach_data_freshness_notice(")
        assert build_calls >= 3
        # def + one call per build site
        assert attach_calls >= build_calls + 1
