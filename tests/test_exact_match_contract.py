# -*- coding: utf-8 -*-
"""Contract tests for the shared `is_exact_match` identity gate (Wave B).

`is_exact_match` does NOT exist yet on the b207bfa base — it is the
single shared set-EQUALITY identity gate the genuine-price CORRECTNESS build
adds in Wave B (see docs/plans/2026-06-27-genuine-price-correctness-IMPL-SPEC.md,
the "THE SHARED HELPERS" section + the per-category axis table).

Signature (PINNED by the IMPL-SPEC):
    is_exact_match(query_name: str, candidate_title: str,
                   category: Optional[str], *, candidate_brand: str = "") -> bool

Returns True iff `candidate_title` is the SAME product as `query_name`
(model + concentration + size/storage + variant + count), False otherwise.

TDD posture:
  * EVERY test below is RED (new-helper) on CURRENT code — the symbol does not
    exist, so the in-body `from app.services.price_service import is_exact_match`
    raises ImportError. The import is INSIDE each test body (not module-level) so
    pytest COLLECTION never errors; the test fails at run time = a real red until
    Wave B lands the function.
  * REJECT tests assert the gate returns False on a WRONG SKU — the no-fab
    correctness requirement (no S24->S24 FE, EDP->EDT, flanker, count drift).
  * ACCEPT tests assert the gate returns True on a LEGIT alias wording — the
    anti-over-rejection guard (the strict gate must NOT false-pend genuine
    listings: brand-omitted sephora titles, EDT abbreviation, oz<->ml, diacritics,
    storage-absent-in-query, 2-digit model survival).

After Wave B: the REJECT tests must pass (gate rejects) AND the ACCEPT tests must
pass (gate accepts) — both directions are the contract.
"""

import pytest


# ===========================================================================
# REJECT — wrong SKU must NOT match (no-fab correctness). # RED (new-helper)
# ===========================================================================

def test_electronics_s24_vs_s24_fe_rejected():  # RED (new-helper)
    """Samsung Galaxy S24 != Samsung Galaxy S24 FE (the warm-cache bug:
    S24 256GB resolved to an S24 FE listing). The "FE" variant qualifier
    breaks identity even though storage is equal and the base name is a
    prefix of the candidate."""
    from app.services.price_service import is_exact_match
    assert is_exact_match(
        "Samsung Galaxy S24 256GB",
        "Samsung Galaxy S24 FE 256GB",
        "electronics",
    ) is False


def test_electronics_storage_mismatch_rejected():  # RED (new-helper)
    """256GB query must NOT match a 128GB candidate — storage is an identity
    axis for electronics when the query states it."""
    from app.services.price_service import is_exact_match
    assert is_exact_match(
        "Samsung Galaxy S24 256GB",
        "Samsung Galaxy S24 128GB",
        "electronics",
    ) is False


def test_electronics_iphone_15_vs_15_pro_max_rejected():  # RED (new-helper)
    """iPhone 15 != iPhone 15 Pro Max — the Pro/Max variant qualifiers are
    in the candidate but not the query (base-model-as-prefix-of-variant bug)."""
    from app.services.price_service import is_exact_match
    assert is_exact_match(
        "iPhone 15",
        "iPhone 15 Pro Max",
        "electronics",
    ) is False


def test_fragrance_edp_vs_edt_rejected():  # RED (new-helper)
    """Bleu de Chanel EDP 100ml != Bleu de Chanel EDT 100ml — concentration is
    an identity axis for fragrances (the EDP->EDT warm-cache bug). The
    identity token sets are equal AFTER concentration-stripping, so the gate
    must reject on the SEPARATE concentration axis, not on tokens."""
    from app.services.price_service import is_exact_match
    assert is_exact_match(
        "Bleu de Chanel EDP 100ml",
        "Bleu de Chanel EDT 100ml",
        "fragrances",
    ) is False


def test_fragrance_size_mismatch_rejected():  # RED (new-helper)
    """100ml query must NOT match a 30ml candidate — size (ml) is an identity
    axis for fragrances when the query states it (kills the sample/decant leak)."""
    from app.services.price_service import is_exact_match
    assert is_exact_match(
        "Bleu de Chanel EDP 100ml",
        "Bleu de Chanel EDP 30ml",
        "fragrances",
    ) is False


def test_fragrance_flanker_rejected():  # RED (new-helper)
    """YSL Black Opium != Black Opium Over Red — the flanker has an EXTRA
    identity token ({over, red}) so the identity sets are NOT equal. This is
    the exact flanker leak the loose-0.5-overlap matcher shipped."""
    from app.services.price_service import is_exact_match
    assert is_exact_match(
        "YSL Black Opium EDP 90ml",
        "YSL Black Opium Over Red EDP 90ml",
        "fragrances",
    ) is False


def test_supplements_count_mismatch_rejected():  # RED (new-helper)
    """Now Vitamin D3 120 softgels != Now Vitamin D3 240 softgels — count is an
    identity axis for supplements when the query states it."""
    from app.services.price_service import is_exact_match
    assert is_exact_match(
        "Now Vitamin D3 120 softgels",
        "Now Vitamin D3 240 softgels",
        "supplements",
    ) is False


# ===========================================================================
# ACCEPT — legit alias wording must STILL match (anti-over-rejection). # GREEN
# (intent: must PASS after Wave B; RED on current code = ImportError)
# ===========================================================================

def test_electronics_storage_absent_in_query_accepted():  # GREEN
    """Query omits storage ("Samsung Galaxy S24") — a 256GB candidate must
    still match (absent-axis policy: an axis the QUERY omits does not reject;
    selection ranks a canonical basis later, never cheapest)."""
    from app.services.price_service import is_exact_match
    assert is_exact_match(
        "Samsung Galaxy S24",
        "Samsung Galaxy S24 256GB",
        "electronics",
    ) is True


def test_fragrance_edt_abbreviation_accepted():  # GREEN
    """"EDT" query must match a "Eau de Toilette" candidate — same concentration,
    different wording (alias). Both collapse to EDT via _CONCENTRATION_PATTERNS."""
    from app.services.price_service import is_exact_match
    assert is_exact_match(
        "Dior Sauvage EDT 100ml",
        "Dior Sauvage Eau de Toilette 100ml",
        "fragrances",
    ) is True


def test_fragrance_oz_equals_ml_accepted():  # GREEN
    """"100ml" query must match a "3.4 oz" candidate — oz snaps to the standard
    100ml bottle (extract_size_ml_any). Same size, different unit wording."""
    from app.services.price_service import is_exact_match
    assert is_exact_match(
        "Dior Sauvage EDT 100ml",
        "Dior Sauvage Eau de Toilette 3.4 oz",
        "fragrances",
    ) is True


def test_fragrance_diacritics_accepted():  # GREEN
    """"Acqua di Gio" (plain ASCII) must match "Acqua di Giò Eau de Toilette"
    (accented o) — diacritic-folded identity (the live-observed false-pend the
    _fold helper fixes). Brand "Giorgio Armani" is stripped from identity, and
    the query stating no concentration must not reject the EDT title."""
    from app.services.price_service import is_exact_match
    assert is_exact_match(
        "Acqua di Gio",
        u"Acqua di Giò Eau de Toilette",
        "fragrances",
        candidate_brand="Giorgio Armani",
    ) is True


def test_fragrance_brand_omitted_sephora_style_accepted():  # GREEN
    """Sephora-style title OMITS the brand: query "Marc Jacobs Daisy EDT 100ml",
    title "Daisy - Eau de Toilette 100ml", candidate_brand="Marc Jacobs".
    The gate must subtract the brand words from BOTH sides so the residual
    identity ({daisy}) matches — keeps the brand-aware sephora behaviour."""
    from app.services.price_service import is_exact_match
    assert is_exact_match(
        "Marc Jacobs Daisy EDT 100ml",
        "Daisy - Eau de Toilette 100ml",
        "fragrances",
        candidate_brand="Marc Jacobs",
    ) is True


def test_electronics_2digit_model_same_accepted():  # GREEN
    """iPhone 15 == iPhone 15 — a 2-digit model number ("15") must SURVIVE as
    identity (the Zyte len>2 gap drops bare 2-digit model numbers). Same model
    -> match."""
    from app.services.price_service import is_exact_match
    assert is_exact_match(
        "iPhone 15",
        "iPhone 15",
        "electronics",
    ) is True


def test_electronics_2digit_model_diff_rejected():  # RED (new-helper)
    """iPhone 15 != iPhone 14 — proof the 2-digit model number is a
    DISCRIMINATING identity axis, not dropped noise. If "15"/"14" were stripped
    (the Zyte len>2 bug), this would FALSELY match."""
    from app.services.price_service import is_exact_match
    assert is_exact_match(
        "iPhone 15",
        "iPhone 14",
        "electronics",
    ) is False
