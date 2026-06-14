"""S3-genuine (PDP curl Decision-F, 2026-06-14) — OG price currency default.

THE sharafdg BUG (found by curling the live PDP through the production
extractor): bahrain.sharafdg.com iPhone-15 PDP carries
`<meta property="product:price:amount" content="244.990">` but NO
`product:price:currency` tag, and ZERO "USD" anywhere on the page (it's a BHD
storefront — the microdata even says priceCurrency="BHD "). The OG branch
(Priority 2) fired before microdata (Priority 3) and DEFAULTED the currency-less
amount to "USD", then converted 244.990 USD -> 92.12 BHD. A genuine 244.990 BHD
BH price was mangled into a wrong 92.12 BHD.

THE FIX: a currency-less OG price defaults to the EXPECTED currency argument
(BHD for a .bh / bahrain-region scrape), NOT a hardcoded "USD". An unlabeled
price on a Bahrain retailer page is in BHD.

Synthetic fixtures matching the live sharafdg markup (OG amount, no OG currency).
"""

import pytest

from app.services.price_service import extract_price_from_html


# The exact sharafdg failure shape: OG amount, NO OG currency, BHD page.
_SHARAFDG_SHAPE = """<html><head>
  <meta property="product:price:amount" content="244.990">
  <title>Apple iPhone 15 128GB Blue</title>
</head><body>
  <span class="price">BHD 244.990</span>
</body></html>"""


class TestOgCurrencylessDefaultsToExpected:
    def test_bhd_page_og_no_currency_stays_bhd(self):
        """OG amount 244.990 with no OG currency on a BHD scrape → 244.990 BHD,
        NOT 92.12 BHD (the USD-default-then-convert bug)."""
        res = extract_price_from_html(
            _SHARAFDG_SHAPE, "Apple iPhone 15 128GB", "BHD",
            "bahrain.sharafdg.com",
            "https://bahrain.sharafdg.com/product/apple-iphone-15-128gb-blue/",
        )
        assert res is not None
        assert res["amount"] == pytest.approx(244.990)
        assert res["amount"] != pytest.approx(92.12)  # NOT USD-converted
        assert res["currency"].upper() == "BHD"
        # original_currency must reflect the expected BHD, not a phantom USD.
        assert res.get("original_currency", "BHD").upper() == "BHD"

    def test_explicit_og_currency_still_honored(self):
        """REGRESSION: when OG DOES carry an explicit currency, it's still used
        (a genuinely-USD page converts correctly — the fix only changes the
        ABSENT-currency default, not the present-currency path)."""
        html = """<html><head>
          <meta property="og:price:amount" content="100.00">
          <meta property="og:price:currency" content="USD">
        </head><body></body></html>"""
        res = extract_price_from_html(
            html, "Some Product", "BHD", "example.com", "https://example.com/p",
        )
        assert res is not None
        # 100 USD converted to BHD (~37.6) — explicit USD honored, then converted.
        assert res["currency"].upper() == "BHD"
        assert res["amount"] < 100  # converted down from USD
        assert res.get("original_currency", "").upper() == "USD"

    def test_usd_domain_og_no_currency_defaults_expected_usd(self):
        """When the EXPECTED currency is USD (a US scrape), a currency-less OG
        price defaults to USD as before — the fix is 'default to expected', not
        'always BHD'."""
        html = """<html><head>
          <meta property="product:price:amount" content="799.00">
        </head><body></body></html>"""
        res = extract_price_from_html(
            html, "Apple iPhone 15", "USD", "apple.com", "https://apple.com/p",
        )
        assert res is not None
        assert res["amount"] == pytest.approx(799.00)
        assert res["currency"].upper() == "USD"
