"""KPI Wave A2 — three BOUNDED matcher folds, all pinned through the REAL
strict_title_match / _selection_match (fashion lane recon 2026-07-02).

1. APOSTROPHE fold — retailer titles carry the possessive/elision spelling
   ("Levi's 501", "Air Force 1 '07", "Men's Shoes"; ASCII ' or typographic
   U+2019) that the truth query writes bare, and the unfolded apostrophe was a
   token mismatch rejecting the EXACT product at one or both gates.
2. LUXOTTICA 0-PREFIX fold — namshi/Luxottica catalogs list "0Rb3025" for
   RB3025; the 0-prefixed token failed identity equality. NARROW alias
   (^0(rb|rx)\\d{3,}$ only) — leading zeros are never stripped generally.
3. POLO COMPOUND collapse — "Polo T-Shirt" is retail phrasing for a POLO
   (6thstreet lists Lacoste L1212 that way); the compound collapses to "polo"
   so a polo query matches it AND a plain t-shirt query class-swap-rejects it.
   A bare "t-shirt" (no polo) is untouched in both directions.

Every fold ships with BOTH directions: the newly-accepted correct title and
the adversarial neighbour that must stay rejected.
"""
import pytest

from app.services.price_service import (
    _identity_tokens_ps,
    _selection_match,
    strict_title_match,
)


@pytest.fixture(autouse=True)
def _gate_on(monkeypatch):
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "true")


def _sel(query, title, candidate_brand=""):
    return _selection_match(query, title, "fashion", candidate_brand=candidate_brand)


# ---------------------------------------------------------------------------
# Fold 1 — apostrophes (footlocker AF1 '07 / 6thstreet-noon Levi's)
# ---------------------------------------------------------------------------

def test_af1_07_apostrophe_title_accepts():
    # footlocker GraphQL name + urlKey colourway enrichment (65 BHD inStock);
    # the query's bare "07" vs the title's "'07" was a one-sided year strip.
    title = "Nike Air Force 1 '07 White - Men's Shoes"
    assert strict_title_match("Nike Air Force 1 07 White", title) is True
    assert _sel("Nike Air Force 1 07 White", title) is True


def test_af1_07_typographic_apostrophe_accepts():
    title = "Nike Air Force 1 ’07 White - Men’s Shoes"
    assert strict_title_match("Nike Air Force 1 07 White", title) is True
    assert _sel("Nike Air Force 1 07 White", title) is True


def test_af1_shadow_still_rejects():
    # a DIFFERENT model-line flanker must not ride the year fold in
    assert _sel("Nike Air Force 1 07 White",
                "Nike Air Force 1 Shadow - Women's Shoes") is False


def test_bare_af1_query_still_tolerates_year_suffix():
    # pre-fold behaviour pin: "'07" stays NOISE for a query that omits it —
    # the fold must not turn the year suffix into a variant-add rejection.
    assert _sel("Nike Air Force 1", "Nike Air Force 1 '07 - Men's Shoes") is True


def test_air_max_number_is_identity_not_year():
    # the bare-year strip is LEADING-ZERO only — "95" is the model number.
    assert _sel("Nike Air Max 95", "Nike Air Max 95 - Men's Shoes") is True
    assert _sel("Nike Air Max 90", "Nike Air Max 95 - Men's Shoes") is False


def test_levis_501_apostrophe_title_accepts():
    # 6thstreet stored-title shape after the SKU-tail strip (24 BHD in_stock);
    # strict_title_match had NO apostrophe handling ("levis" not in "levi's").
    title = "Levi's 501 Original Fit Jeans - Black"
    assert strict_title_match("Levis 501 Original Fit Jeans", title) is True
    assert _sel("Levis 501 Original Fit Jeans", title) is True


def test_levis_501_typographic_apostrophe_accepts():
    # U+2019 survived even _fold_identity (token "levi’s") — both gates.
    title = "Levi’s 501 Original Fit Jeans - Black"
    assert strict_title_match("Levis 501 Original Fit Jeans", title) is True
    assert _sel("Levis 501 Original Fit Jeans", title) is True


def test_levis_502_still_rejects():
    title = "Levi's 502 Regular Taper Jeans - Black"
    assert strict_title_match("Levis 501 Original Fit Jeans", title) is False
    assert _sel("Levis 501 Original Fit Jeans", title) is False


# ---------------------------------------------------------------------------
# Fold 2 — Luxottica 0-prefix (namshi "0Rb3025")
# ---------------------------------------------------------------------------

def test_rb3025_luxottica_zero_prefix_accepts():
    # namshi PDP JSON-LD name (82.52 BHD InStock)
    title = "Ray-Ban 0Rb3025 Aviator Sunglasses"
    assert strict_title_match("Ray-Ban Aviator RB3025", title) is True
    assert _sel("Ray-Ban Aviator RB3025", title) is True


def test_rb3026_still_rejects():
    title = "Ray-Ban 0Rb3026 Aviator Sunglasses"
    assert strict_title_match("Ray-Ban Aviator RB3025", title) is False
    assert _sel("Ray-Ban Aviator RB3025", title) is False


def test_zero_prefix_fold_is_luxottica_scoped():
    # folds: 0rb/0rx + 3+ digits; everything else keeps its leading zero.
    toks = _identity_tokens_ps("Ray-Ban 0Rb3025 Aviator", "", "fashion")
    assert "rb3025" in toks and "0rb3025" not in toks
    toks = _identity_tokens_ps("Ray-Ban 0Rx5154 Clubmaster", "", "fashion")
    assert "rx5154" in toks and "0rx5154" not in toks
    # digits-only token: NOT folded (no rb/rx marker)
    assert "0801" in _identity_tokens_ps("Onitsuka Style 0801", "", "fashion")
    # ordinary model number untouched
    assert "501" in _identity_tokens_ps("Levis 501 Jeans", "", "fashion")


# ---------------------------------------------------------------------------
# Fold 3 — "Polo T-Shirt" compound (6thstreet Lacoste L1212)
# ---------------------------------------------------------------------------

def test_polo_tshirt_compound_accepts_polo_query():
    title = "Lacoste L1212 Polo T-Shirt"
    assert strict_title_match("Lacoste L1212 Polo", title) is True
    assert _sel("Lacoste L1212 Polo", title) is True


def test_polo_t_shirt_spaced_compound_accepts_polo_query():
    assert _sel("Lacoste L1212 Polo", "Lacoste L1212 Polo T Shirt") is True


def test_bare_tshirt_candidate_still_rejects_polo_query():
    # the collapse fires ONLY on the compound — a tee is not a polo.
    assert _sel("Lacoste L1212 Polo", "Lacoste L1212 T-Shirt") is False
    assert _sel("Lacoste L1212 Polo", "Nike Sportswear T-Shirt") is False


def test_polo_candidate_still_rejects_tshirt_query():
    assert _sel("Tommy Hilfiger Essential Flag T-Shirt",
                "Tommy Hilfiger Essential Flag Polo") is False


def test_polo_tshirt_compound_is_a_polo_not_a_tee():
    # the collapse TIGHTENS this direction: a "Polo T-Shirt" candidate is a
    # POLO, so a plain t-shirt query must class-swap-reject it (it previously
    # leaked through the shared "tshirt" token).
    assert _sel("Tommy Hilfiger Essential Flag T-Shirt",
                "Tommy Hilfiger Essential Flag Polo T-Shirt") is False


# ---------------------------------------------------------------------------
# Fold 1b (Wave B review MED, price_service.py strict_title_match) —
# candidate_brand APOSTROPHE fold. A2 folded apostrophes on both TEXT sides
# but brand_toks was built from the RAW candidate_brand, so an
# apostrophe-spelled retailer brand label ("Levi's" / "L'Oreal") never
# equalled the folded query brand token and failed to RELEASE it — the
# brand-omitting titles the A4 magento candidate_brand path exists to recover
# kept rejecting (magento Shape-B: title NOT brand-prepended).
# ---------------------------------------------------------------------------

def test_candidate_brand_apostrophe_releases_levis_token():
    # brand-omitting stored title + the retailer's own "Levi's" brand label:
    # the folded label must release the query's "levis" token.
    assert strict_title_match(
        "Levis 501 Original Fit Jeans", "501 Original Fit Jeans - Black",
        candidate_brand="Levi's",
    ) is True


def test_candidate_brand_typographic_apostrophe_releases():
    # U+2019 — the quote form retailer CMSes actually emit.
    assert strict_title_match(
        "Levis 501 Original Fit Jeans", "501 Original Fit Jeans - Black",
        candidate_brand="Levi’s",
    ) is True


def test_candidate_brand_loreal_apostrophe_releases():
    assert strict_title_match(
        "Loreal Elvive Hyaluron Pure Shampoo 400ml",
        "Elvive Hyaluron Pure Shampoo 400ml",
        candidate_brand="L'Oreal",
    ) is True


def test_wrong_candidate_brand_still_requires_query_brand():
    # ADVERSARIAL: a WRONG-brand candidate ("Levi's" label for a Wrangler
    # query) releases only ITS OWN tokens — the query brand stays required
    # and the brand-omitting title still rejects. The fold must not leak.
    assert strict_title_match(
        "Wrangler 501 Original Fit Jeans", "501 Original Fit Jeans - Black",
        candidate_brand="Levi's",
    ) is False
    assert _sel(
        "Wrangler 501 Original Fit Jeans", "501 Original Fit Jeans - Black",
        candidate_brand="Levi's",
    ) is False
