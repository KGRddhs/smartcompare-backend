"""Genuine-BH coverage keystone — strict_title_match must accept a model-line PDP
whose title omits the brand (BH retailers list "iPad Air M2 128GB", not
"Apple iPad Air M2 128GB"), WITHOUT letting a wrong-brand product through.

The candidate's own brand is dropped from the required query words ONLY when the
candidate carries that brand; a wrong-brand candidate keeps the query brand
required. Backed by _selection_match (run alongside), which strips candidate_brand
+ vets the full SKU.
"""
from __future__ import annotations

import pytest

from app.services.price_service import strict_title_match


class TestStrictTitleBrand:
    def test_model_line_pdp_accepted_with_candidate_brand(self):
        # The proven case: imachines.bh lists the iPad by model line, no "Apple".
        assert strict_title_match(
            "Apple iPad Air M2 128GB",
            "iPad Air M2 11-inch Wi-Fi 128GB Blue",
            candidate_brand="Apple",
        ) is True

    def test_model_line_rejected_without_candidate_brand_legacy(self):
        # No candidate_brand → legacy behaviour: brand still required (byte-safe).
        assert strict_title_match(
            "Apple iPad Air M2 128GB", "iPad Air M2 128GB",
        ) is False

    def test_wrong_brand_candidate_still_rejected(self):
        # candidate_brand=Samsung does NOT drop "apple"; and the model tokens
        # (ipad/air) are absent → rejected on two counts.
        assert strict_title_match(
            "Apple iPad Air M2 128GB", "Galaxy Tab S9 128GB",
            candidate_brand="Samsung",
        ) is False

    def test_same_class_different_brand_rejected(self):
        # "Apple Watch" vs a Samsung watch: candidate_brand=Samsung → "apple"
        # stays required → Samsung title lacks it → rejected.
        assert strict_title_match(
            "Apple Watch Series 9", "Galaxy Watch 6 44mm",
            candidate_brand="Samsung",
        ) is False

    def test_wrong_variant_still_rejected_even_with_brand(self):
        # Dropping the brand must NOT weaken the model/number discriminators.
        assert strict_title_match(
            "Apple iPad Air M2 256GB", "iPad Air M2 128GB",
            candidate_brand="Apple",
        ) is False  # 256 not in a 128 title

    def test_footwear_model_line_accepted(self):
        assert strict_title_match(
            "Nike Air Force 1 07 White",
            "Air Force 1 '07 Men's Shoes White",
            candidate_brand="Nike",
        ) is True

    def test_fragrance_unaffected(self):
        # Brand-present fragrance titles keep working (regression guard).
        assert strict_title_match(
            "Dior Sauvage Eau de Toilette 100ml",
            "Dior Sauvage Edt M 100Ml", candidate_brand="Dior",
        ) is True
