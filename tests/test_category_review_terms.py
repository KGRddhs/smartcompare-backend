"""L2.10 — Tests for per-category review search terms.

Asserts that every category in CATEGORY_SPEC_SCHEMAS has its own entry in
CATEGORY_REVIEW_TERMS so the Serper review query is tailored to the domain
vocabulary (supplements -> dosage/clinical, fragrances -> longevity/sillage,
haircare -> frizz/scalp).
"""

import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

from app.services.extraction_service import CATEGORY_SPEC_SCHEMAS
from app.services.review_service import CATEGORY_REVIEW_TERMS


def test_review_terms_for_supplements_clinical():
    terms = CATEGORY_REVIEW_TERMS["supplements"]
    assert any(w in terms for w in ("dosage", "effectiveness", "side effects", "clinical"))


def test_review_terms_for_fragrances_longevity():
    terms = CATEGORY_REVIEW_TERMS["fragrances"]
    assert any(w in terms for w in ("longevity", "sillage", "projection", "scent"))


def test_review_terms_for_haircare_results():
    terms = CATEGORY_REVIEW_TERMS["haircare"]
    assert any(w in terms for w in ("frizz", "scalp", "texture", "results"))


def test_review_terms_for_other_generic():
    terms = CATEGORY_REVIEW_TERMS["other"]
    assert any(w in terms for w in ("quality", "value", "function"))


def test_every_spec_schema_category_has_review_terms():
    """No category in CATEGORY_SPEC_SCHEMAS may fall back to the implicit
    default. Each schema-supported category needs tailored vocabulary."""
    missing = []
    for cat in CATEGORY_SPEC_SCHEMAS:
        if cat not in CATEGORY_REVIEW_TERMS:
            missing.append(cat)
    assert not missing, f"missing review-term vocabularies: {missing}"


def test_review_terms_are_lowercase_strings():
    for cat, terms in CATEGORY_REVIEW_TERMS.items():
        assert isinstance(terms, str), f"{cat} terms not a string"
        assert terms == terms.lower(), f"{cat} terms should be lowercase for Serper"
        assert len(terms) > 10, f"{cat} terms too short to be useful"


def test_review_terms_make_sense_per_category():
    """Sanity: terms must include 'review' or 'rating' or a domain noun so the
    Serper organic results are biased toward user feedback, not retail
    listings."""
    for cat, terms in CATEGORY_REVIEW_TERMS.items():
        has_review_signal = any(
            w in terms for w in ("review", "rating", "feedback", "results")
        )
        assert has_review_signal, (
            f"{cat} terms lack review/rating/feedback signal: {terms!r}"
        )
