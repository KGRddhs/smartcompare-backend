"""M21 currency-parity unit (M18 findings CD-wave-diffs-03 / -07 / -08).

Three canary preconditions for the W2 currency flag family:

- CD-wave-diffs-03: ``_seed_shortcircuit_candidates`` (the M13-10 re-selection
  stash) got the parse parity but NOT the two M13-09 strict-shopping guards, so
  with ENABLE_SHOPPING_STRICT_CURRENCY ON the back door still admits the exact
  foreign-currency row the front door (``extract_price_from_shopping``) pends.
  The two guards are factored into one shared admission helper
  (``shopping_strict_currency_pend``) both paths call.

- CD-wave-diffs-07: the strict-shopping guards OVER-pend two genuine shapes:
  (a) "US$ 25.99" — the letter-dollar regex matches the S of "US" even though
  the standard international USD notation was detected CORRECTLY; (b) an
  Arabic-Indic-numeral target glyph ("١٢٣ ر.س" on a SAR ask) — the residue
  strip was ASCII-[0-9]-only, so the digits survived into the residue and hit
  the non-ASCII catch-all.

- CD-wave-diffs-08: ENABLE_EXTENDED_FALLBACK_RATES reached ``_convert_to_bhd``
  but NOT the Shopify-catalog convertibility gate in
  ``price_service._match_shopify_product``, so a TRY-base store still skipped
  with the flag ON (a canary of the flag under-measures it). The other adapter
  gates (shopify_pdp/algolia/magento/occ/rest_json/unbxd/woocommerce/salla)
  live outside this unit's lane and are reported, not changed.

Everything here is flag-gated: with the wave flags OFF every path is
byte-identical to base (pinned below). ENABLE_EXACT_PRICE_GATE=false isolates
extraction (no network anywhere in this file).
"""
import pytest

from app.services import price_service as ps
from app.services.structured_comparison_service import get_comparison_service

NAME = "Acme Widget Deluxe"


def _seed(monkeypatch, price_str, *, currency="BHD", strict="true"):
    """Run the tier1_shopping stash over ONE item; return the seeded candidates."""
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "false")
    monkeypatch.setenv("ENABLE_SHOPPING_STRICT_CURRENCY", strict)
    svc = get_comparison_service()
    svc._shopping_items_cache[NAME] = [{
        "title": NAME, "price": price_str,
        "source": "noon.com", "link": "https://noon.com/p",
    }]
    svc._seed_shortcircuit_candidates(
        NAME, kind="tier1_shopping", currency=currency, shopping_region="bahrain",
    )
    return svc._price_candidates.get(NAME, [])


def _main(monkeypatch, price_str, *, currency="BHD", strict="true"):
    """Run the SAME item through the main path (extract_price_from_shopping)."""
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "false")
    monkeypatch.setenv("ENABLE_SHOPPING_STRICT_CURRENCY", strict)
    item = {
        "title": NAME, "price": price_str,
        "source": "noon.com", "link": "https://noon.com/p",
    }
    return ps.extract_price_from_shopping(
        NAME, [item], currency, shopping_region="bahrain",
    )


class TestSeedStrictParity:
    """CD-wave-diffs-03 — the stash applies the SAME strict-currency admission
    rule as the front door, under the same flag."""

    def test_seed_pends_unresolved_foreign_glyph_flag_on(self, monkeypatch):
        """Strict ON: a UAE glyph on a BHD ask pends on the main path — the
        stash must NOT seed it for fairness re-selection."""
        assert _main(monkeypatch, "1,399 د.إ") is None  # front door pends
        assert _seed(monkeypatch, "1,399 د.إ") == []    # back door must too

    def test_seed_pends_letter_dollar_flag_on(self, monkeypatch):
        """Strict ON: 'R$' is BRL, detect_currency's USD is bogus — the main
        path pends; the stash must not convert BRL as USD and seed it."""
        assert _main(monkeypatch, "R$ 25.99") is None
        assert _seed(monkeypatch, "R$ 25.99") == []

    def test_seed_ships_target_glyph_flag_on(self, monkeypatch):
        """Strict ON: a TARGET-currency glyph ('د.إ' on an AED ask) is genuine
        — the mirror lets it through on both paths (no over-pend)."""
        cands = _seed(monkeypatch, "25.99 د.إ", currency="AED")
        assert cands, "target-currency glyph must still seed"

    def test_seed_unchanged_flag_off(self, monkeypatch):
        """Strict OFF: byte-identity — the stash seeds the glyph row exactly as
        it does at base (the guard is gated, never unconditional)."""
        cands = _seed(monkeypatch, "1,399 د.إ", strict="false")
        assert cands and cands[0]["value"] == 1399.0

    def test_seed_plain_row_unaffected_flag_on(self, monkeypatch):
        """Strict ON: an ordinary target-currency row still seeds (the guard
        only pends what the front door pends)."""
        cands = _seed(monkeypatch, "BHD 12,500")
        assert cands and cands[0]["value"] == 12.5


class TestLetterDollarOverPend:
    """CD-wave-diffs-07(a) — 'US$' is the standard international USD notation;
    detect_currency's USD is CORRECT and must not pend."""

    def test_us_dollar_notation_ships_flag_on(self, monkeypatch):
        res = _main(monkeypatch, "US$ 25.99")
        assert res is not None, "US$ notation must not be pended"
        assert res["source_method"] == "converted_usd"  # honest label: USD != BHD

    def test_u_s_dollar_notation_ships_flag_on(self, monkeypatch):
        assert _main(monkeypatch, "U.S.$ 25.99") is not None

    def test_r_dollar_still_pends_flag_on(self, monkeypatch):
        """Guard-rail: the fix is US$-specific — R$ (BRL) still pends."""
        assert _main(monkeypatch, "R$ 25.99") is None

    def test_aus_dollar_still_pends_flag_on(self, monkeypatch):
        """'AUS$' keeps the letter-dollar pend (the whitelist requires the U
        not be letter-preceded, so 'AUS$' is not treated as US notation)."""
        assert _main(monkeypatch, "AUS$ 25.99") is None

    def test_bare_dollar_ships_flag_on(self, monkeypatch):
        assert _main(monkeypatch, "$ 25.99") is not None

    def test_seed_parity_us_dollar_flag_on(self, monkeypatch):
        """The shared helper keeps the stash in lockstep: US$ seeds too."""
        assert _seed(monkeypatch, "US$ 25.99")


class TestArabicIndicResidue:
    """CD-wave-diffs-07(b) — Arabic-Indic digits (U+0660-0669) and the Arabic
    separators U+066B/U+066C must be stripped from the residue like ASCII
    digits, so a genuine target glyph with Arabic-Indic numerals is not pended
    by the non-ASCII catch-all."""

    def test_arabic_indic_target_glyph_not_foreign(self):
        assert ps._shopping_foreign_currency_signal(
            "١٢٣ ر.س", "SAR",
        ) is False

    def test_ascii_digit_target_glyph_not_foreign(self):
        """Unchanged behavior: the ASCII twin was already False."""
        assert ps._shopping_foreign_currency_signal(
            "123 ر.س", "SAR",
        ) is False

    def test_arabic_indic_foreign_glyph_still_pends(self):
        """Guard-rail: a FOREIGN glyph with Arabic-Indic digits still signals."""
        assert ps._shopping_foreign_currency_signal(
            "١٢٣ د.إ", "BHD",
        ) is True

    def test_arabic_separators_stripped(self):
        """U+066B (decimal) / U+066C (thousands) are numeric punctuation, not
        currency residue."""
        assert ps._shopping_foreign_currency_signal(
            "١٬٢٣٤٫٥٠ ر.س",
            "SAR",
        ) is False

    def test_main_path_ships_arabic_indic_target_glyph_flag_on(self, monkeypatch):
        """End-to-end: strict ON, '١٢٣ ر.س' on a SAR ask ships (123.0)."""
        res = _main(monkeypatch, "١٢٣ ر.س", currency="SAR")
        assert res is not None
        assert res["amount"] == 123.0


class TestExtendedRatesReachShopifyCatalog:
    """CD-wave-diffs-08 — the Shopify-catalog convertibility gate consults the
    EFFECTIVE table, so ENABLE_EXTENDED_FALLBACK_RATES actually reaches it."""

    CATALOG = {
        "_store_currency": "TRY",
        "products": [{
            "title": NAME, "vendor": "Acme", "handle": "acme-widget-deluxe",
            "variants": [{"price": "5050.00", "title": "Default", "available": True}],
        }],
    }

    def test_try_store_converts_flag_on(self, monkeypatch):
        monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "false")
        monkeypatch.setenv("ENABLE_EXTENDED_FALLBACK_RATES", "true")
        res = ps._match_shopify_product(
            dict(self.CATALOG), NAME, "BHD", "acme-store.com",
        )
        assert res is not None, "TRY store must convert with the extended table ON"
        assert res["currency"] == "BHD"
        assert res["original_currency"] == "TRY"
        assert res["source_method"] == "converted_usd"
        from app.services.exchange_rate_service import effective_fallback_rates
        expected = 5050.0 * effective_fallback_rates()["TRY"]
        assert res["amount"] == pytest.approx(expected, rel=1e-6)

    def test_try_store_skips_flag_off(self, monkeypatch):
        """Byte-identity: flag OFF, the TRY store still skips (base table)."""
        monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "false")
        monkeypatch.setenv("ENABLE_EXTENDED_FALLBACK_RATES", "false")
        assert ps._match_shopify_product(
            dict(self.CATALOG), NAME, "BHD", "acme-store.com",
        ) is None

    def test_sar_store_converts_flag_off(self, monkeypatch):
        """Guard-rail: a base-table currency converts with the flag OFF, as at
        base (the gate swap is a pure superset)."""
        monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "false")
        monkeypatch.setenv("ENABLE_EXTENDED_FALLBACK_RATES", "false")
        cat = dict(self.CATALOG, _store_currency="SAR")
        res = ps._match_shopify_product(cat, NAME, "BHD", "acme-store.com")
        assert res is not None and res["currency"] == "BHD"
