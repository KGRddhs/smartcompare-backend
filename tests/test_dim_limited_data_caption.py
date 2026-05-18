"""Bundle C § 2b A.4.4 — caption_key='limited_data' on missing-data dims.

Per design § 2b + plan A.4.4: when a dim cannot honestly compute a winner
(both products missing the underlying signal) but is still emitted as a
last-resort row, it carries `caption_key='limited_data'` so the frontend
can render the spec § 2b "—" row instead of fake scores.

Backend contract only — frontend rendering is owned by B.5
(DimensionBars). Backend never emits user-facing strings; only the
i18n key reference.
"""
import pytest

from app.services.scoring_service import _dim_price, _dim_reviews, _dim_value


def test_dim_price_emits_limited_data_caption_when_both_prices_missing():
    products = [
        {"name": "A", "price": {"amount": None}},
        {"name": "B", "price": {"amount": None}},
    ]
    dim = _dim_price(products)
    assert dim["confidence"] == "low"
    assert dim.get("caption_key") == "limited_data"


def test_dim_price_no_caption_when_both_prices_present():
    products = [
        {"name": "A", "price": {"amount": 100.0}},
        {"name": "B", "price": {"amount": 80.0}},
    ]
    dim = _dim_price(products)
    assert dim["confidence"] == "high"
    assert dim.get("caption_key") is None


def test_dim_reviews_emits_limited_data_caption_when_both_ratings_missing():
    products = [
        {"name": "A", "price": {"amount": 100.0}, "rating": None},
        {"name": "B", "price": {"amount": 80.0}, "rating": None},
    ]
    dim = _dim_reviews(products)
    assert dim["confidence"] == "low"
    assert dim.get("caption_key") == "limited_data"


def test_dim_value_emits_limited_data_caption_when_missing_data():
    """A.4.2 made _dim_value short-circuit to neutral when rating/price
    missing. A.4.4 adds the caption_key marker on that path."""
    products = [
        {"name": "A", "price": {"amount": None}, "rating": None},
        {"name": "B", "price": {"amount": None}, "rating": None},
    ]
    dim = _dim_value(products)
    assert dim["confidence"] == "low"
    assert dim.get("caption_key") == "limited_data"


def test_caption_key_uses_i18n_key_not_user_string():
    """Backend MUST emit only the i18n key reference, not the rendered
    English string. Frontend B.5 resolves the key to a localised label."""
    products = [
        {"name": "A", "price": {"amount": None}},
        {"name": "B", "price": {"amount": None}},
    ]
    dim = _dim_price(products)
    caption = dim.get("caption_key", "")
    # i18n key style: lowercase snake_case, no spaces, no punctuation
    assert " " not in caption
    assert "—" not in caption
    assert "limited data" not in caption.lower() or caption == "limited_data"


def test_no_forbidden_words_in_dim_strings_when_caption_key_set():
    """Critical rule #3 + #5: even on missing-data path, no 'estimated'
    / 'reference price' / scary copy leaks into delta_text or label."""
    products = [
        {"name": "A", "price": {"amount": None}, "rating": None},
        {"name": "B", "price": {"amount": None}, "rating": None},
    ]
    for builder in (_dim_price, _dim_reviews, _dim_value):
        dim = builder(products)
        body = " ".join(str(dim.get(k, "")) for k in ("delta_text", "label"))
        low = body.lower()
        for forbidden in ("estimated", "reference price", "approximate",
                          "couldn't", "try again", "failed to"):
            assert forbidden not in low, (
                f"{builder.__name__} leaked {forbidden!r} on missing-data path: {dim!r}"
            )
