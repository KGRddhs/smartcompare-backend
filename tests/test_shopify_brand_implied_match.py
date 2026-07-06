"""Brand-implied matcher fix (2026-07-07) — Shopify own-brand-store coverage.

THE BUG (audit-confirmed live): a brand's OWN Shopify store OMITS its brand from
product titles — en-bh.ajmal.com lists "ARISTOCRAT CORAL EAU DE PARFUM 75 ML"
(vendor="Ajmal"), NOT "Ajmal Aristocrat". The app queries "Ajmal Aristocrat", so
_match_shopify_product's strict_title_match/_selection_match — called WITHOUT a
candidate_brand — required the "ajmal" token in the title and REJECTED the exact
SKU. A genuine 22.55 BHD price existed and was thrown away (this is why
"Ajmal Aristocrat vs Rasasi Hawas" dead-ended).

THE FIX (mirrors the proven magento_graphql / occ / noon / algolia pattern):
derive _cand_brand from the Shopify product's `vendor` field and thread
candidate_brand=_cand_brand into BOTH strict_title_match and _selection_match.
When the candidate's own brand == the query brand, its tokens drop from the
required set (brand-omitted title recovered); a WRONG-brand candidate keeps the
query brand required and is still rejected (no wrong-match). Gated by
exact_gate_enabled() the same way the sibling adapters gate it → flag-OFF
byte-identical.
"""
import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

import pytest

from app.services.price_service import _match_shopify_product


def _catalog(title, vendor, price="22.55", currency="BHD", available=True):
    return {
        "_store_currency": currency,
        "products": [{
            "title": title,
            "vendor": vendor,
            "handle": title.lower().replace(" ", "-"),
            "variants": [{"price": price, "available": available, "title": "75ml"}],
        }],
    }


class TestBrandImpliedMatch:
    def test_own_brand_store_brand_omitted_title_matches(self):
        """en-bh.ajmal.com: query 'Ajmal Aristocrat' vs a BASE title
        'Aristocrat Eau de Parfum 75 ML' (vendor='Ajmal') -> the vendor supplies
        the brand, so the brand-omitted title resolves to the genuine 22.55 BHD."""
        cat = _catalog("Aristocrat Eau de Parfum 75 ML", "Ajmal")
        r = _match_shopify_product(cat, "Ajmal Aristocrat", "BHD", "en-bh.ajmal.com", "fragrances")
        assert r is not None, "brand-omitted own-store title was rejected (the bug)"
        assert r["amount"] == 22.55
        assert r["currency"] == "BHD"
        assert r["source_method"] == "shopify_json"

    def test_flanker_still_rejected_no_fab(self):
        """CORRECTNESS: a base query 'Ajmal Aristocrat' must NOT match a distinct
        FLANKER 'Aristocrat Coral' — even on the right brand's store — because
        Coral is a different product. The brand-implied relaxation does NOT open
        the flanker (the _selection_match axis/superset gate still rejects it)."""
        cat = _catalog("Aristocrat Coral Eau de Parfum 75 ML", "Ajmal")
        r = _match_shopify_product(cat, "Ajmal Aristocrat", "BHD", "en-bh.ajmal.com", "fragrances")
        assert r is None

    def test_wrong_brand_still_rejected(self):
        """A DIFFERENT query brand must NOT be satisfied by the store's vendor:
        query 'Rasasi Aristocrat' vs an Ajmal-vendor title -> None (the vendor is
        Ajmal, so 'rasasi' is never dropped and stays required; the title lacks
        it). This is the wrong-match guard."""
        cat = _catalog("Aristocrat Eau de Parfum 75 ML", "Ajmal")
        r = _match_shopify_product(cat, "Rasasi Aristocrat", "BHD", "en-bh.ajmal.com", "fragrances")
        assert r is None

    def test_brand_present_title_still_matches(self):
        """Regression: a title that DOES carry the brand still matches (the fix
        only RELAXES a brand-omitted title, never rejects a brand-present one)."""
        cat = _catalog("Ajmal Aristocrat Eau de Parfum 75 ML", "Ajmal")
        r = _match_shopify_product(cat, "Ajmal Aristocrat", "BHD", "en-bh.ajmal.com", "fragrances")
        assert r is not None and r["amount"] == 22.55

    def test_no_vendor_field_unchanged(self):
        """A product with NO vendor field behaves exactly as today (brand
        required) — the fix reads vendor defensively, empty -> legacy behaviour."""
        cat = {"_store_currency": "BHD", "products": [{
            "title": "Aristocrat Eau de Parfum 75 ML", "handle": "x",
            "variants": [{"price": "22.55", "available": True, "title": "75ml"}],
        }]}
        r = _match_shopify_product(cat, "Ajmal Aristocrat", "BHD", "en-bh.ajmal.com", "fragrances")
        assert r is None  # no vendor -> brand still required -> rejected (as today)

    def test_flag_off_byte_identical(self, monkeypatch):
        """ENABLE_EXACT_PRICE_GATE=false -> candidate_brand is inert (strict_title_match
        computes brand_toks only under the gate), so the brand-omitted title is
        REJECTED exactly as pre-fix."""
        monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "false")
        cat = _catalog("Aristocrat Eau de Parfum 75 ML", "Ajmal")
        r = _match_shopify_product(cat, "Ajmal Aristocrat", "BHD", "en-bh.ajmal.com", "fragrances")
        assert r is None  # flag-off: brand required, brand-omitted title rejected
