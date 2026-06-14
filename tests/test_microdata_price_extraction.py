"""S3-genuine — Schema.org MICRODATA price extraction (the sharafdg fix) +
lowercase priceCurrency normalization (the lulu fix).

Gap-fill research (team-lead, verified live): bahrain.sharafdg.com PDPs are
microdata-only (the existing JSON-LD path misses them) and the price lives in an
itemprop=price/priceCurrency Offer — BUT an EPP installment widget also carries
an itemprop=price ("BHD 48.332/month"), so the naive `find-first itemprop=price`
grabs the WRONG number. iPhone 15 = BHD 244.990 (not 48.332).

Also: gcc.luluhypermarket.com emits priceCurrency in LOWERCASE "bhd" — must be
.upper()-normalized so a BHD price isn't mistaken for a foreign currency and
needlessly "converted".

Offline TDD against a standard-Schema.org fixture (the W3C Offer contract + the
installment gotcha). Live PDP confirmation pends the Serper rotation.
"""

from pathlib import Path

import pytest

from app.services.price_service import extract_price_from_html

FIX = Path(__file__).parent / "fixtures"


class TestMicrodataInstallmentSkip:
    def test_extracts_offer_price_not_installment(self):
        """The real Offer price (244.990 BHD) is extracted, NOT the EPP
        installment (48.332/month) that the naive find-first grabs."""
        html = (FIX / "sharafdg_microdata_pdp.html").read_text(encoding="utf-8")
        res = extract_price_from_html(
            html, "Apple iPhone 15 128GB", "BHD", "bahrain.sharafdg.com",
            "https://bahrain.sharafdg.com/product/apple-iphone-15-128gb/",
        )
        assert res is not None
        assert res["amount"] == pytest.approx(244.990)
        assert res["amount"] != pytest.approx(48.332)  # NOT the installment
        assert res["currency"] == "BHD"
        assert res["source_method"] in ("page_scrape", "page_scrape_microdata")

    def test_no_microdata_price_returns_none(self):
        """A page with only an installment itemprop=price (no real Offer price)
        and no other structured data → None (don't surface an installment as
        the product price)."""
        html = '''<html><body>
        <div class="epp">Pay monthly <span itemprop="price" content="48.332">BHD 48.332</span>/month</div>
        </body></html>'''
        res = extract_price_from_html(
            html, "Apple iPhone 15", "BHD", "x.com", "https://x.com/p",
        )
        assert res is None


class TestLowercasePriceCurrency:
    def test_lowercase_bhd_currency_normalized(self):
        """JSON-LD with priceCurrency 'bhd' (lowercase, lulu) is treated as BHD
        — the price is NOT spuriously converted as if foreign."""
        html = '''<html><head><script type="application/ld+json">
        {"@type":"Product","name":"Panadol Extra","offers":{"@type":"Offer",
         "price":0.990,"priceCurrency":"bhd"}}
        </script></head><body></body></html>'''
        res = extract_price_from_html(
            html, "Panadol Extra", "BHD", "gcc.luluhypermarket.com",
            "https://gcc.luluhypermarket.com/en-bh/panadol/p/1",
        )
        assert res is not None
        # 0.990 BHD, unchanged (not converted as if 0.990 of a foreign currency).
        assert res["amount"] == pytest.approx(0.990)
        assert res["currency"].upper() == "BHD"


class TestMicrodataRegression:
    def test_clean_single_itemprop_price_still_works(self):
        """A normal page with one clean itemprop=price/priceCurrency still
        extracts (no regression for the common case)."""
        html = '''<html><body>
        <div itemscope itemtype="https://schema.org/Product">
          <div itemprop="offers" itemscope itemtype="https://schema.org/Offer">
            <span itemprop="price" content="55.000">BHD 55.000</span>
            <meta itemprop="priceCurrency" content="BHD">
          </div>
        </div></body></html>'''
        res = extract_price_from_html(
            html, "Some Product", "BHD", "x.com", "https://x.com/p",
        )
        assert res is not None
        assert res["amount"] == pytest.approx(55.000)
        assert res["currency"] == "BHD"
