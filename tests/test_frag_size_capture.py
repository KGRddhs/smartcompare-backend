"""Fragrance price-size CAPTURE gap (feature/frag-size-capture).

BUG (verified in prod): a live fragrance compare (Tom Ford Ombré Leather vs
Tobacco Vanille) returned both prices with ``price.size = None`` — both
``page_scrape_jsonld``. The JSON-LD / curl-scraped PDP exposes the size in the
product ``name`` / ``og:title`` / page ``<title>`` (e.g. "...Eau de Parfum
100ml"), NOT in an "Xml" token in the shopping listing title field. The legacy
code only set ``price.size`` from ``extract_sizes_ml(title)``, so both sides came
back size-None.

Because size was None on BOTH, ``effective_pair_size_ml`` fell back to the
designer flagship-100ml default for BOTH → they "matched" at 100ml and passed
``reconcile_pair_sizes`` through — EVEN WHEN the underlying listings were
different real sizes (the 38 BHD one being a 30ml/50ml). That MASKED the exact
size unfairness the engine exists to prevent.

FIX: capture each fragrance price's REAL size (ml) from ALL available listing
signals (JSON-LD product ``name``, ``og:title``, page ``<title>``, oz→ml) and
set ``price.size`` whenever the data exposes it. The flagship-100ml default
stays ONLY as the last resort when NO size signal exists anywhere.

Run: pytest tests/test_frag_size_capture.py -v
"""
import os

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

import pytest

from app.services.price_service import (
    extract_price_from_html,
    extract_size_ml_any,
    reconcile_pair_sizes,
    effective_pair_size_ml,
    _FRAGRANCE_FLAGSHIP_SIZE_ML,
)


# ============================================================
# extract_size_ml_any — ml OR oz, normalized to an ml integer
# ============================================================
class TestExtractSizeMlAny:
    @pytest.mark.parametrize("text,expected", [
        ("Tom Ford Ombré Leather Eau de Parfum 100ml", 100),
        ("Ombre Leather 50 ml EDP", 50),
        ("Tom Ford Tobacco Vanille 30 ML", 30),
        ("Creed Aventus 100-ml", 100),
        # oz → ml (3.4 oz ≈ 100ml; 1.7 oz ≈ 50ml; 1 oz ≈ 30ml)
        ("Tom Ford Ombré Leather 3.4 oz", 100),
        ("Tobacco Vanille 1.7 oz EDP", 50),
        ("Sample 1 oz", 30),
        # smallest token when several are present (range text)
        ("Sampler 30ml / 50ml / 100ml", 30),
        # no size signal
        ("Tom Ford Tobacco Vanille", None),
        ("MacBook Air 13", None),     # bare number is NOT a size
        ("", None),
        (None, None),
    ])
    def test_parses_ml_and_oz(self, text, expected):
        assert extract_size_ml_any(text) == expected


# ============================================================
# extract_price_from_html — size captured from page signals
# ============================================================
class TestPageScrapeSizeCapture:
    def test_size_from_jsonld_name(self):
        """Size lives ONLY in the JSON-LD product name (not in any shopping
        title) → price.size is now populated."""
        html = '''<html><head><script type="application/ld+json">
        {"@type":"Product","name":"Tom Ford Ombré Leather Eau de Parfum 50ml",
         "offers":{"@type":"Offer","price":62.000,"priceCurrency":"BHD"}}
        </script></head><body></body></html>'''
        res = extract_price_from_html(
            html, "Tom Ford Ombré Leather", "BHD", "someshop.bh",
            "https://someshop.bh/p/ombre",
        )
        assert res is not None
        assert res["amount"] == pytest.approx(62.000)
        assert res["size"] == "50ml"

    def test_size_from_jsonld_name_oz(self):
        """An oz size in the JSON-LD name is converted to the ml basis."""
        html = '''<html><head><script type="application/ld+json">
        {"@type":"Product","name":"Tom Ford Tobacco Vanille EDP 3.4 oz",
         "offers":{"@type":"Offer","price":118.000,"priceCurrency":"BHD"}}
        </script></head><body></body></html>'''
        res = extract_price_from_html(
            html, "Tom Ford Tobacco Vanille", "BHD", "someshop.bh",
            "https://someshop.bh/p/tobacco",
        )
        assert res is not None
        assert res["size"] == "100ml"

    def test_size_from_og_title_when_jsonld_name_silent(self):
        """JSON-LD name carries no size, but og:title does → captured from
        og:title (OG-price branch)."""
        html = '''<html><head>
        <meta property="og:title" content="Tom Ford Ombré Leather Parfum 50ml">
        <meta property="og:price:amount" content="62.000">
        <meta property="og:price:currency" content="BHD">
        </head><body></body></html>'''
        res = extract_price_from_html(
            html, "Tom Ford Ombré Leather", "BHD", "someshop.bh",
            "https://someshop.bh/p/ombre",
        )
        assert res is not None
        assert res["amount"] == pytest.approx(62.000)
        assert res["size"] == "50ml"

    def test_size_from_page_title_tag(self):
        """No ml in JSON-LD name or og:title, but the page <title> has it →
        captured from <title>."""
        html = '''<html><head>
        <title>Tom Ford Ombré Leather 30ml - Buy Online | SomeShop</title>
        <script type="application/ld+json">
        {"@type":"Product","name":"Tom Ford Ombré Leather Eau de Parfum",
         "offers":{"@type":"Offer","price":40.000,"priceCurrency":"BHD"}}
        </script></head><body></body></html>'''
        res = extract_price_from_html(
            html, "Tom Ford Ombré Leather", "BHD", "someshop.bh",
            "https://someshop.bh/p/ombre",
        )
        assert res is not None
        assert res["size"] == "30ml"

    def test_no_size_signal_anywhere_leaves_size_unset(self):
        """No ml/oz in any field → size stays None (the flagship default is a
        pair-level fairness concern, NOT fabricated onto a single price)."""
        html = '''<html><head>
        <title>Tom Ford Ombré Leather - SomeShop</title>
        <script type="application/ld+json">
        {"@type":"Product","name":"Tom Ford Ombré Leather Eau de Parfum",
         "offers":{"@type":"Offer","price":80.000,"priceCurrency":"BHD"}}
        </script></head><body></body></html>'''
        res = extract_price_from_html(
            html, "Tom Ford Ombré Leather", "BHD", "someshop.bh",
            "https://someshop.bh/p/ombre",
        )
        assert res is not None
        assert res["amount"] == pytest.approx(80.000)
        assert res.get("size") is None

    def test_non_fragrance_electronics_size_unset(self):
        """A phone PDP must NOT get a spurious 'size' (no ml/oz tokens; and the
        capture is fragrance-scoped so electronics is untouched)."""
        html = '''<html><head><script type="application/ld+json">
        {"@type":"Product","name":"Apple iPhone 15 128GB Blue",
         "offers":{"@type":"Offer","price":244.990,"priceCurrency":"BHD"}}
        </script></head><body></body></html>'''
        res = extract_price_from_html(
            html, "Apple iPhone 15 128GB", "BHD", "bahrain.sharafdg.com",
            "https://bahrain.sharafdg.com/p/iphone-15",
        )
        assert res is not None
        assert res["amount"] == pytest.approx(244.990)
        assert res.get("size") is None


# ============================================================
# Pair-level fairness now engages on TRUE sizes
# ============================================================
def _prod(name, amount, size, source_method="page_scrape_jsonld"):
    return {
        "name": name, "full_name": name,
        "price": {
            "amount": amount, "currency": "BHD",
            "source_method": source_method, "size": size,
        },
        "best_price": amount,
        "retailer": "someshop.bh",
    }


class TestFairnessEngagesOnRealSizes:
    def test_real_100_vs_50_detected_off_side_pended(self):
        """The prod scenario, now FIXED: Ombré genuinely 100ml @ 80, Tobacco
        genuinely 50ml @ 38 (sizes captured). Target = flagship 100ml. Ombré is
        at target → kept; Tobacco at 50ml can't reach 100 (no candidates) → pend
        ONLY Tobacco. The mismatch is no longer silently both-flagship-100ml."""
        pd = [
            _prod("Tom Ford Ombré Leather", 80.0, "100ml"),
            _prod("Tom Ford Tobacco Vanille", 38.0, "50ml"),
        ]
        changed = reconcile_pair_sizes(pd)
        assert changed is True
        assert pd[0]["price"]["amount"] == 80.0            # genuine 100ml kept
        assert pd[1]["price"]["amount"] is None            # off-basis 50ml pended
        assert pd[1]["price"]["unavailable"] is True
        assert pd[1]["price"]["reason"] == "size_mismatch"

    def test_both_real_50ml_is_a_valid_shared_basis(self):
        """When BOTH listings are genuinely 50ml (sizes captured), that's a fair
        shared basis → pass through (NOT forced up to flagship 100)."""
        pd = [
            _prod("Tom Ford Ombré Leather", 62.0, "50ml"),
            _prod("Tom Ford Tobacco Vanille", 70.0, "50ml"),
        ]
        changed = reconcile_pair_sizes(pd)
        assert changed is False
        assert pd[0]["price"]["amount"] == 62.0
        assert pd[1]["price"]["amount"] == 70.0

    def test_no_size_anywhere_flagship_default_still_applies(self):
        """REGRESSION GUARD: when NO size signal exists on either side, both
        designer fragrances still default to the flagship 100ml basis and pass
        through (the last-resort default is unchanged)."""
        pd = [
            _prod("Tom Ford Ombré Leather", 80.0, None),
            _prod("Tom Ford Tobacco Vanille", 90.0, None),
        ]
        # Both resolve to the flagship default → equal basis → no change.
        assert effective_pair_size_ml(pd[0]) == _FRAGRANCE_FLAGSHIP_SIZE_ML
        assert effective_pair_size_ml(pd[1]) == _FRAGRANCE_FLAGSHIP_SIZE_ML
        changed = reconcile_pair_sizes(pd)
        assert changed is False
        assert pd[0]["price"]["amount"] == 80.0
        assert pd[1]["price"]["amount"] == 90.0
