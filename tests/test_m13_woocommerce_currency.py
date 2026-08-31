"""M13-07 + M13-08 — WooCommerce currency truth (Wave 2).

Both pins run against ``price_service._extract_woocommerce_price`` directly (no
network, no exact-gate involvement — the Woo branch does not read
ENABLE_EXACT_PRICE_GATE). ENABLE_JSONLD_FIRST is the gate: ON = the fixes,
OFF = the exact legacy bytes.

FAILURE SCENARIOS reproduced:
  * M13-08: a de-DE dot-grouped "1.234" on a EUR WooCommerce page whose span
    carries NO currency-symbol child. Pre-fix the minor-unit divisor came from
    ``detected_currency`` (the ASK fallback, BHD/3-minor) so "1.234" read as
    1.234, while the stamped label came from page evidence (EUR) — converting
    1.234 EUR -> 0.51 BHD (~2400x under). The fix parses with the SAME resolved
    label it stamps, so "1.234" reads 1234 EUR -> ~505.94 BHD.
  * M13-07: that converted price used to bank as ``page_scrape`` (a genuine
    Bahrain shelf price); it must be relabelled ``converted_usd``.
"""
from bs4 import BeautifulSoup

from app.services import price_service as ps

# EUR page, WooCommerce span with a dot-grouped thousands amount and NO symbol
# child, so detected_currency falls back to the BHD ask while page evidence
# (og:price:currency) resolves EUR — the exact M13-08 divergence.
_EUR_DEDE_WOO = (
    '<html><head><meta property="og:price:currency" content="EUR"></head>'
    '<body><p class="price">'
    '<span class="woocommerce-Price-amount amount">1.234</span>'
    '</p></body></html>'
)

# Bahraini WooCommerce store: a real BHD glyph symbol child and the shelf price
# "12,500" (= 12.5 BHD, three-minor-unit). The regression guard for M13-08.
_BHD_WOO = (
    '<html><head></head><body><p class="price">'
    '<span class="woocommerce-Price-amount amount">'
    '<span class="woocommerce-Price-currencySymbol">.د.ب</span>12,500'
    '</span></p></body></html>'
)


def _extract(html, ask="BHD"):
    soup = BeautifulSoup(html, "html.parser")
    return ps._extract_woocommerce_price(soup, ask, "klinq.com", "https://klinq.com/p")


def test_m13_08_dedE_eur_page_is_not_051_bhd(monkeypatch):
    """M13-08 pin: the de-DE EUR page does NOT become 0.51 BHD (flag ON)."""
    monkeypatch.setenv("ENABLE_JSONLD_FIRST", "true")
    r = _extract(_EUR_DEDE_WOO)
    assert r is not None
    # The bug shipped ~0.51 BHD (1.234 EUR converted). The fix ships ~505.94 BHD
    # (1234 EUR converted at 0.41). Never the ~2400x-under value.
    assert abs(r["amount"] - 0.51) > 1.0, r
    assert r["amount"] == 505.94, r
    assert r["currency"] == "BHD", r


def test_m13_08_parse_currency_equals_stamped_currency(monkeypatch):
    """M13-08 pin: parse currency == the label the number is denominated in.

    original_currency is the token the amount was PARSED under; a EUR parse of
    "1.234" yields 1234 (not 1.234), proving the divisor came from EUR, not the
    3-minor BHD ask.
    """
    monkeypatch.setenv("ENABLE_JSONLD_FIRST", "true")
    r = _extract(_EUR_DEDE_WOO)
    assert r["original_currency"] == "EUR", r
    # 1234 EUR * 0.41 = 505.94 BHD proves "1.234" parsed as 1234 under EUR.
    assert r["amount"] == round(1234 * 0.41, 2), r


def test_m13_07_converted_woo_price_relabelled_converted_usd(monkeypatch):
    """M13-07 pin: a converted WooCommerce price is stamped converted_usd,
    matching the four sibling branches (flag ON)."""
    monkeypatch.setenv("ENABLE_JSONLD_FIRST", "true")
    r = _extract(_EUR_DEDE_WOO)
    assert r["source_method"] == "converted_usd", r


def test_m13_woo_flag_off_byte_identical(monkeypatch):
    """Flag OFF: the legacy bytes — ASK-token parse (1.234), no relabel, no
    conversion (BHD == BHD ask). Byte-identity guard for both fixes."""
    monkeypatch.setenv("ENABLE_JSONLD_FIRST", "false")
    r = _extract(_EUR_DEDE_WOO)
    assert r["amount"] == 1.234, r
    assert r["currency"] == "BHD", r
    assert r["source_method"] == "page_scrape", r


def test_m13_08_bahraini_woo_12500_reads_12_5_both_modes(monkeypatch):
    """Regression guard: a genuine Bahraini WooCommerce "12,500" must still read
    12.5 (three-minor-unit) under BOTH flag modes — the fix must not break the
    case the original detected_currency-glyph fold protected."""
    for flag in ("false", "true"):
        monkeypatch.setenv("ENABLE_JSONLD_FIRST", flag)
        r = _extract(_BHD_WOO)
        assert r is not None, flag
        assert r["amount"] == 12.5, (flag, r)
        assert r["currency"] == "BHD", (flag, r)
        # Native BHD price on a BHD ask — genuine, never relabelled converted.
        assert r["source_method"] == "page_scrape", (flag, r)
