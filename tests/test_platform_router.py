"""Platform detection over the cached fragrance PDP corpus.

`app.services.platform_router.detect_platform` is a pure, offline classifier:
given the HTML of a product page it names the storefront platform. Every
fixture under `tests/fixtures/platform/` is a verbatim ~1KB fragment lifted out
of a real cached page in `_proof/html/` (filename =
sha1("curl_cffi|" + url) + ".html"), so the assertions below are anchored to
real markup rather than hand-written markup that flatters the regexes.

`EXPECTED.json` maps fixture filename -> expected platform and is the single
source of truth for the corpus assertions; the census it encodes is
shopify 6, salla 5, woocommerce 4, magento 4, sfcc 3, nextjs 3, unknown 4.

No network, no credentials, no imports from price_service.
"""

import json
from pathlib import Path

import pytest

from app.services.platform_router import detect_platform

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "platform"
EXPECTED = json.loads(
    (FIXTURE_DIR / "EXPECTED.json").read_text(encoding="utf-8")
)["fixtures"]

ALL_PLATFORMS = {
    "shopify",
    "salla",
    "woocommerce",
    "magento",
    "sfcc",
    "nextjs",
    "unknown",
}


def _read(name: str) -> str:
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


def test_corpus_spans_all_seven_classes_and_twenty_plus_domains():
    """Guard the guard: the fixture set must stay broad enough to be evidence."""
    assert len(EXPECTED) >= 20, f"only {len(EXPECTED)} fixtures"
    assert set(EXPECTED.values()) == ALL_PLATFORMS


@pytest.mark.parametrize("name,expected", sorted(EXPECTED.items()))
def test_detect_platform_matches_cached_corpus(name, expected):
    assert detect_platform(_read(name), url=f"https://{name[:-5]}/") == expected


def test_every_result_is_a_known_label():
    for name in EXPECTED:
        assert detect_platform(_read(name)) in ALL_PLATFORMS


# --- negatives -------------------------------------------------------------


@pytest.mark.parametrize(
    "html",
    [
        "",
        "   ",
        "<html><head><title>Hello</title></head><body><p>A page.</p></body></html>",
        "<!doctype html><html><body><h1>Perfume 12.500 BHD</h1></body></html>",
    ],
)
def test_plain_or_empty_html_is_unknown(html):
    assert detect_platform(html) == "unknown"


def test_none_and_non_string_are_unknown_not_crash():
    assert detect_platform(None) == "unknown"  # type: ignore[arg-type]
    assert detect_platform(b"<html>cdn.shopify.com</html>") == "unknown"  # type: ignore[arg-type]


# --- ordering / priority ---------------------------------------------------


def test_shopify_wins_over_nextjs_regardless_of_document_order():
    """A Shopify store can also be a Next.js app; the ecommerce label wins."""
    next_first = '<script id="__NEXT_DATA__"></script><img src="//cdn.shopify.com/x.png">'
    shop_first = '<img src="//cdn.shopify.com/x.png"><script id="__NEXT_DATA__"></script>'
    assert detect_platform(next_first) == "shopify"
    assert detect_platform(shop_first) == "shopify"


def test_ecommerce_platforms_beat_generic_frameworks():
    for token, expected in [
        ("cdn.salla.network", "salla"),
        ("wp-content/plugins/woocommerce", "woocommerce"),
        ("data-mage-init", "magento"),
        ("demandware", "sfcc"),
    ]:
        html = f'<link href="/_next/static/x.css"><div>{token}</div>'
        assert detect_platform(html) == expected


# --- individual verified signatures ----------------------------------------


@pytest.mark.parametrize(
    "token,expected",
    [
        ("cdn.shopify.com", "shopify"),
        ("/cdn/shop/files/a.jpg", "shopify"),
        ("Shopify.theme", "shopify"),
        ("shopify-section", "shopify"),
        ("salla.sa", "salla"),
        ("cdn.salla.network", "salla"),
        ("woocommerce-Price-amount", "woocommerce"),
        ("wp-content/plugins/woocommerce", "woocommerce"),
        ("Magento_", "magento"),
        ("/pub/static/", "magento"),
        ("data-mage-init", "magento"),
        ("demandware", "sfcc"),
        ("__NEXT_DATA__", "nextjs"),
        ("/_next/static", "nextjs"),
    ],
)
def test_each_verified_signature_is_recognised(token, expected):
    assert detect_platform(f"<html><body>{token}</body></html>") == expected


# Every verified signature, paired with the platform it proves. Kept as a flat
# table so the pairwise priority test below covers all 14x14 combinations.
SIGNATURE_TOKENS = [
    ("cdn.shopify.com", "shopify"),
    ("/cdn/shop/files/a.jpg", "shopify"),
    ("Shopify.theme", "shopify"),
    ("shopify-section", "shopify"),
    ("salla.sa", "salla"),
    ("cdn.salla.network", "salla"),
    ("woocommerce-Price-amount", "woocommerce"),
    ("wp-content/plugins/woocommerce", "woocommerce"),
    ("Magento_", "magento"),
    ("/pub/static/", "magento"),
    ("data-mage-init", "magento"),
    ("demandware", "sfcc"),
    ("__NEXT_DATA__", "nextjs"),
    ("/_next/static", "nextjs"),
]

PRIORITY = ["shopify", "salla", "woocommerce", "magento", "sfcc", "nextjs"]


def test_priority_is_total_over_every_pair_of_signatures():
    """Characterization: for ANY two signatures in ANY document order, the
    higher-priority platform wins. Locks the semantics against refactors of
    the scanning strategy (e.g. sequential passes vs one combined pass)."""
    for first, want_a in SIGNATURE_TOKENS:
        for second, want_b in SIGNATURE_TOKENS:
            expected = min(want_a, want_b, key=PRIORITY.index)
            html = f"<html><head>{first}</head><body>{second}</body></html>"
            assert detect_platform(html) == expected, (first, second)
            # adjacent, no separator - guards against one match consuming the other
            assert detect_platform(first + second) == expected, (first, second)


def test_detection_is_case_insensitive():
    assert detect_platform("<div>CDN.SHOPIFY.COM</div>") == "shopify"
    assert detect_platform("<div>DEMANDWARE</div>") == "sfcc"
    assert detect_platform("<div>__next_data__</div>") == "nextjs"


def test_dots_in_host_signatures_are_literal():
    """`salla.sa` must not be an unescaped regex that matches `sallaxsa`."""
    assert detect_platform("<div>sallaxsa</div>") == "unknown"
    assert detect_platform("<div>cdnxshopifyxcom</div>") == "unknown"


# --- cost guard ------------------------------------------------------------


def test_only_the_capped_prefix_is_scanned():
    """A 2.6MB page must not cost a full-document scan."""
    from app.services.platform_router import MAX_SCAN_CHARS

    filler = "<p>0123456789</p>" * ((MAX_SCAN_CHARS // 17) + 100)
    assert len(filler) > MAX_SCAN_CHARS
    assert detect_platform(filler + "cdn.shopify.com") == "unknown"
    assert detect_platform("cdn.shopify.com" + filler) == "shopify"


def test_url_is_only_a_fallback_and_never_overrides_the_html():
    salla_html = _read("vanilla_sa.html")
    assert detect_platform(salla_html, url="https://x.myshopify.com/p") == "salla"
    assert detect_platform("", url="https://salla.sa/store/abc") == "salla"
    assert detect_platform("", url="https://example.com/p") == "unknown"


def test_makes_no_network_call(monkeypatch):
    import socket

    def _boom(*a, **k):  # pragma: no cover - only fires on regression
        raise AssertionError("detect_platform must not touch the network")

    monkeypatch.setattr(socket, "socket", _boom)
    monkeypatch.setattr(socket, "create_connection", _boom)
    assert detect_platform(_read("klinq_com.html")) == "magento"


def test_does_not_import_price_service():
    """Import cycle guard: the router must stay free of price_service."""
    import sys

    for mod in [m for m in sys.modules if "price_service" in m]:
        del sys.modules[mod]
    import importlib

    importlib.reload(
        importlib.import_module("app.services.platform_router")
    )
    assert not any("price_service" in m for m in sys.modules)
