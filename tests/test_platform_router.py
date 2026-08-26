"""Platform detection over the cached fragrance PDP corpus.

`app.services.platform_router` is a pure, offline classifier: given the HTML of
a product page it names the storefront platform and, since 2026-08-26, the
rendering stack separately. Every fixture under `tests/fixtures/platform/` is a
verbatim fragment lifted out of a real cached page - never hand-written markup
that would flatter the regexes.

The original fixtures come from the Gulf-92 sweep (`_proof/html/`, filename =
sha1("curl_cffi|" + url) + ".html"). Everything added on 2026-08-26 comes from
the 328-row GLOBAL corpus (`_proof/global/html/`) and from
`_proof/global/robots/`, because that is where the platforms the six original
regexes could not see actually live. Per-fixture provenance - source host, URL,
cache file, HTTP status, source byte count, and the corpus's own
`platform_truth` - is recorded in `SOURCES.json`, which also documents the
three hosts where that `platform_truth` is WRONG against its own cached bytes
and the bytes win.

`EXPECTED.json` maps fixture filename -> ``[legacy, commerce_platform,
render_stack]`` and is the single source of truth for the corpus assertions.
`legacy` is what `detect_platform` returned before the two-field verdict landed
and is what it still returns with `ENABLE_PLATFORM_VERDICT=false`; the other
two are the independent fields of `detect_platform_verdict`.

The commerce census the fixture set encodes is magento 7, shopify 6, salla 5,
sap_hybris 5, woocommerce 4, sfcc 4, shopware 2, prestashop 2, zid 2,
bigcommerce 1, unknown 10; the render census is nextjs 6, angular 3, classic 2,
nuxt 1, react 1, unknown 35 (most fixtures are ~1KB fragments cut around the
COMMERCE signature, so they carry no framework bundle at all - that is recorded
honestly rather than papered over).

`vtex` and the `vue` render stack have NO fixture because neither appears
anywhere in either corpus: 0 hits for `vtexassets.com` / `vteximg.com.br` and 0
pages whose highest render signal is Vue across all 521 cached pages. They are
covered by token-level tests only, and that gap is deliberate and recorded.

No network, no credentials, no imports from price_service.
"""

import json
from pathlib import Path

import pytest

from app.services.platform_router import detect_platform

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "platform"
_EXPECTED_DOC = json.loads(
    (FIXTURE_DIR / "EXPECTED.json").read_text(encoding="utf-8")
)
EXPECTED = _EXPECTED_DOC["fixtures"]
ROBOTS_EXPECTED = {
    k: v for k, v in _EXPECTED_DOC["robots_fixtures"].items()
    if not k.startswith("_")
}

#: What `detect_platform` returned before this wave, and still returns with
#: ENABLE_PLATFORM_VERDICT=false.
LEGACY_PLATFORMS = {
    "shopify",
    "salla",
    "zid",
    "woocommerce",
    "magento",
    "sfcc",
    "nextjs",
    "unknown",
}
LEGACY = {k: v[0] for k, v in EXPECTED.items()}
COMMERCE = {k: v[1] for k, v in EXPECTED.items()}
RENDER = {k: v[2] for k, v in EXPECTED.items()}


def _read(name: str) -> str:
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


@pytest.fixture(autouse=True)
def _default_flag_state(monkeypatch):
    """Every test states the flag it wants; the default is the shipped default."""
    monkeypatch.delenv("ENABLE_PLATFORM_VERDICT", raising=False)


def test_corpus_spans_all_eight_legacy_classes_and_twenty_plus_domains():
    """Guard the guard: the fixture set must stay broad enough to be evidence."""
    assert len(EXPECTED) >= 20, f"only {len(EXPECTED)} fixtures"
    assert set(LEGACY.values()) == LEGACY_PLATFORMS


@pytest.mark.parametrize("name,expected", sorted(LEGACY.items()))
def test_detect_platform_legacy_verdict_is_pinned_with_the_flag_off(
    name, expected, monkeypatch
):
    monkeypatch.setenv("ENABLE_PLATFORM_VERDICT", "false")
    assert detect_platform(_read(name), url=f"https://{name[:-5]}/") == expected


def test_every_legacy_result_is_a_known_label(monkeypatch):
    monkeypatch.setenv("ENABLE_PLATFORM_VERDICT", "false")
    for name in EXPECTED:
        assert detect_platform(_read(name)) in LEGACY_PLATFORMS


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


def test_shopify_wins_over_a_framework_regardless_of_document_order():
    """A Shopify store can also be a Next.js app; the ecommerce label wins."""
    next_first = '<script id="__NEXT_DATA__"></script><img src="//cdn.shopify.com/x.png">'
    shop_first = '<img src="//cdn.shopify.com/x.png"><script id="__NEXT_DATA__"></script>'
    assert detect_platform(next_first) == "shopify"
    assert detect_platform(shop_first) == "shopify"


def test_ecommerce_platforms_beat_generic_frameworks():
    for token, expected in [
        ("cdn.salla.network", "salla"),
        ("media.zid.store", "zid"),
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
        ("h3jssz.zid.store", "zid"),
        ("assets.zid.store", "zid"),
        ("media.zid.store", "zid"),
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
def test_each_verified_signature_is_recognised(token, expected, monkeypatch):
    """Legacy semantics, so the flag is OFF: `nextjs` is a value only the legacy
    single-string verdict ever returned."""
    monkeypatch.setenv("ENABLE_PLATFORM_VERDICT", "false")
    assert detect_platform(f"<html><body>{token}</body></html>") == expected


# Every verified signature, paired with the platform it proves. Kept as a flat
# table so the pairwise priority test below covers all 17x17 combinations.
SIGNATURE_TOKENS = [
    ("cdn.shopify.com", "shopify"),
    ("/cdn/shop/files/a.jpg", "shopify"),
    ("Shopify.theme", "shopify"),
    ("shopify-section", "shopify"),
    ("salla.sa", "salla"),
    ("cdn.salla.network", "salla"),
    ("h3jssz.zid.store", "zid"),
    ("assets.zid.store", "zid"),
    ("media.zid.store", "zid"),
    ("woocommerce-Price-amount", "woocommerce"),
    ("wp-content/plugins/woocommerce", "woocommerce"),
    ("Magento_", "magento"),
    ("/pub/static/", "magento"),
    ("data-mage-init", "magento"),
    ("demandware", "sfcc"),
    ("__NEXT_DATA__", "nextjs"),
    ("/_next/static", "nextjs"),
]

PRIORITY = [
    "shopify", "salla", "zid", "woocommerce", "magento", "sfcc", "nextjs",
]


def test_priority_is_total_over_every_pair_of_signatures(monkeypatch):
    """Characterization: for ANY two signatures in ANY document order, the
    higher-priority platform wins. Locks the semantics against refactors of
    the scanning strategy (e.g. sequential passes vs one combined pass).

    Legacy table, so the flag is OFF - `nextjs` is in it."""
    monkeypatch.setenv("ENABLE_PLATFORM_VERDICT", "false")
    for first, want_a in SIGNATURE_TOKENS:
        for second, want_b in SIGNATURE_TOKENS:
            expected = min(want_a, want_b, key=PRIORITY.index)
            html = f"<html><head>{first}</head><body>{second}</body></html>"
            assert detect_platform(html) == expected, (first, second)
            # adjacent, no separator - guards against one match consuming the other
            assert detect_platform(first + second) == expected, (first, second)


def test_detection_is_case_insensitive(monkeypatch):
    assert detect_platform("<div>CDN.SHOPIFY.COM</div>") == "shopify"
    assert detect_platform("<div>DEMANDWARE</div>") == "sfcc"
    monkeypatch.setenv("ENABLE_PLATFORM_VERDICT", "false")
    assert detect_platform("<div>__next_data__</div>") == "nextjs"


def test_dots_in_host_signatures_are_literal():
    """`salla.sa` must not be an unescaped regex that matches `sallaxsa`."""
    assert detect_platform("<div>sallaxsa</div>") == "unknown"
    assert detect_platform("<div>cdnxshopifyxcom</div>") == "unknown"
    assert detect_platform("<div>zidxstore</div>") == "unknown"


# --- zid (added 2026-08-26) ------------------------------------------------
#
# Zid is invisible to the original six regexes: on all 8 cached Zid rows in the
# 328-row global corpus `detect_platform` returned "unknown" and NO other
# signature matched either. It matters because Zid is one of the only two
# platforms on earth that publish `product:sale_price:amount` (measured: 21
# pages carry that tag across both corpora, 14 Salla + 7 Gulf, of which 5 are
# Zid), so the OG sale-price rule cannot be scoped to platform without it.


def test_zid_is_a_first_class_platform_label():
    from app.services.platform_router import PLATFORMS

    assert "zid" in PLATFORMS


def test_the_zid_host_signature_needs_a_leading_word_boundary():
    """Every real Zid signal is a HOST label - `zid.store`, `assets.zid.store`,
    `media.zid.store` - so `zid` always follows a dot or a delimiter. A LEADING
    \b keeps the signature off an unrelated domain that merely ends in the same
    letters. There is deliberately no TRAILING boundary: none of the other six
    signatures has one either, and adding one would make the label depend on
    what happens to follow it in the byte stream."""
    assert detect_platform("<div>media.zid.store</div>") == "zid"
    assert detect_platform("<div>https://zid.store/x</div>") == "zid"
    assert detect_platform("<div>rapidzid.store</div>") == "unknown"
    assert detect_platform("<div>myzid.storefront</div>") == "unknown"
    assert detect_platform("<div>zidxstore</div>") == "unknown"


def test_zid_beats_a_framework_signal():
    """mazeed.sa runs Zid behind a Nuxt front end and h3jssz ships no framework
    bundle at all; a framework is never a platform, so the Zid signal wins in
    either document order."""
    for framework in ('<link href="/_nuxt/entry.CkDq1cNn.css">',
                      '<script id="__NEXT_DATA__"></script>',
                      '<link href="/_next/static/x.css">'):
        zid = '<link rel="preconnect" href="https://media.zid.store">'
        assert detect_platform(framework + zid) == "zid", framework
        assert detect_platform(zid + framework) == "zid", framework


def test_the_two_cached_zid_storefronts_are_detected():
    """Both real shapes: the zid.store host itself, and a custom domain whose
    only signal is the media.zid.store asset preconnect."""
    assert detect_platform(_read("h3jssz_zid_store.html")) == "zid"
    assert detect_platform(_read("mazeed_sa.html")) == "zid"


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


# ===========================================================================
# THE TWO-FIELD VERDICT (added 2026-08-26)
# ===========================================================================
#
# WHY this exists at all, measured over the 429 cached global pages plus the 92
# cached Gulf pages (521 pages, one call each, no network):
#
#   * the single-string verdict said "unknown" on 230 of 521 pages (44.1%), and
#     on 101 of the 247 usable global PDPs (40.9%; 106 = 43% before `zid` was
#     admitted, which is the number the finding quotes);
#   * "nextjs" - 53 more pages - is not a platform at all. It fires across
#     unrelated commerce backends, so it can never route an extraction
#     strategy. Counting it as the non-answer it is, the single string failed
#     to name an extraction contract on 283 of 521 pages (54.3%).
#
# So the verdict is now two independent fields:
#
#   commerce_platform - the EXTRACTION contract
#   render_stack      - the FETCH strategy
#
# Either may be "unknown" on its own, and a framework signal must NEVER mask a
# commerce signal.

from app.services.platform_router import (  # noqa: E402
    COMMERCE_PLATFORMS,
    PlatformVerdict,
    RENDER_STACKS,
    detect_platform_verdict,
)

CORPUS_DIRS = [Path("_proof/html"), Path("_proof/global/html")]
_HAVE_CORPUS = all(d.is_dir() for d in CORPUS_DIRS)
requires_corpus = pytest.mark.skipif(
    not _HAVE_CORPUS,
    reason="the zero-network corpora (_proof/) are git-excluded and local-only",
)


# --- shape -----------------------------------------------------------------


def test_the_verdict_is_two_named_fields_not_one_string():
    # Resolved through the module rather than the file-level import: the
    # import-cycle guard above reloads `platform_router`, which rebinds
    # `PlatformVerdict` to a fresh class object, so a stale name would make
    # this isinstance check depend on test ORDER rather than on behaviour.
    from app.services import platform_router as pr

    v = pr.detect_platform_verdict("<div>cdn.shopify.com</div>")
    assert isinstance(v, pr.PlatformVerdict)
    assert v.commerce_platform == "shopify"
    assert (v.commerce_platform, v.render_stack) == tuple(v)
    assert v._fields == ("commerce_platform", "render_stack")


def test_the_two_label_sets_are_disjoint_and_each_carries_its_own_unknown():
    """A framework name must not be spendable as an extraction contract, and a
    platform name must not be spendable as a fetch strategy. The ONLY label the
    two sets share is `unknown`."""
    assert COMMERCE_PLATFORMS & RENDER_STACKS == {"unknown"}
    assert "nextjs" not in COMMERCE_PLATFORMS
    assert "shopify" not in RENDER_STACKS
    assert COMMERCE_PLATFORMS == {
        "shopify", "salla", "zid", "woocommerce", "magento", "sfcc",
        "bigcommerce", "prestashop", "shopware", "sap_hybris", "vtex",
        "unknown",
    }
    assert RENDER_STACKS == {
        "nextjs", "nuxt", "react", "vue", "angular", "classic", "unknown",
    }


def test_the_fields_vary_independently():
    """All four corners of the (known/unknown x known/unknown) square occur."""
    corners = {
        ("shopify", "nextjs"): '<img src="//cdn.shopify.com/x.png">'
                               '<script id="__NEXT_DATA__"></script>',
        ("shopify", "unknown"): '<img src="//cdn.shopify.com/x.png">',
        ("unknown", "nextjs"): '<script id="__NEXT_DATA__"></script>',
        ("unknown", "unknown"): "<p>A page.</p>",
    }
    for want, html in corners.items():
        assert tuple(detect_platform_verdict(html)) == want, html


# --- the corpus ------------------------------------------------------------


@pytest.mark.parametrize("name,expected", sorted(COMMERCE.items()))
def test_commerce_platform_matches_cached_corpus(name, expected):
    got = detect_platform_verdict(_read(name), url="https://%s/" % name[:-5])
    assert got.commerce_platform == expected


@pytest.mark.parametrize("name,expected", sorted(RENDER.items()))
def test_render_stack_matches_cached_corpus(name, expected):
    assert detect_platform_verdict(_read(name)).render_stack == expected


def test_every_verdict_field_is_a_known_label():
    for name in EXPECTED:
        v = detect_platform_verdict(_read(name))
        assert v.commerce_platform in COMMERCE_PLATFORMS
        assert v.render_stack in RENDER_STACKS


def test_the_fixture_set_covers_every_platform_the_corpora_contain():
    """Guard the guard. `vtex` is deliberately absent - see the module
    docstring: it has ZERO occurrences in either corpus, so there is no real
    page to cut a fixture from and inventing one would only flatter the
    regex. Same for the `vue` render stack."""
    assert set(COMMERCE.values()) == COMMERCE_PLATFORMS - {"vtex"}
    assert set(RENDER.values()) == RENDER_STACKS - {"vue"}


# --- a framework signal must never mask a commerce signal ------------------


def test_sephora_com_tr_is_sfcc_even_though_it_is_a_next_js_app():
    """THE case the finding is about, from real cached bytes: sephora.com.tr
    serves a Next.js front end (`/_next/static/...`) over Salesforce Commerce
    (`/dw/image/v2/.../on/demandware.static/`). The commerce contract and the
    fetch strategy are BOTH true and are reported separately."""
    v = detect_platform_verdict(_read("tr_sephora_com_tr.html"))
    assert v == PlatformVerdict("sfcc", "nextjs")


def test_sephora_me_is_never_labelled_nextjs():
    """The finding names sephora.me as the worst case of the nextjs bucket:
    Salesforce Commerce underneath, filed under a rendering framework.

    Its cached PDP bytes cannot prove EITHER, and saying so is the point. All
    five sephora.me fetches in the corpus returned the same ~624-byte Akamai
    "Access Denied" body, which carries no commerce signal and no framework
    signal. The corpus's `nextjs` label for this host came from a
    `/_next/static/media/ITC` string seen on a DIFFERENT fetch, not from these
    bytes. On the bytes we actually hold the honest verdict is unknown/unknown
    - and crucially NOT `nextjs`."""
    v = detect_platform_verdict(_read("ae_sephora_me_akamai_403.html"),
                                url="https://www.sephora.me/ae-en/p/x/P10064615")
    assert v.render_stack != "nextjs"
    assert v == PlatformVerdict("unknown", "unknown")


def test_sephora_me_is_sfcc_once_its_own_robots_txt_is_offered_as_evidence():
    """The evidence the finding actually cites for sephora.me is its robots.txt
    ("Disallow: /on/demandware.store/*"), and that file IS cached. Offered as
    the third evidence channel it settles the host as sfcc."""
    v = detect_platform_verdict(
        _read("ae_sephora_me_akamai_403.html"),
        url="https://www.sephora.me/ae-en/p/x/P10064615",
        robots_txt=_read("ae_sephora_me_robots.txt"),
    )
    assert v.commerce_platform == "sfcc"


@pytest.mark.parametrize("name,expected", sorted(ROBOTS_EXPECTED.items()))
def test_the_robots_channel_over_real_cached_robots_files(name, expected):
    got = detect_platform_verdict("", robots_txt=_read(name))
    assert got.commerce_platform == expected


def test_hudabeauty_robots_shows_why_the_robots_channel_needs_its_own_table():
    """hudabeauty.com's robots.txt opens with "# we use Shopify as our
    ecommerce platform" and STILL carries a stale
    "Disallow: /on/demandware.store/" from the platform it migrated off. A
    naive demandware match would call a Shopify store SFCC."""
    v = detect_platform_verdict("", robots_txt=_read("com_hudabeauty_com_robots.txt"))
    assert v.commerce_platform == "shopify"


def test_robots_is_the_weakest_channel_and_never_overrides_the_markup():
    salla = _read("vanilla_sa.html")
    assert detect_platform_verdict(
        salla, robots_txt=_read("ae_sephora_me_robots.txt")
    ).commerce_platform == "salla"
    assert detect_platform_verdict(
        "", url="https://salla.sa/store/abc",
        robots_txt=_read("ae_sephora_me_robots.txt"),
    ).commerce_platform == "salla"


# --- the signatures the corpus measured and the six regexes missed ---------


@pytest.mark.parametrize(
    "token,expected",
    [
        # SAP Commerce Cloud (hybris). `smartEditComponent` is the CMS
        # authoring runtime's own CSS class; `cx-page-slot` is the Spartacus
        # Angular storefront; `/medias/sys_master/` is the media repository.
        ("smartEditComponent", "sap_hybris"),
        ("<cx-page-slot>", "sap_hybris"),
        ("/medias/sys_master/prd-images/x.jpg", "sap_hybris"),
        ("/_ui/responsive/theme-alpha/", "sap_hybris"),
        ("hybris", "sap_hybris"),
        # Salesforce Commerce, named properly instead of swallowed by nextjs.
        ("/on/demandware.store/Sites-x-Site/", "sfcc"),
        ("/on/demandware.static/-/Library-Sites-x/", "sfcc"),
        ("/dw/image/v2/BCZG_PRD/", "sfcc"),
        ("dwfrm_login", "sfcc"),
        ("prestashop", "prestashop"),
        ("shopware", "shopware"),
        ("cdn11.bigcommerce.com/s-abc/", "bigcommerce"),
        ("stencil-utils", "bigcommerce"),
        ("vtexassets.com", "vtex"),
        ("vteximg.com.br", "vtex"),
        # widened magento / woocommerce
        ("/media/catalog/product/x.jpg", "magento"),
        ("/static/version1723/frontend/", "magento"),
        ("x-magento-init", "magento"),
        ("wc-ajax=get_refreshed_fragments", "woocommerce"),
    ],
)
def test_each_added_signature_names_its_platform(token, expected):
    v = detect_platform_verdict("<html><body>%s</body></html>" % token)
    assert v.commerce_platform == expected


@pytest.mark.parametrize(
    "token,expected",
    [
        ("__NEXT_DATA__", "nextjs"),
        ("/_next/static/chunks/x.js", "nextjs"),
        ("window.__NUXT__={}", "nuxt"),
        ("/_nuxt/entry.CkDq1cNn.css", "nuxt"),
        ('ng-version="19.2.7"', "angular"),
        ("/@angular/core", "angular"),
        ("react-dom.production.min.js", "react"),
        ("data-reactroot", "react"),
        ("data-v-6362761e", "vue"),
        ("window.__VUE__", "vue"),
        ("jquery.min.js", "classic"),
        ("requirejs/require.js", "classic"),
    ],
)
def test_each_render_signature_names_its_stack(token, expected):
    got = detect_platform_verdict("<html><body>%s</body></html>" % token)
    assert got.render_stack == expected


def test_the_added_signatures_are_case_insensitive_and_their_dots_are_literal():
    assert detect_platform_verdict("<div>SMARTEDIT</div>").commerce_platform == "sap_hybris"
    assert detect_platform_verdict("<div>PRESTASHOP</div>").commerce_platform == "prestashop"
    assert detect_platform_verdict("<div>cdn11xbigcommercexcom</div>").commerce_platform == "unknown"
    assert detect_platform_verdict("<div>vtexassetsxcom</div>").commerce_platform == "unknown"


def test_the_hosts_the_corpus_mislabels_are_adjudicated_against_their_own_bytes():
    """Two hosts where corpus.json's `platform_truth` disagrees with the cached
    bytes it was derived from, and the bytes win:

    * douglas.at (and douglas.ch) - filed `magento`, but they carry NO Magento
      token at all (no `Magento_`, no `/pub/static/`, no `data-mage-init`, no
      `/media/catalog/product/`, no `/static/versionN`) and DO carry SAP's
      `.smartEditComponent` CSS class;
    * watsons.com.tr - filed `unknown`, but it ships the full SAP Spartacus
      set: `/medias/sys_master/`, `cx-page-slot` and `<app-root ng-version=>`.
    """
    assert detect_platform_verdict(
        _read("at_douglas_at.html")).commerce_platform == "sap_hybris"
    assert detect_platform_verdict(
        _read("tr_watsons_com_tr.html")) == PlatformVerdict("sap_hybris", "angular")


# --- priority --------------------------------------------------------------


def test_a_commerce_signal_always_beats_a_framework_signal():
    """Exhaustive over every commerce signature x every render signature, in
    BOTH document orders. This is the invariant the whole finding rests on."""
    commerce = [
        ("cdn.shopify.com", "shopify"), ("cdn.salla.network", "salla"),
        ("media.zid.store", "zid"), ("woocommerce-Price-amount", "woocommerce"),
        ("data-mage-init", "magento"), ("/on/demandware.store/x", "sfcc"),
        ("smartEditComponent", "sap_hybris"), ("prestashop", "prestashop"),
        ("shopware", "shopware"), ("cdn11.bigcommerce.com/s-a/", "bigcommerce"),
        ("vtexassets.com", "vtex"),
    ]
    frameworks = [
        ("__NEXT_DATA__", "nextjs"), ("/_next/static/x.js", "nextjs"),
        ("/_nuxt/entry.css", "nuxt"), ('ng-version="19.2.7"', "angular"),
        ("react-dom.production.min.js", "react"), ("data-v-6362761e", "vue"),
        ("jquery.min.js", "classic"),
    ]
    for ctok, cwant in commerce:
        for ftok, fwant in frameworks:
            for html in ("<html>%s</html><body>%s</body>" % (ftok, ctok),
                         "<html>%s</html><body>%s</body>" % (ctok, ftok)):
                v = detect_platform_verdict(html)
                assert v.commerce_platform == cwant, (ctok, ftok)
                assert v.render_stack == fwant, (ctok, ftok)


RENDER_PRIORITY = ["nextjs", "nuxt", "angular", "react", "vue", "classic"]


def test_the_six_legacy_platforms_outrank_every_platform_added_this_wave():
    """The added signatures live in a SECOND tier that is only consulted once
    all six legacy patterns have missed. That is what makes the back-compat
    claim provable rather than hopeful: a page the old classifier placed can
    never be moved by anything added here."""
    legacy = [("cdn.shopify.com", "shopify"), ("salla.sa", "salla"),
              ("media.zid.store", "zid"), ("woocommerce-Price-amount", "woocommerce"),
              ("Magento_Catalog", "magento"), ("demandware", "sfcc")]
    added = [("smartEditComponent", "sap_hybris"), ("prestashop", "prestashop"),
             ("shopware", "shopware"), ("cdn11.bigcommerce.com/s-a/", "bigcommerce"),
             ("vtexassets.com", "vtex"), ("/media/catalog/product/x.jpg", "magento")]
    for ltok, lwant in legacy:
        for atok, _ in added:
            assert detect_platform_verdict(atok + ltok).commerce_platform == lwant
            assert detect_platform_verdict(ltok + atok).commerce_platform == lwant


def test_render_priority_is_total_over_every_pair():
    tokens = [
        ("__NEXT_DATA__", "nextjs"), ("/_next/static/x.js", "nextjs"),
        ("window.__NUXT__", "nuxt"), ("/_nuxt/e.css", "nuxt"),
        ('ng-version="19"', "angular"), ("/@angular/core", "angular"),
        ("react-dom.min.js", "react"), ("data-reactroot", "react"),
        ("data-v-6362761e", "vue"), ("window.__VUE__", "vue"),
        ("jquery.min.js", "classic"), ("requirejs", "classic"),
    ]
    for first, a in tokens:
        for second, b in tokens:
            want = min(a, b, key=RENDER_PRIORITY.index)
            got = detect_platform_verdict("<html>%s</html><body>%s</body>" % (first, second))
            assert got.render_stack == want, (first, second)


def test_nuxt_beats_the_vue_scoped_style_attribute_it_emits():
    """A Nuxt page necessarily also looks like a Vue page - it IS one. The more
    specific label wins, the same way nextjs wins over react."""
    html = '<link href="/_nuxt/entry.css"><style>.x[data-v-6362761e]{}</style>'
    assert detect_platform_verdict(html).render_stack == "nuxt"
    assert detect_platform_verdict(_read("iq_miswag_com.html")).render_stack == "nuxt"


# --- totality / hostile input ----------------------------------------------


@pytest.mark.parametrize(
    "bad", [None, b"<html>cdn.shopify.com</html>", 0, 1.5, [], {}, object()]
)
def test_a_non_string_document_is_no_evidence_not_a_crash(bad):
    assert detect_platform_verdict(bad) == PlatformVerdict("unknown", "unknown")
    assert detect_platform_verdict("", url=bad) == PlatformVerdict("unknown", "unknown")
    assert detect_platform_verdict("", robots_txt=bad) == PlatformVerdict("unknown", "unknown")


def test_only_the_capped_prefix_is_scanned_for_both_fields():
    from app.services.platform_router import MAX_SCAN_CHARS

    filler = "<p>0123456789</p>" * ((MAX_SCAN_CHARS // 17) + 100)
    assert detect_platform_verdict(
        filler + "smartEditComponent__NEXT_DATA__"
    ) == PlatformVerdict("unknown", "unknown")
    assert detect_platform_verdict(
        "smartEditComponent__NEXT_DATA__" + filler
    ) == PlatformVerdict("sap_hybris", "nextjs")


def test_the_verdict_makes_no_network_call(monkeypatch):
    import socket

    def _boom(*a, **k):  # pragma: no cover - only fires on regression
        raise AssertionError("detect_platform_verdict must not touch the network")

    monkeypatch.setattr(socket, "socket", _boom)
    monkeypatch.setattr(socket, "create_connection", _boom)
    assert detect_platform_verdict(_read("uk_theperfumeshop_com.html")) == (
        PlatformVerdict("sap_hybris", "angular"))


# --- the flag --------------------------------------------------------------
#
# `detect_platform` cannot preserve one of the values it used to return:
# "nextjs" is not a commerce platform, and removing it from the answer set IS
# the finding. So the widened wrapper is gated, per the assignment's own rule.


def test_the_flag_is_read_per_call_and_never_cached_at_import(monkeypatch):
    html = _read("it_ideabellezza_it.html")
    monkeypatch.setenv("ENABLE_PLATFORM_VERDICT", "true")
    assert detect_platform(html) == "bigcommerce"
    monkeypatch.setenv("ENABLE_PLATFORM_VERDICT", "false")
    assert detect_platform(html) == "nextjs"
    monkeypatch.setenv("ENABLE_PLATFORM_VERDICT", "true")
    assert detect_platform(html) == "bigcommerce"


def test_the_flag_defaults_on(monkeypatch):
    monkeypatch.delenv("ENABLE_PLATFORM_VERDICT", raising=False)
    assert detect_platform(_read("it_ideabellezza_it.html")) == "bigcommerce"


@pytest.mark.parametrize("off", ["false", "FALSE", "0", "no", "off", "", "  Off  "])
def test_every_off_spelling_restores_the_legacy_verdict(off, monkeypatch):
    monkeypatch.setenv("ENABLE_PLATFORM_VERDICT", off)
    assert detect_platform(_read("it_ideabellezza_it.html")) == "nextjs"


@pytest.mark.parametrize("on", ["true", "1", "yes", "on", "anything-else"])
def test_anything_that_is_not_an_off_spelling_is_on(on, monkeypatch):
    monkeypatch.setenv("ENABLE_PLATFORM_VERDICT", on)
    assert detect_platform(_read("it_ideabellezza_it.html")) == "bigcommerce"


def test_detect_platform_verdict_is_NOT_gated(monkeypatch):
    """The new function is unreachable before this commit, so there is no
    legacy behaviour for a rollback to restore. It always does the full job;
    only the back-compat wrapper is gated."""
    for state in ("true", "false"):
        monkeypatch.setenv("ENABLE_PLATFORM_VERDICT", state)
        assert detect_platform_verdict(
            _read("it_ideabellezza_it.html")).commerce_platform == "bigcommerce"


def test_the_wrapper_signature_is_unchanged():
    import inspect

    sig = inspect.signature(detect_platform)
    assert list(sig.parameters) == ["html", "url"]
    assert sig.parameters["url"].default == ""


def test_the_flag_can_only_ever_move_a_page_off_nextjs_or_unknown(monkeypatch):
    """The one behaviour change, stated as an invariant instead of a promise:
    for EVERY fixture, flag-ON differs from flag-OFF only where flag-OFF said
    `nextjs` or `unknown`."""
    for name in EXPECTED:
        html = _read(name)
        monkeypatch.setenv("ENABLE_PLATFORM_VERDICT", "false")
        off = detect_platform(html)
        monkeypatch.setenv("ENABLE_PLATFORM_VERDICT", "true")
        on = detect_platform(html)
        if off not in ("nextjs", "unknown"):
            assert on == off, name


def test_the_only_live_call_site_cannot_change_behaviour(monkeypatch):
    """`price_service` asks exactly one question of this module: is the page
    Salla or Zid (so the OpenGraph sale-price rule may run)? Both labels are
    legacy Tier-A labels, so the answer to THAT question is identical in both
    flag states on every fixture."""
    for name in EXPECTED:
        html = _read(name)
        monkeypatch.setenv("ENABLE_PLATFORM_VERDICT", "false")
        off = detect_platform(html) in {"salla", "zid"}
        monkeypatch.setenv("ENABLE_PLATFORM_VERDICT", "true")
        on = detect_platform(html) in {"salla", "zid"}
        assert off == on, name


# --- the corpus-wide invariants (skipped where _proof/ is absent) ----------


def _corpus_pages():
    import hashlib

    pages = [(str(p), "") for p in sorted(Path("_proof/global/html").glob("*.html"))]
    idx = Path("_proof/sweep2_curl_cffi.jsonl")
    if idx.is_file():
        for line in idx.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            u = row.get("url") or ""
            name = hashlib.sha1(("curl_cffi|" + u).encode("utf-8")).hexdigest() + ".html"
            f = Path("_proof/html") / name
            if f.is_file():
                pages.append((str(f), u))
    return pages


@requires_corpus
def test_over_all_521_cached_pages_the_legacy_verdict_is_preserved(monkeypatch):
    """The back-compat claim, measured rather than asserted: across every
    cached page in both corpora, whenever the legacy classifier named a
    platform (i.e. said anything other than `nextjs` or `unknown`), the new
    commerce_platform is the SAME label."""
    pages = _corpus_pages()
    assert len(pages) >= 500, "only %d cached pages found" % len(pages)
    moved = []
    for path, url in pages:
        html = Path(path).read_text(encoding="utf-8", errors="replace")
        monkeypatch.setenv("ENABLE_PLATFORM_VERDICT", "false")
        legacy = detect_platform(html, url=url)
        got = detect_platform_verdict(html, url=url).commerce_platform
        if legacy not in ("nextjs", "unknown") and got != legacy:
            moved.append((path, legacy, got))
    assert moved == []


@requires_corpus
def test_over_all_521_cached_pages_the_contract_rate_actually_improves():
    """The number the assignment asks for, pinned so it cannot silently rot.

    Measured on 521 cached pages (429 global + 92 Gulf), no network:
      legacy named a platform            238   (45.7%)
      legacy `unknown`                   230   (44.1%)
      legacy `unknown` OR `nextjs`       283   (54.3%)  <- no extraction contract
      new commerce_platform named        291   (55.9%)
      new commerce_platform `unknown`    230   (44.1%)

    Read that carefully. The headline `unknown` percentage barely moves,
    because the widened tiers recover 48 pages while the 48 ex-`nextjs` pages
    that carry no commerce signal at all correctly become `unknown` instead of
    pretending to be a platform. The honest comparison is against 54.3%: the
    share of pages with NO routable extraction contract falls 54.3% -> 44.1%.
    """
    pages = _corpus_pages()
    named = sum(
        1 for path, url in pages
        if detect_platform_verdict(
            Path(path).read_text(encoding="utf-8", errors="replace"),
            url=url,
        ).commerce_platform != "unknown"
    )
    assert named >= 291, "only %d/%d pages get a commerce contract" % (named, len(pages))


@requires_corpus
def test_no_cached_page_is_ever_labelled_with_a_framework():
    for path, url in _corpus_pages():
        html = Path(path).read_text(encoding="utf-8", errors="replace")
        v = detect_platform_verdict(html, url=url)
        assert v.commerce_platform in COMMERCE_PLATFORMS
        assert v.render_stack in RENDER_STACKS
