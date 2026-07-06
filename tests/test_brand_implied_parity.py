"""Brand-implied matcher parity (2026-07-07) — the 5 adapters that lacked
candidate_brand threading now match magento/occ/noon/algolia.

An own-brand store OMITS its brand from titles (Ajmal store: "ARISTOCRAT EDP",
not "Ajmal Aristocrat"). Each adapter derives the candidate's OWN brand from its
platform's brand field and threads it as candidate_brand so a brand-omitted title
of the QUERY's brand resolves, while a WRONG-brand hit keeps the query brand
required (no wrong-match). These pin each adapter's derivation + threading.
"""
import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

import pytest

from app.services.price_service import (
    strict_title_match, _selection_match, normalize_candidate_brand,
)
from app.services.unbxd_service import _match_unbxd_product
from app.services.salla_service import _select_candidate
from app.services.rest_json_service import _title_matches

Q = "Ajmal Aristocrat"
WRONG_Q = "Rasasi Aristocrat"
TITLE = "Aristocrat Eau de Parfum 75 ML"   # BASE product, brand OMITTED
CAT = "fragrances"


class TestNormalizeCandidateBrand:
    """The shared brand normalizer — must handle every adapter field shape and
    NEVER raise (brand-implied review: salla can return a bare-string `brand`,
    a dict/list slipped into a scalar field must not stringify to junk)."""

    def test_scalar_string(self):
        assert normalize_candidate_brand("Ajmal") == "Ajmal"
        assert normalize_candidate_brand("  Ajmal  ") == "Ajmal"

    def test_dict_name(self):
        assert normalize_candidate_brand({"id": 1, "name": "Ajmal"}) == "Ajmal"

    def test_list_first(self):
        assert normalize_candidate_brand(["Ajmal", "x"]) == "Ajmal"
        assert normalize_candidate_brand([{"name": "Ajmal"}]) == "Ajmal"

    def test_none_and_empty(self):
        assert normalize_candidate_brand(None) == ""
        assert normalize_candidate_brand([]) == ""
        assert normalize_candidate_brand({}) == ""

    def test_never_raises_on_junk(self):
        # a bare int / bool / nested-empty must return "" not raise
        for junk in (123, True, {"name": None}, [None], [[]]):
            assert normalize_candidate_brand(junk) == ""


class TestSharedMechanism:
    """The strict_title_match + _selection_match candidate_brand mechanism every
    adapter now relies on."""

    def test_candidate_brand_recovers_brand_omitted_title(self):
        assert strict_title_match(Q, TITLE, candidate_brand="Ajmal") is True
        assert _selection_match(Q, TITLE, CAT, candidate_brand="Ajmal") is True

    def test_no_candidate_brand_rejects(self):
        assert strict_title_match(Q, TITLE) is False  # brand required, omitted -> reject

    def test_wrong_brand_not_recovered(self):
        # candidate_brand 'Ajmal' does not drop 'rasasi' -> still required -> reject
        assert strict_title_match(WRONG_Q, TITLE, candidate_brand="Ajmal") is False


class TestRestJsonTitleMatches:
    def test_brand_omitted_matches_with_candidate_brand(self):
        assert _title_matches(Q, TITLE, CAT, candidate_brand="Ajmal") is True

    def test_brand_omitted_rejected_without_candidate_brand(self):
        assert _title_matches(Q, TITLE, CAT) is False

    def test_wrong_brand_rejected(self):
        assert _title_matches(WRONG_Q, TITLE, CAT, candidate_brand="Ajmal") is False


class TestUnbxdBrandEn:
    def _products(self, brand):
        return [{"title": TITLE, "brandEn": brand, "price": 22.55}]

    def test_own_brand_omitted_matches(self):
        r = _match_unbxd_product(self._products("Ajmal"), Q, CAT)
        assert r is not None, "brandEn did not recover the brand-omitted title"

    def test_wrong_brand_rejected(self):
        # query 'Ajmal Aristocrat' vs a SAMSUNG-branded node -> None
        r = _match_unbxd_product(self._products("Samsung"), Q, CAT)
        assert r is None

    def test_no_brand_field_unchanged(self):
        r = _match_unbxd_product([{"title": TITLE, "price": 22.55}], Q, CAT)
        assert r is None  # no brandEn -> brand required -> rejected (legacy)


class TestSallaNestedBrand:
    def _data(self, brand_name):
        return [{"name": TITLE, "brand": {"id": 1, "name": brand_name}, "price": 22.55}]

    def test_own_brand_omitted_matches(self):
        r = _select_candidate(self._data("Ajmal"), Q, CAT)
        assert r is not None

    def test_wrong_brand_rejected(self):
        r = _select_candidate(self._data("Rasasi"), Q, CAT)
        assert r is None

    def test_null_brand_dict_safe_and_legacy(self):
        # brand is the literal null (JSON) -> None -> legacy (brand required) -> reject
        r = _select_candidate([{"name": TITLE, "brand": None, "price": 22.55}], Q, CAT)
        assert r is None

    def test_bare_string_brand_does_not_crash_and_matches(self):
        """Review MEDIUM fix: a Salla store returning brand as a bare STRING
        (not a {"name":...} dict) must NOT AttributeError — it now normalizes to
        the string and recovers the own-brand-omitted title."""
        r = _select_candidate([{"name": TITLE, "brand": "Ajmal", "price": 22.55}], Q, CAT)
        assert r is not None
