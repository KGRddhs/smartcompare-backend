"""M6 UNIT C1 — normalize_words empty-token fix (PART A) + sitemap matcher
relax behind ENABLE_SITEMAP_MATCH_V2 (PART B).

PART A — the empty-token bug (price_service.normalize_words):
    ``normalize_words`` filters on the UN-replaced token, so a lone ``"-"`` (from
    a spaced hyphen ``" - "``) passes the ``w.strip(punct)`` filter but its value
    ``"-".replace("-", "")`` is ``""`` — a phantom empty-string token joins the
    set. Because ``_slug_from_pdp`` turns hyphens into spaces, no slug token set
    ever contains ``""``, so ``q_words.issubset(s_words)`` is ALWAYS False for a
    query carrying ``" - "`` → a guaranteed MISS. Gated behind
    ENABLE_NORMALIZE_WORDS_EMPTY_FIX (default OFF); flag-OFF is byte-identical.

PART B — the sitemap matcher relax (sitemap_discovery_service._match_sitemap_slug):
    the shipped matcher demands strict ``q_words.issubset(s_words)``; real JSON-LD
    ``Product.name`` values carry brand / gender / size tokens the URL slug omits.
    ENABLE_SITEMAP_MATCH_V2 (default OFF) relaxes the SITEMAP matcher toward the
    overlap-ratio score it already computes AND drops phantom empty tokens locally,
    keeping the fail-closed "return None, never a wrong URL" property.

No live network — the matcher is a pure ``{slug: url}``-dict function.
"""

import pytest

import app.services.sitemap_discovery_service as sd
from app.services.price_service import normalize_words

_A_FLAG = "ENABLE_NORMALIZE_WORDS_EMPTY_FIX"
_B_FLAG = "ENABLE_SITEMAP_MATCH_V2"


# ===========================================================================
# PART A — normalize_words empty-token bug
# ===========================================================================
class TestNormalizeWordsEmptyToken:
    def test_flag_off_is_byte_identical_phantom_empty_survives(self, monkeypatch):
        """Flag OFF (unset) preserves the exact shipped behavior: a spaced hyphen
        injects a phantom ``""`` token."""
        monkeypatch.delenv(_A_FLAG, raising=False)
        words = normalize_words("dior sauvage - edt")
        assert "" in words  # shipped bug, preserved when the flag is OFF
        assert words == {"dior", "sauvage", "edt", ""}

    def test_flag_on_drops_the_phantom_empty(self, monkeypatch):
        monkeypatch.setenv(_A_FLAG, "on")
        words = normalize_words("dior sauvage - edt")
        assert "" not in words
        assert words == {"dior", "sauvage", "edt"}

    def test_flag_on_recovers_issubset_against_a_slug(self, monkeypatch):
        """The measured failure: a ``" - "`` query is never a subset of the slug
        tokens (hyphens already folded to spaces). The fix restores the subset."""
        slug_words = normalize_words("khamrah qahwa")  # _slug_from_pdp output
        monkeypatch.delenv(_A_FLAG, raising=False)
        assert not normalize_words("Khamrah - Qahwa").issubset(slug_words)  # bug
        monkeypatch.setenv(_A_FLAG, "on")
        assert normalize_words("Khamrah - Qahwa").issubset(slug_words)  # fixed

    def test_no_hyphen_text_is_identical_on_and_off(self, monkeypatch):
        """The fix ONLY drops empties — a query with no spaced hyphen tokenizes
        identically flag-ON and flag-OFF (the common path is untouched)."""
        monkeypatch.delenv(_A_FLAG, raising=False)
        off = normalize_words("dior sauvage edt 100ml")
        monkeypatch.setenv(_A_FLAG, "on")
        on = normalize_words("dior sauvage edt 100ml")
        assert off == on == {"dior", "sauvage", "edt", "100ml"}

    def test_flag_on_folds_all_hyphen_only_tokens(self, monkeypatch):
        """Multi-hyphen / punct+hyphen tokens also collapse to empties under the
        shipped code and are dropped by the fix."""
        monkeypatch.setenv(_A_FLAG, "on")
        assert "" not in normalize_words("a -- b")
        assert normalize_words("a -- b") == {"a", "b"}


# ===========================================================================
# PART B — sitemap matcher relax (ENABLE_SITEMAP_MATCH_V2)
# ===========================================================================
# A representative {slug: url} index. Keys are `_slug_from_pdp` output (hyphens
# already folded to spaces).
INDEX = {
    # Empty-token suppressed hits (M5: tuzzut, samawa) — the JSON-LD name carries
    # a spaced hyphen the slug does not.
    "khamrah qahwa": "https://www.tuzzut.com/products/khamrah-qahwa",
    "yara moi": "https://www.samawa.ae/products/yara-moi",
    # Extra brand/gender/size token target (M5: coral) — the slug omits the store
    # brand prefix the JSON-LD name carries.
    "blue oud edp 100ml": "https://coralperfumes.com/products/blue-oud-edp-100ml",
    # A genuinely different product present in the same index.
    "dyson airwrap complete": "https://example.com/products/dyson-airwrap-complete",
}


class TestSitemapMatcherV2Off:
    """Flag OFF — the shipped strict matcher is preserved byte-for-byte."""

    @pytest.fixture(autouse=True)
    def _flags_off(self, monkeypatch):
        monkeypatch.delenv(_B_FLAG, raising=False)
        monkeypatch.delenv(_A_FLAG, raising=False)

    def test_empty_token_query_misses(self):
        # phantom "" → issubset always False → guaranteed MISS (the shipped bug)
        assert sd._match_sitemap_slug(INDEX, "Khamrah - Qahwa") is None

    def test_extra_brand_token_query_misses(self):
        # strict issubset fails: "coral"/"perfumes" are not in the slug tokens
        assert sd._match_sitemap_slug(INDEX, "Coral Perfumes Blue Oud EDP 100ml") is None

    def test_clean_subset_still_hits(self):
        # a clean subset with no spaced hyphen and no extra tokens still resolves
        assert (
            sd._match_sitemap_slug(INDEX, "Blue Oud EDP 100ml")
            == INDEX["blue oud edp 100ml"]
        )

    def test_different_product_returns_none(self):
        assert sd._match_sitemap_slug(INDEX, "Chanel No 5 Parfum") is None


class TestSitemapMatcherV2On:
    """Flag ON — the relaxed overlap matcher recovers the M5 cases while staying
    fail-closed. PART A flag is left OFF to prove PART B is self-contained."""

    @pytest.fixture(autouse=True)
    def _v2_on(self, monkeypatch):
        monkeypatch.setenv(_B_FLAG, "on")
        monkeypatch.delenv(_A_FLAG, raising=False)  # PART A flag OFF on purpose

    def test_empty_token_suppressed_hit_recovers_tuzzut(self):
        assert (
            sd._match_sitemap_slug(INDEX, "Khamrah - Qahwa")
            == INDEX["khamrah qahwa"]
        )

    def test_empty_token_suppressed_hit_recovers_samawa(self):
        assert sd._match_sitemap_slug(INDEX, "Yara - Moi") == INDEX["yara moi"]

    def test_extra_brand_gender_size_token_resolves_own_pdp(self):
        assert (
            sd._match_sitemap_slug(INDEX, "Coral Perfumes Blue Oud EDP 100ml")
            == INDEX["blue oud edp 100ml"]
        )

    def test_genuinely_different_product_still_returns_none(self):
        assert sd._match_sitemap_slug(INDEX, "Chanel No 5 Parfum") is None

    def test_size_mismatch_stays_fail_closed(self):
        # the size guard survives the relax: a 50ml query must not bind a 100ml slug
        assert sd._match_sitemap_slug(INDEX, "Blue Oud EDP 50ml") is None

    def test_low_overlap_stays_fail_closed(self):
        # sharing only a generic token ("oud") is below the overlap floor → None
        assert sd._match_sitemap_slug(INDEX, "Rose Oud") is None
