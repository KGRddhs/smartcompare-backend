# -*- coding: utf-8 -*-
"""Genuine-Price CORRECTNESS — fragrance concentration + ml-size EXACTNESS.

Wave-A TDD reds/greens for the CARDINAL RULE (see
``docs/plans/2026-06-27-genuine-price-correctness-IMPL-SPEC.md``): a price is
selectable ONLY when it is the EXACT requested product (model + concentration +
size). A wrong concentration/size must PEND (return None / not be selected),
NOT be down-ranked-but-still-returned. The gate must ALSO not over-reject
legitimate alias wording (EDT≡"eau de toilette", oz≡ml, absent concentration).

These exercise the two real-shaped extractors that carry the bug today:
- ``extract_price_from_shopping`` — Serper Shopping path. Today concentration /
  size are only a SOFT tie-break (``variant_precision_rank``) behind retailer
  authority, and ``amount`` is the final sort key, so a wrong-concentration /
  wrong-size candidate with a higher retailer score (or as the sole candidate)
  is returned instead of pending.
- ``extract_jsonld_price`` — curl JSON-LD path. Today it keeps the CHEAPEST
  offer across same-brand Product nodes (``price_val < best_price["amount"]``)
  with no concentration / size identity check, so the cheaper EDT is attributed
  to an EDP query.

RED tests fail on the CURRENT code (the bug) and pass after Wave B/C strengthen
the matcher with a hard exact-identity gate + an authority selector.
GREEN tests pass NOW and MUST keep passing after the strict gate (no false
pends on legitimate alias wording).

NEW-HELPER contract tests (``is_exact_match`` / ``select_best``) import the
symbol INSIDE the test body so collection never errors before Wave B lands;
they fail with ImportError = a real red until the helpers exist.

Windows: any file open uses encoding='utf-8' (none opened here).
"""

import pytest

from app.services.price_service import (
    extract_price_from_shopping,
    extract_jsonld_price,
)


# ---------------------------------------------------------------------------
# Real-shaped fixtures
# ---------------------------------------------------------------------------
#
# Chanel is in LUXURY_BRAND_KEYWORDS → is_luxury_brand("Bleu de Chanel ...") is
# True → extract_price_from_shopping sorts by
#   (-retailer_score, -variant_rank, -match_score, amount).
# "Bleu de Chanel" is NOT high-value (is_high_value_query is False for
# fragrances) → strict_title_match is NOT applied, only the soft variant_rank
# tie-break. So a WRONG-concentration / WRONG-size candidate sitting on a
# higher-authority retailer (Sephora, score 1.0) out-ranks the correct one on
# the default-score retailer (0.5) — the cheapest-wrong-SKU class.

_EDP_QUERY = "Bleu de Chanel Eau de Parfum 100ml"

# correct EDP on a default-tier retailer (score 0.5)
_EDP_ITEM = {
    "title": "Bleu de Chanel Eau de Parfum 100ml",
    "price": "BHD 60.000",
    "source": "ParfumStore",
    "link": "https://parfumstore.example/bleu-edp-100",
}
# WRONG concentration EDT — cheaper AND on a HIGHER-authority retailer (1.0)
_EDT_ITEM = {
    "title": "Bleu de Chanel Eau de Toilette 100ml",
    "price": "BHD 45.000",
    "source": "Sephora",
    "link": "https://sephora.example/bleu-edt-100",
}
# WRONG size 30ml — cheaper AND on a HIGHER-authority retailer (1.0)
_SIZE_30_ITEM = {
    "title": "Bleu de Chanel Eau de Parfum 30ml",
    "price": "BHD 25.000",
    "source": "Sephora",
    "link": "https://sephora.example/bleu-edp-30",
}


def _jsonld_product(name, price, currency="BHD", availability="https://schema.org/InStock"):
    """A single JSON-LD <script> for a same-brand (Chanel) Product node."""
    return (
        '<script type="application/ld+json">'
        '{"@type":"Product","name":"%s",'
        '"brand":{"@type":"Brand","name":"Chanel"},'
        '"offers":{"@type":"Offer","price":"%s","priceCurrency":"%s",'
        '"availability":"%s"}}'
        "</script>"
    ) % (name, price, currency, availability)


# ===========================================================================
# RED — extract_price_from_shopping concentration exactness
# ===========================================================================

def test_shopping_edp_query_rejects_cheaper_higher_authority_edt():  # RED
    """Query is EDP; a CHEAPER EDT on a higher-authority retailer is present
    alongside the correct EDP. The EXACT EDP (60.0) must be selected — the
    wrong-concentration EDT (45.0) must NOT win despite its retailer authority.
    CURRENT: returns the EDT (45.0) — concentration is only a soft tie-break."""
    result = extract_price_from_shopping(
        _EDP_QUERY,
        [_EDT_ITEM, _EDP_ITEM],
        "BHD",
        shopping_region="bahrain",
    )
    assert result is not None, "the exact EDP candidate must be selectable"
    assert result["amount"] == 60.0, (
        "must select the EXACT EDP (60.0), not the cheaper wrong-concentration "
        f"EDT (45.0); got {result['amount']}"
    )


def test_shopping_edp_query_pends_when_only_edt_available():  # RED
    """Query is EDP; the ONLY candidate is an EDT. A wrong-concentration sole
    candidate must PEND (None), never be returned as the EDP's price.
    CURRENT: returns the EDT (45.0)."""
    result = extract_price_from_shopping(
        _EDP_QUERY,
        [_EDT_ITEM],
        "BHD",
        shopping_region="bahrain",
    )
    assert result is None, (
        "no EDP candidate exists — an EDT must not be attributed to an EDP "
        f"query; expected None, got {result}"
    )


# ===========================================================================
# RED — extract_price_from_shopping ml-size exactness
# ===========================================================================

def test_shopping_100ml_query_rejects_cheaper_higher_authority_30ml():  # RED
    """Query states 100ml; a CHEAPER 30ml on a higher-authority retailer is
    present alongside the correct 100ml. The EXACT 100ml (60.0) must win — the
    30ml (25.0) must NOT be attributed to a 100ml query.
    CURRENT: returns the 30ml (25.0) — size is only a soft tie-break."""
    result = extract_price_from_shopping(
        _EDP_QUERY,  # "...Eau de Parfum 100ml"
        [_SIZE_30_ITEM, _EDP_ITEM],
        "BHD",
        shopping_region="bahrain",
    )
    assert result is not None, "the exact 100ml candidate must be selectable"
    assert result["amount"] == 60.0, (
        "must select the EXACT 100ml (60.0), not the cheaper 30ml (25.0); "
        f"got {result['amount']}"
    )


def test_shopping_100ml_query_pends_when_only_30ml_available():  # RED
    """Query states 100ml; the ONLY candidate is a 30ml (a sample-sized /
    decant-sized bottle). It must PEND (None), not be shown as the 100ml price.
    CURRENT: returns the 30ml (25.0)."""
    result = extract_price_from_shopping(
        _EDP_QUERY,
        [_SIZE_30_ITEM],
        "BHD",
        shopping_region="bahrain",
    )
    assert result is None, (
        "no 100ml candidate exists — a 30ml must not be attributed to a 100ml "
        f"query; expected None, got {result}"
    )


# ===========================================================================
# RED — extract_jsonld_price concentration / size exactness
# ===========================================================================

def test_jsonld_edp_query_rejects_cheaper_edt_node():  # RED
    """Two same-brand Product nodes on one PDP: a cheaper EDT 100ml (45) and the
    correct EDP 100ml (60). The EDP query must resolve to the EDP node (60).
    CURRENT: keeps the cheapest offer (45, the EDT) via `price_val < best`."""
    html = (
        "<html><head>"
        + _jsonld_product("Bleu de Chanel Eau de Toilette 100ml", "45.000")
        + _jsonld_product("Bleu de Chanel Eau de Parfum 100ml", "60.000")
        + "</head></html>"
    )
    result = extract_jsonld_price(html, "Chanel", "BHD", query_name=_EDP_QUERY)
    assert result is not None, "the exact EDP node must be selectable"
    assert result["amount"] == 60.0, (
        "must select the EXACT EDP node (60.0), not the cheaper EDT node "
        f"(45.0); got {result['amount']}"
    )


def test_jsonld_edp_query_pends_when_only_edt_node():  # RED
    """Only an EDT 100ml node exists for an EDP query → PEND (None).
    CURRENT: returns the EDT (45.0)."""
    html = (
        "<html><head>"
        + _jsonld_product("Bleu de Chanel Eau de Toilette 100ml", "45.000")
        + "</head></html>"
    )
    result = extract_jsonld_price(html, "Chanel", "BHD", query_name=_EDP_QUERY)
    assert result is None, (
        "no EDP node exists — an EDT node must not be attributed to an EDP "
        f"query; expected None, got {result}"
    )


def test_jsonld_100ml_query_rejects_cheaper_30ml_node():  # RED
    """Two same-brand EDP nodes differing only in size: a cheaper 30ml (35) and
    the correct 100ml (60). A 100ml query must resolve to the 100ml node.
    CURRENT: keeps the cheapest offer (35, the 30ml)."""
    html = (
        "<html><head>"
        + _jsonld_product("Bleu de Chanel Eau de Parfum 30ml", "35.000")
        + _jsonld_product("Bleu de Chanel Eau de Parfum 100ml", "60.000")
        + "</head></html>"
    )
    result = extract_jsonld_price(html, "Chanel", "BHD", query_name=_EDP_QUERY)
    assert result is not None, "the exact 100ml node must be selectable"
    assert result["amount"] == 60.0, (
        "must select the EXACT 100ml node (60.0), not the cheaper 30ml node "
        f"(35.0); got {result['amount']}"
    )


# ===========================================================================
# RED (new-helper) — is_exact_match concentration + size contract
# ===========================================================================
# Import INSIDE the test body so collection never errors before Wave B adds the
# symbol; until then these fail with ImportError = a real red.

def test_is_exact_match_rejects_concentration_mismatch():  # RED (new-helper)
    from app.services.price_service import is_exact_match
    assert is_exact_match(
        "Bleu de Chanel Eau de Parfum 100ml",
        "Bleu de Chanel Eau de Toilette 100ml",
        "fragrances",
    ) is False, "EDP query vs EDT title must NOT be an exact match"


def test_is_exact_match_rejects_size_mismatch():  # RED (new-helper)
    from app.services.price_service import is_exact_match
    assert is_exact_match(
        "Bleu de Chanel Eau de Parfum 100ml",
        "Bleu de Chanel Eau de Parfum 30ml",
        "fragrances",
    ) is False, "100ml query vs 30ml title must NOT be an exact match"


def test_is_exact_match_accepts_edt_abbreviation_alias():  # RED (new-helper)
    from app.services.price_service import is_exact_match
    assert is_exact_match(
        "Dior Sauvage EDT 100ml",
        "Dior Sauvage Eau de Toilette 100ml",
        "fragrances",
    ) is True, "EDT ≡ 'eau de toilette' must collapse-equal (no false reject)"


def test_is_exact_match_accepts_oz_size_alias():  # RED (new-helper)
    from app.services.price_service import is_exact_match
    assert is_exact_match(
        "Dior Sauvage Eau de Toilette 100ml",
        "Dior Sauvage Eau de Toilette 3.4 oz",
        "fragrances",
    ) is True, "3.4 oz ≡ 100ml (snapped) must match (no false reject)"


def test_is_exact_match_accepts_when_query_omits_concentration():  # RED (new-helper)
    from app.services.price_service import is_exact_match
    assert is_exact_match(
        "Bleu de Chanel 100ml",
        "Bleu de Chanel Eau de Parfum 100ml",
        "fragrances",
    ) is True, (
        "query silent on concentration → a candidate concentration must NOT "
        "reject (absent-axis policy)"
    )


# ===========================================================================
# GREEN — anti-over-rejection: legit alias wording stays selectable
# ===========================================================================

def test_shopping_edt_abbreviation_alias_still_matched():  # GREEN
    """Query 'Dior Sauvage EDT 100ml' must match a 'Dior Sauvage Eau de Toilette
    100ml' title (EDT ≡ spelled-out concentration). MUST stay green after the
    strict gate."""
    result = extract_price_from_shopping(
        "Dior Sauvage EDT 100ml",
        [{
            "title": "Dior Sauvage Eau de Toilette 100ml",
            "price": "BHD 35.000",
            "source": "ParfumStore",
            "link": "https://parfumstore.example/sauvage-edt-100",
        }],
        "BHD",
        shopping_region="bahrain",
    )
    assert result is not None and result["amount"] == 35.0, (
        "an EDT-abbreviation alias of the same concentration must NOT be "
        f"pended; got {result}"
    )


def test_shopping_oz_size_alias_still_matched():  # GREEN
    """Query '...Eau de Parfum 100ml' must match a title carrying '3.4 oz'
    (snaps to 100ml). MUST stay green after the strict gate."""
    result = extract_price_from_shopping(
        "Dior Sauvage Eau de Toilette 100ml",
        [{
            "title": "Dior Sauvage Eau de Toilette 3.4 oz",
            "price": "BHD 35.000",
            "source": "ParfumStore",
            "link": "https://parfumstore.example/sauvage-oz",
        }],
        "BHD",
        shopping_region="bahrain",
    )
    assert result is not None and result["amount"] == 35.0, (
        "a 3.4 oz title (= 100ml snapped) must NOT be pended against a 100ml "
        f"query; got {result}"
    )


def test_shopping_query_without_concentration_still_selectable():  # GREEN
    """Query 'Bleu de Chanel 100ml' states NO concentration. A candidate with a
    concentration (EDP) must remain selectable — the absent axis must not
    reject. MUST stay green after the strict gate."""
    result = extract_price_from_shopping(
        "Bleu de Chanel 100ml",
        [{
            "title": "Bleu de Chanel Eau de Parfum 100ml",
            "price": "BHD 60.000",
            "source": "ParfumStore",
            "link": "https://parfumstore.example/bleu-edp-100",
        }],
        "BHD",
        shopping_region="bahrain",
    )
    assert result is not None and result["amount"] == 60.0, (
        "a concentration-unspecified query must still select a candidate "
        f"(no false pend for an unspecified axis); got {result}"
    )
