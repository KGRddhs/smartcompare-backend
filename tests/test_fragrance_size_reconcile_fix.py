"""frag-size-reconcile fix — a genuine fragrance PAIR where neither/one side is
brand-keyword-recognized was wrongly NULLED by reconcile_pair_sizes.

ROOT CAUSE: genuine adapter prices (woo/magento/noon) carry NO price["size"] and
their title has no `\\d+ml` token. effective_pair_size_ml only defaulted a
size-UNSPECIFIED product to the flagship 100ml basis when
_is_designer_fragrance_name(name) was True (name contains a FRAGRANCE_BRAND_KEYWORD
or is luxury). A genuine fragrance from an unlisted house ("Armaf Club de Nuit",
"Nishane Hacivat") returned None -> target_pair_size_ml's both-designer gate failed
-> the legacy branch saw 100 (recognized side) != None (unrecognized side) ->
BOTH pended, nulling a correct genuine price.

FIX (approach c, flag-gated): reconcile_pair_fairness passes
treat_unsized_as_flagship=frag_reconcile_fix_enabled() into reconcile_pair_sizes
on the canon=="fragrances" path. The orchestrator has already established the pair
is a fragrance, so an UNSIZED product defaults to the flagship 100ml basis even
without a brand-keyword name match. It ONLY broadens the unsized case — any
explicit `\\d+ml` token on either side is used verbatim, so a genuine 30ml/50ml
still resolves + still PENDS vs a 100ml partner.

FLAG: ENABLE_FRAGRANCE_SIZE_RECONCILE_FIX, default OFF -> byte-identical to today.

Run: pytest tests/test_fragrance_size_reconcile_fix.py -v
"""
import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

import pytest

from app.services.price_service import (
    reconcile_pair_sizes,
    reconcile_pair_fairness,
    effective_pair_size_ml,
    target_pair_size_ml,
)


def _prod(name, amount, *, price_size=None, specs=None,
          source_method="woo_store_api", title=None):
    """A GENUINE adapter-shaped product: price.size is None + no ml token in the
    title (matches woo/magento/noon)."""
    price = {
        "amount": amount, "currency": "BHD",
        "source_method": source_method, "size": price_size,
        "in_stock": True,
    }
    if title is not None:
        price["title"] = title
    return {
        "name": name, "full_name": name,
        "price": price,
        "best_price": amount,
        "retailer": "someshop.bh",
        "specs": specs or {},
    }


@pytest.fixture
def flag_on(monkeypatch):
    monkeypatch.setenv("ENABLE_FRAGRANCE_SIZE_RECONCILE_FIX", "true")


@pytest.fixture
def flag_off(monkeypatch):
    monkeypatch.setenv("ENABLE_FRAGRANCE_SIZE_RECONCILE_FIX", "false")


# ============================================================
# FLAG ON — the fix recovers wrongly-pended genuine pairs
# ============================================================
class TestFlagOnRecoversGenuinePairs:
    def test_recognized_plus_unrecognized_unsized_shows_both(self, flag_on):
        # THE bug: Creed (recognized -> 100) + Armaf (unrecognized -> None today).
        # With the fix both default to the flagship basis -> fair -> show both.
        pd = [
            _prod("Creed Aventus", 90.0),
            _prod("Armaf Club de Nuit Intense", 35.0),
        ]
        changed = reconcile_pair_fairness(pd, None, "fragrances")
        assert changed is False
        assert pd[0]["price"]["amount"] == 90.0
        assert pd[1]["price"]["amount"] == 35.0
        assert pd[0]["price"].get("unavailable") is not True
        assert pd[1]["price"].get("unavailable") is not True

    def test_both_unrecognized_unsized_shows_both(self, flag_on):
        # Two genuine niche fragrances, neither in the keyword list, both unsized.
        pd = [
            _prod("Nishane Hacivat", 60.0),
            _prod("Armaf Club de Nuit Intense", 35.0),
        ]
        changed = reconcile_pair_fairness(pd, None, "fragrances")
        assert changed is False
        assert pd[0]["price"]["amount"] == 60.0
        assert pd[1]["price"]["amount"] == 35.0

    def test_via_reconcile_pair_sizes_directly(self, flag_on):
        # Direct reconcile_pair_sizes with the flag param wired True.
        pd = [
            _prod("Creed Aventus", 90.0),
            _prod("Armaf Club de Nuit Intense", 35.0),
        ]
        changed = reconcile_pair_sizes(pd, treat_unsized_as_flagship=True)
        assert changed is False
        assert pd[0]["price"]["amount"] == 90.0
        assert pd[1]["price"]["amount"] == 35.0


# ============================================================
# FLAG ON — the correctness guards STAY intact
# ============================================================
class TestFlagOnGuardsIntact:
    def test_explicit_different_sizes_still_pend(self, flag_on):
        # A confirmed 30ml travel vs a 100ml full bottle GENUINELY differ ->
        # still pend the off-target 30ml. NEVER show two different sizes as
        # comparable just because the fix defaults unsized -> flagship.
        pd = [
            _prod("Nishane Hacivat 100ml", 100.0),
            _prod("Armaf Club de Nuit 30ml", 20.0),
        ]
        changed = reconcile_pair_fairness(pd, None, "fragrances")
        assert changed is True
        assert pd[0]["price"]["amount"] == 100.0            # 100ml = target, kept
        assert pd[1]["price"]["amount"] is None             # 30ml off-target -> pended
        assert pd[1]["price"]["reason"] == "size_mismatch"

    def test_unsized_flagship_vs_explicit_30ml_pends_the_30(self, flag_on):
        # One side unsized (-> 100 via the fix), the other explicitly 30ml.
        # 30 != 100 -> pend ONLY the 30ml side; the unsized-flagship side shows.
        pd = [
            _prod("Armaf Club de Nuit Intense", 35.0),
            _prod("Nishane Hacivat 30ml", 22.0),
        ]
        changed = reconcile_pair_fairness(pd, None, "fragrances")
        assert changed is True
        assert pd[0]["price"]["amount"] == 35.0
        assert pd[1]["price"]["amount"] is None
        assert pd[1]["price"]["reason"] == "size_mismatch"

    def test_both_explicit_off_flagship_different_both_pend(self, flag_on):
        # 50ml vs 30ml, no candidates to reach a common basis -> both pend
        # (the fix must not force these to 100).
        pd = [
            _prod("Armaf Club de Nuit 50ml", 40.0),
            _prod("Nishane Hacivat 30ml", 22.0),
        ]
        changed = reconcile_pair_fairness(pd, None, "fragrances")
        assert changed is True
        assert pd[0]["price"]["amount"] is None
        assert pd[1]["price"]["amount"] is None

    def test_user_query_size_still_authoritative(self, flag_on):
        # User typed "50ml" -> target 50; both unsized products can't reach 50
        # -> both pend (the fix does not override an explicit user size to 100).
        pd = [
            _prod("Armaf Club de Nuit Intense", 35.0),
            _prod("Nishane Hacivat", 60.0),
        ]
        changed = reconcile_pair_fairness(
            pd, "Armaf Club de Nuit vs Nishane Hacivat 50ml", "fragrances"
        )
        assert changed is True
        assert pd[0]["price"]["amount"] is None
        assert pd[1]["price"]["amount"] is None

    def test_non_fragrance_category_untouched(self, flag_on):
        # Electronics still never gets the flagship default (the flag only wires
        # through on canon=="fragrances").
        pd = [
            _prod("iPhone 15 Pro", 400.0, source_method="local_bhd"),
            _prod("Galaxy S24 Ultra", 450.0, source_method="local_bhd"),
        ]
        changed = reconcile_pair_fairness(pd, None, "electronics")
        assert pd[0]["price"]["amount"] == 400.0
        assert pd[1]["price"]["amount"] == 450.0


# ============================================================
# FLAG OFF — byte-identical to today (the bug reproduces)
# ============================================================
class TestFlagOffByteIdentical:
    def test_recognized_plus_unrecognized_unsized_still_pends_both(self, flag_off):
        # The pre-fix behavior: BOTH nulled (the very bug we fix). Flag OFF must
        # reproduce it exactly.
        pd = [
            _prod("Creed Aventus", 90.0),
            _prod("Armaf Club de Nuit Intense", 35.0),
        ]
        changed = reconcile_pair_fairness(pd, None, "fragrances")
        assert changed is True
        assert pd[0]["price"]["amount"] is None
        assert pd[1]["price"]["amount"] is None
        assert pd[1]["price"]["reason"] == "size_mismatch"

    def test_effective_size_default_off(self, flag_off):
        # treat_unsized_as_flagship default False -> unrecognized unsized -> None.
        p = _prod("Armaf Club de Nuit Intense", 35.0)
        assert effective_pair_size_ml(p) is None

    def test_target_default_off(self, flag_off):
        p0 = _prod("Armaf Club de Nuit Intense", 35.0)
        p1 = _prod("Nishane Hacivat", 60.0)
        assert target_pair_size_ml(None, p0, p1) is None


# ============================================================
# Recognized-pair regression — the surviving pair still shows on BOTH states
# ============================================================
class TestRecognizedPairStillShows:
    @pytest.mark.parametrize("flag_val", ["true", "false"])
    def test_recognized_designer_pair_shows(self, monkeypatch, flag_val):
        # Baccarat Rouge (mfk-recognized via brand token) + Layton (parfums de
        # marly). Both -> 100 via _is_designer_fragrance_name on both flag states.
        monkeypatch.setenv("ENABLE_FRAGRANCE_SIZE_RECONCILE_FIX", flag_val)
        pd = [
            _prod("Maison Francis Kurkdjian Baccarat Rouge 540", 120.0),
            _prod("Parfums de Marly Layton", 95.0),
        ]
        changed = reconcile_pair_fairness(pd, None, "fragrances")
        assert changed is False
        assert pd[0]["price"]["amount"] == 120.0
        assert pd[1]["price"]["amount"] == 95.0


# ============================================================
# effective_pair_size_ml / target_pair_size_ml — explicit-size precedence with
# the flag param True (the broadening must NEVER override a real size token)
# ============================================================
class TestExplicitSizeWinsOverFlag:
    def test_effective_explicit_size_wins(self):
        p = _prod("Armaf Club de Nuit 30ml", 20.0)
        assert effective_pair_size_ml(p, True) == 30.0    # real size, not 100

    def test_effective_unsized_defaults_flagship_when_flagged(self):
        p = _prod("Armaf Club de Nuit Intense", 35.0)
        assert effective_pair_size_ml(p, True) == 100.0

    def test_effective_non_frag_still_none_without_flag(self):
        # A phone unsized stays None even conceptually — the flag param is only
        # ever True on the fragrance path, but assert the default is preserved.
        p = _prod("iPhone 15 Pro", 400.0, source_method="local_bhd")
        assert effective_pair_size_ml(p) is None

    def test_target_user_size_beats_flag(self):
        p0 = _prod("Armaf Club de Nuit Intense", 35.0)
        p1 = _prod("Nishane Hacivat", 60.0)
        assert target_pair_size_ml("something 50ml", p0, p1, True) == 50.0
