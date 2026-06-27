"""Wave E — fixes for the adversarial-review findings (genuine-price CORRECTNESS).

Each test pins a finding the review VERIFIED against the real code:
- H2 (HIGH): supplement strength (mg/IU) is a discriminating axis (wrong-dose must reject).
- L5 : weight/volume (g/ml) is a discriminating axis (wrong-weight must reject).
- H3 (HIGH): a GENERIC category noun (smartphone/headphones/perfume/protein) that a terse
  genuine listing omits must NOT false-pend the match (over-rejection).
- M3 : fashion colour-wording variance must not false-pend (fashion is permissive).
- M7 : reselect_to_target_value (non-fragrance fairness) must skip OOS + wrong-variant.
- L3 : is_available_state must handle spaced 'Out of Stock' / 'Sold Out' + PreSale.

# RED on the current branch (pre-Wave-E); pass after the fixes.
"""
from app.services.price_service import (
    is_exact_match, _selection_match, is_available_state, reselect_to_target_value,
)


# --- H2: supplement strength axis ------------------------------------------ #
def test_supplement_wrong_strength_rejected():  # RED
    assert is_exact_match("Now Vitamin D3 5000 IU 120 softgels",
                          "Now Vitamin D3 1000 IU 120 softgels", "supplements") is False


def test_supplement_same_strength_accepted():  # GREEN
    assert is_exact_match("Now Vitamin D3 5000 IU 120 softgels",
                          "Now Vitamin D3 5000 IU 120 softgels", "supplements") is True


# --- L5: weight/volume axis ------------------------------------------------ #
def test_skincare_wrong_weight_rejected():  # RED
    assert is_exact_match("CeraVe Moisturizing Cream 50g",
                          "CeraVe Moisturizing Cream 340g", "skincare") is False


def test_skincare_same_weight_accepted():  # GREEN
    assert is_exact_match("CeraVe Moisturizing Cream 340g",
                          "CeraVe Moisturizing Cream 340g", "skincare") is True


# --- H3: generic category noun must not false-pend (over-rejection) --------- #
def test_generic_noun_smartphone_not_pended():  # RED
    assert _selection_match("Samsung Galaxy S24 256GB Smartphone",
                            "Samsung Galaxy S24 256GB", "electronics") is True


def test_generic_noun_headphones_not_pended():  # RED
    assert _selection_match("Sony WH-1000XM5 Headphones",
                            "Sony WH-1000XM5", "electronics") is True


def test_generic_noun_protein_not_pended():  # RED
    assert _selection_match("Optimum Nutrition Gold Standard Whey Protein 5lb",
                            "Optimum Nutrition Gold Standard Whey 5lb", "supplements") is True


def test_distinctive_missing_token_still_rejected():  # GREEN — H3 must NOT over-relax
    # A MISSING DISTINCTIVE token (a different model) still rejects.
    assert _selection_match("Sony WH-1000XM5", "Sony WF-1000XM5", "electronics") is False


# --- M3: fashion colour aliasing works when category=='fashion' is passed --- #
# NOTE: making _infer_category_from_query DETECT fashion (so this engages in prod)
# is DEFERRED — a safe fashion detector is hard (brand overlap + grocery colour
# names like "Red Apple" vs "Green Apple" risk false matches). Fashion is a
# permissive category; the common over-rejection (generic nouns) is fixed by H3.
def test_fashion_color_alias_when_category_passed():  # GREEN (documents the branch)
    assert _selection_match("Adidas Samba OG White", "Adidas Samba OG", "fashion") is True


# --- M7: reselect_to_target_value skips OOS + wrong-variant ----------------- #
def _vcand(amount, title, in_stock=True, sm="local_bhd", variant_rank=0.0):
    # reselect_to_target_value reads the comparable-unit value (storage GB) from the
    # title via _candidate_value; the price/amount lives in raw_data.
    return {"title": title, "source_method": sm, "in_stock": in_stock,
            "retailer": "x.com", "variant_rank": variant_rank,
            "raw_data": {"amount": amount, "currency": "BHD", "source_method": sm,
                         "title": title, "retailer": "x.com", "in_stock": in_stock}}


def test_reselect_value_skips_out_of_stock():  # RED
    cands = [_vcand(540.0, "Samsung Galaxy S24 256GB", in_stock=False)]
    out = reselect_to_target_value("Samsung Galaxy S24 256GB", cands, 256.0, "electronics")
    assert out is None


# --- L3: availability display-string + future states ----------------------- #
def test_availability_spaced_strings():  # RED
    assert is_available_state("Out of Stock") is False
    assert is_available_state("Sold Out") is False


def test_availability_presale_is_future():  # RED
    assert is_available_state("https://schema.org/PreSale") is False
