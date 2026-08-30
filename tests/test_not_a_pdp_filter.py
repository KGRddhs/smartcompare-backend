"""UNIT F1 — ENABLE_NOT_A_PDP_FILTER (default OFF): a fetched page that was
never a product page is named NOT-A-PDP, is never priced, and is never counted
as a render candidate.

WHAT THIS FIXES, MEASURED (E1 census over both corpora, 422 rows —
scratchpad m8/E1/not_a_pdp_table.json + census_final.json):

  * **61 of 422 corpus rows were never product pages at all**, and they were
    sitting inside the "we got no price" bucket that the pipeline reads as an
    instruction to buy a renderer or write a new extractor. Correcting the
    denominator moves the genuine render tier from ~16% of all rows to **7.8%
    of real PDPs** — i.e. roughly half of the old "render residual" was this
    class, and a quarter was walls.
  * The classes are AVOIDABLE mis-resolutions that reach the price path today:
    a deep PDP path served the storefront HOMEPAGE (the three
    ``*.abdulsamadalqurashi.com`` hosts collapse
    ``/en/black-star-perfume-for-men-100-ml/p1469448370`` to ``/en``), a
    redirect to a SEARCH decoy (``sephora.com/product/dior-sauvage-eau-de-
    toilette-P393401`` -> ``/search?keyword=productnotcarried``), an OFFSITE
    redirect (``thebay.com`` -> ``canadiantire.ca``, ``seifonline.com`` ->
    ``hugedomains.com``), a category page whose JSON-LD says ``CollectionPage``
    with no Product node anywhere (``pacoperfumerias.co.uk``), and a branded
    error shell (``boutiqaat.com`` answering HTTP 200 with
    ``<title>Oops</title>`` on five country storefronts).

THE ONE RULE THAT MAKES THIS FAIL-OPEN: a page whose JSON-LD declares a Product
node ANYWHERE is never swept, whatever else fires. Measured over all 422 rows,
that single condition takes the false-positive count on the 301 real priced
pages to **ZERO** for every detector — including the two real PDPs that carry an
``ItemList`` (a ``SiteNavigationElement`` list on ``sephora.com``), which a bare
"ItemList means category page" rule would have swept.

Flag OFF is byte-identical: no classifier runs, no outcome is written, and the
extractor returns the same dict it returns on main.

Run per-file (the full suite hangs on live network):
    pytest tests/test_not_a_pdp_filter.py \
        -m "not (live_unit or live_db or integration)" --timeout=120 \
        -p no:cacheprovider
"""

import asyncio
import json
import os
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from app.services import price_service as ps
from app.services.price_service import extract_price_from_html

FIXTURES = Path(__file__).parent / "fixtures" / "not_a_pdp"

BOUTIQAAT = "kw_boutiqaat_com_oops_error_shell.html"
ASQ = "kw_abdulsamadalqurashi_com_homepage_collapse.html"
PACO = "gb_pacoperfumerias_co_uk_collectionpage.html"
SEPHORA_SEARCH = "us_sephora_com_search_redirect_target.html"
NISHANE = "tr_nishane_com_real_pdp.html"
SEPHORA_PDP = "us_sephora_com_real_pdp_itemlist_and_product.html"

# The REQUESTED urls, verbatim from the corpus rows (SOURCES.json).
BOUTIQAAT_URL = "https://www.boutiqaat.com/en-kw/women/bonbon-eau-de-parfum-50-ml-1/p/"
ASQ_URL = ("https://kw.abdulsamadalqurashi.com/en/"
           "black-star-perfume-for-men-100-ml/p1469448370")
PACO_URL = ("https://www.pacoperfumerias.co.uk/fragrance/womens/fragrance/"
            "bvlgari/omnia-crystalline.html")
SEPHORA_SEARCH_URL = "https://www.sephora.com/product/dior-sauvage-eau-de-toilette-P393401"
SEPHORA_SEARCH_FINAL = "https://www.sephora.com/search?keyword=productnotcarried"
NISHANE_URL = "https://nishane.com/product/hacivat-x-15ml/"
SEPHORA_PDP_URL = "https://www.sephora.com/product/dior-sauvage-elixir-P475526"


def load(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


@pytest.fixture(autouse=True)
def _defaults(monkeypatch):
    """Default OFF is the shipped state; each test that needs it ON says so."""
    monkeypatch.delenv("ENABLE_NOT_A_PDP_FILTER", raising=False)
    monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "false")
    yield


def _f1(monkeypatch, value: str):
    monkeypatch.setenv("ENABLE_NOT_A_PDP_FILTER", value)


# ===========================================================================
# A — THE FLAG
# ===========================================================================
def test_a_a_default_is_off():
    """New flags default OFF (CLAUDE.md). Nothing about the price path changes
    until Railway flips it."""
    assert ps.not_a_pdp_filter_enabled() is False


def test_a_b_the_flag_is_read_per_call_never_cached_at_import(monkeypatch):
    """Copies the ``exact_gate_enabled`` idiom so a Railway flip lands without
    a restart."""
    _f1(monkeypatch, "true")
    assert ps.not_a_pdp_filter_enabled() is True
    _f1(monkeypatch, "false")
    assert ps.not_a_pdp_filter_enabled() is False
    monkeypatch.delenv("ENABLE_NOT_A_PDP_FILTER", raising=False)
    assert ps.not_a_pdp_filter_enabled() is False


def test_a_c_the_flag_name_appears_nowhere_at_module_scope():
    """A getenv evaluated at import would freeze the flag at process start."""
    source = Path(ps.__file__).read_text(encoding="utf-8")
    reads = [ln for ln in source.splitlines()
             if "ENABLE_NOT_A_PDP_FILTER" in ln and "getenv" in ln]
    assert reads, "the flag must be read somewhere"
    for line in reads:
        assert line.startswith("    "), (
            "ENABLE_NOT_A_PDP_FILTER must only be read inside a function: " + line
        )


# ===========================================================================
# B — ONE CASE PER MEASURED CLASS
# ===========================================================================
def test_b_a_a_branded_error_shell_is_not_a_pdp():
    """boutiqaat.com answers HTTP 200 with ``<title>Oops</title>`` on five
    country storefronts; the full page is 3.9MB, so it reads today as a real
    page with no structured price — an EXTRACTOR instruction for a page that
    has no product on it."""
    assert ps.classify_not_a_pdp(load(BOUTIQAAT), BOUTIQAAT_URL) == ps.NOT_A_PDP_ERROR_SHELL


def test_b_b_a_deep_pdp_path_served_the_homepage_is_not_a_pdp():
    """kw/om/qa.abdulsamadalqurashi.com collapse a deep product path onto the
    storefront home. The page's OWN canonical and og:url say ``/en`` while the
    requested path is ``/en/black-star-perfume-for-men-100-ml/p1469448370`` —
    so this is readable from the bytes, with no redirect bookkeeping."""
    assert ps.classify_not_a_pdp(load(ASQ), ASQ_URL) == ps.NOT_A_PDP_REDIRECT_HOMEPAGE


def test_b_c_a_search_decoy_redirect_is_not_a_pdp():
    """sephora.com serves ``/search?keyword=productnotcarried`` for a product
    it does not carry. The 587KB redirect TARGET carries no canonical, no
    og:url and zero ld+json — the fact is only in the FINAL URL, which is why
    the classifier takes one."""
    assert ps.classify_not_a_pdp(
        load(SEPHORA_SEARCH), SEPHORA_SEARCH_URL, final_url=SEPHORA_SEARCH_FINAL,
    ) == ps.NOT_A_PDP_REDIRECT_SEARCH


def test_b_d_an_offsite_redirect_is_not_a_pdp():
    """thebay.com -> canadiantire.ca and seifonline.com -> hugedomains.com. The
    page in hand is not from the host the selector chose."""
    assert ps.classify_not_a_pdp(
        "<html><head><title>Hudson's Bay Stripes | Canadian Tire</title></head></html>",
        "https://www.thebay.com/product/dior-sauvage-eau-de-toilette-0400089256427",
        final_url="https://www.canadiantire.ca/en/inspiration/hudsonsbay.html",
    ) == ps.NOT_A_PDP_REDIRECT_OFFSITE


def test_b_e_a_collectionpage_with_no_product_node_is_not_a_pdp():
    """pacoperfumerias.co.uk serves a product-shaped URL whose JSON-LD declares
    ``@type: CollectionPage`` and carries no Product node anywhere in its 405KB."""
    assert ps.classify_not_a_pdp(load(PACO), PACO_URL) == ps.NOT_A_PDP_CATEGORY_PAGE


def test_b_f_the_reasons_are_a_closed_named_set():
    for reason in (ps.NOT_A_PDP_ERROR_SHELL, ps.NOT_A_PDP_REDIRECT_HOMEPAGE,
                   ps.NOT_A_PDP_REDIRECT_SEARCH, ps.NOT_A_PDP_REDIRECT_OFFSITE,
                   ps.NOT_A_PDP_CATEGORY_PAGE):
        assert reason in ps.NOT_A_PDP_REASONS
    assert len(set(ps.NOT_A_PDP_REASONS)) == 5


# ===========================================================================
# C — REAL PDPs ARE NEVER SWEPT (the fail-open half, and the falsifiers)
# ===========================================================================
def test_c_a_a_real_pdp_is_not_swept():
    """nishane.com — E1 recorded that a challenge heuristic mis-flagged these
    pages, so they are pinned here explicitly."""
    assert ps.classify_not_a_pdp(load(NISHANE), NISHANE_URL) is None


def test_c_b_a_real_pdp_carrying_an_itemlist_is_not_swept():
    """THE FALSIFIER for a bare "ItemList means category page" rule: a real
    sephora.com PDP ships an ``@type: ItemList`` (its SiteNavigationElement
    list) beside its ProductGroup. Only the absence of a Product node separates
    a listing from a PDP."""
    html = load(SEPHORA_PDP)
    assert '"ItemList"' in html
    assert ps.classify_not_a_pdp(html, SEPHORA_PDP_URL) is None


def test_c_c_a_product_node_vetoes_every_detector():
    """The single fail-open rule, stated directly: bolt the loudest possible
    NOT-A-PDP evidence onto a page that declares a Product and nothing fires."""
    product_block = (
        '<script type="application/ld+json">'
        '{"@context":"https://schema.org","@type":"Product","name":"Sauvage EDT",'
        '"offers":{"@type":"Offer","price":"77.000","priceCurrency":"BHD"}}'
        "</script>"
    )
    html = (
        "<html><head><title>Oops</title>"
        '<link rel="canonical" href="https://shop.example.com/en"/>'
        '<script type="application/ld+json">{"@type":"CollectionPage"}</script>'
        + product_block
        + "</head><body></body></html>"
    )
    assert ps.classify_not_a_pdp(
        html, "https://shop.example.com/en/products/sauvage-edt-100ml",
        final_url="https://shop.example.com/search?q=sauvage",
    ) is None


def test_c_d_the_error_phrase_is_title_anchored_never_a_body_substring():
    """The swissarabian lesson: ``access denied`` living in a JS comment made a
    body substring test fire on a served page. An error word in the BODY, or
    late in a real product title, is not evidence."""
    body_only = (
        "<html><head><title>Sauvage Eau de Toilette 100ml | Klinq</title></head>"
        "<body><script>// oops, not found: fallback to error handler</script>"
        "<p>Oops! You have no items in your wishlist.</p></body></html>"
    )
    assert ps.classify_not_a_pdp(body_only, "https://klinq.com/products/sauvage") is None


def test_c_e_an_error_word_inside_a_real_title_does_not_fire():
    """Title-START anchored: the phrase has to BE the title, not appear in it."""
    html = ("<html><head><title>Trial and Error Eau de Parfum 50ml - Brand</title>"
            "</head><body></body></html>")
    assert ps.classify_not_a_pdp(html, "https://x.com/products/trial-and-error") is None


def test_c_f_a_homepage_request_is_not_a_redirect_collapse():
    """The collapse is a DEEP path served the home page. When the selector
    handed us the homepage URL itself, that is a discovery defect, not a
    capture outcome, and this classifier says nothing about it."""
    html = ('<html><head><title>Store</title>'
            '<link rel="canonical" href="https://x.com/en"/></head><body></body></html>')
    assert ps.classify_not_a_pdp(html, "https://x.com/en") is None


def test_c_g_a_cross_domain_canonical_alone_never_sweeps():
    """A canonical is the page's CLAIM about where it belongs (a Shopify store
    on a custom domain does exactly this); only a cross-domain FINAL URL is a
    fetch FACT. Measured: allowing body-derived offsite adds zero catches."""
    html = ('<html><head><title>Sauvage EDT</title>'
            '<link rel="canonical" href="https://brand.com/products/sauvage"/>'
            "</head><body></body></html>")
    assert ps.classify_not_a_pdp(
        html, "https://brand.myshopify.com/products/sauvage") is None


# ===========================================================================
# D — THE OUTCOME CONTRACT
# ===========================================================================
def test_d_a_not_a_pdp_is_a_capture_outcome():
    """It is a sixth INSTRUCTION, and it belongs in the enumeration for the
    same reason the other five do: a wall needs a different fetch channel, a
    shell needs a renderer, a markup-less page needs an extractor, a
    multiplicity needs a discriminator — and a page that was never a product
    page needs none of those. It needs a better SELECTION."""
    assert ps.CAPTURE_NOT_A_PDP == "not_a_pdp"
    assert ps.CAPTURE_NOT_A_PDP in ps.CAPTURE_OUTCOMES
    assert set(ps.CAPTURE_OUTCOMES) == {
        "ok", "walled", "empty_shell", "no_structured_price", "ambiguous_price",
        "not_a_pdp",
    }


def test_d_b_classify_capture_itself_never_returns_it():
    """``classify_capture`` stays total over (html, price, status) and NOTHING
    else — the redirect facts are not in the bytes. The new outcome is stamped
    by the extractor, which is the frame that knows the url."""
    for html in (load(BOUTIQAAT), load(ASQ), load(PACO), load(SEPHORA_SEARCH), ""):
        assert ps.classify_capture(html) != ps.CAPTURE_NOT_A_PDP


def test_d_c_the_outcome_replaces_the_render_instruction(monkeypatch):
    """THE POINT OF THE UNIT. Flag OFF these four pages are named with an
    instruction to go buy a renderer or write an extractor; flag ON they are
    named as never having been product pages."""
    for name, url, final in (
        (BOUTIQAAT, BOUTIQAAT_URL, None),
        (ASQ, ASQ_URL, None),
        (PACO, PACO_URL, None),
        (SEPHORA_SEARCH, SEPHORA_SEARCH_URL, SEPHORA_SEARCH_FINAL),
    ):
        html = load(name)
        off = []
        monkeypatch.delenv("ENABLE_NOT_A_PDP_FILTER", raising=False)
        extract_price_from_html(html, "Dior Sauvage", "BHD", "x.com", url,
                                outcome_out=off, final_url=final)
        assert off and off[0] in (ps.CAPTURE_EMPTY_SHELL, ps.CAPTURE_NO_STRUCTURED_PRICE), (
            name, off)

        on = []
        _f1(monkeypatch, "true")
        extract_price_from_html(html, "Dior Sauvage", "BHD", "x.com", url,
                                outcome_out=on, final_url=final)
        assert on == [ps.CAPTURE_NOT_A_PDP], (name, on)


def test_d_d_a_not_a_pdp_page_is_never_priced(monkeypatch):
    """A category page CAN carry an offer the ladder would read. Flag ON it is
    dropped, because a price from a page that is not the product page is a
    wrong price however well-formed it is."""
    html = (
        "<html><head><title>Perfumes</title>"
        '<script type="application/ld+json">{"@context":"https://schema.org",'
        '"@type":"CollectionPage","name":"Bvlgari"}</script>'
        '<meta property="og:price:amount" content="59.90"/>'
        '<meta property="og:price:currency" content="BHD"/>'
        '<meta property="og:title" content="Bvlgari Omnia Crystalline"/>'
        "</head><body></body></html>"
    )
    url = "https://www.pacoperfumerias.co.uk/fragrance/womens/bvlgari/omnia.html"
    monkeypatch.delenv("ENABLE_NOT_A_PDP_FILTER", raising=False)
    legacy = extract_price_from_html(html, "Bvlgari Omnia", "BHD", "pacoperfumerias.co.uk", url)
    assert legacy and legacy["amount"] == 59.90

    _f1(monkeypatch, "true")
    out = []
    got = extract_price_from_html(html, "Bvlgari Omnia", "BHD", "pacoperfumerias.co.uk",
                                  url, outcome_out=out)
    assert got is None
    assert out == [ps.CAPTURE_NOT_A_PDP]


def test_d_e_a_real_pdp_still_prices_with_the_flag_on(monkeypatch):
    """The other half of D-d: turning the filter on must not cost a real page
    its price."""
    _f1(monkeypatch, "true")
    out = []
    got = extract_price_from_html(load(NISHANE), "Nishane Hacivat", "EUR",
                                  "nishane.com", NISHANE_URL, outcome_out=out)
    assert got is not None and got.get("amount")
    assert out == [ps.CAPTURE_OK]


# ===========================================================================
# E — FLAG OFF IS BYTE-IDENTICAL
# ===========================================================================
@pytest.mark.parametrize("name,url,final", [
    (BOUTIQAAT, BOUTIQAAT_URL, None),
    (ASQ, ASQ_URL, None),
    (PACO, PACO_URL, None),
    (SEPHORA_SEARCH, SEPHORA_SEARCH_URL, SEPHORA_SEARCH_FINAL),
    (NISHANE, NISHANE_URL, None),
    (SEPHORA_PDP, SEPHORA_PDP_URL, None),
])
def test_e_a_flag_off_returns_the_legacy_dict(monkeypatch, name, url, final):
    """Flag OFF the classifier never runs and the extractor's answer is the one
    it gives with the parameter absent entirely."""
    monkeypatch.delenv("ENABLE_NOT_A_PDP_FILTER", raising=False)
    html = load(name)
    baseline = extract_price_from_html(html, "Dior Sauvage", "BHD", "x.com", url)
    with_param = extract_price_from_html(html, "Dior Sauvage", "BHD", "x.com", url,
                                         final_url=final)
    assert json.dumps(baseline, sort_keys=True, default=str) == json.dumps(
        with_param, sort_keys=True, default=str)


def test_e_b_flag_off_writes_no_outcome_beyond_the_legacy_five(monkeypatch):
    monkeypatch.delenv("ENABLE_NOT_A_PDP_FILTER", raising=False)
    for name, url in ((BOUTIQAAT, BOUTIQAAT_URL), (ASQ, ASQ_URL), (PACO, PACO_URL)):
        out = []
        extract_price_from_html(load(name), "Dior Sauvage", "BHD", "x.com", url,
                                outcome_out=out)
        assert out and ps.CAPTURE_NOT_A_PDP not in out


# ===========================================================================
# F — TOTALITY. A classifier that can raise is a classifier that can take the
# price path down with it.
# ===========================================================================
@pytest.mark.parametrize("html", [None, "", b"bytes", 3, [], {}, object()])
def test_f_a_total_over_html(html):
    assert ps.classify_not_a_pdp(html, "https://x.com/p/1") in (None,) + tuple(
        ps.NOT_A_PDP_REASONS)


@pytest.mark.parametrize("url", [None, "", "not a url", 7, object(), "http://", "///"])
def test_f_b_total_over_url(url):
    assert ps.classify_not_a_pdp("<html><title>Oops</title></html>", url) in (
        None,) + tuple(ps.NOT_A_PDP_REASONS)


@pytest.mark.parametrize("final", [None, "", 7, object(), "javascript:alert(1)", "///"])
def test_f_c_total_over_final_url(final):
    assert ps.classify_not_a_pdp(
        "<html><title>Sauvage</title></html>", "https://x.com/p/1", final_url=final,
    ) in (None,) + tuple(ps.NOT_A_PDP_REASONS)


def test_f_d_unreadable_jsonld_is_not_evidence():
    """A block that will not parse says nothing either way — and must not
    become a "no Product node" verdict on a page whose Product node is inside
    it."""
    html = ("<html><head><title>Oops</title>"
            '<script type="application/ld+json">{not json at all</script>'
            "</head><body></body></html>")
    # No Product is READABLE, so the error-shell verdict still stands — but the
    # call must return, not raise.
    assert ps.classify_not_a_pdp(html, "https://x.com/p/1") in (
        None, ps.NOT_A_PDP_ERROR_SHELL)


# ===========================================================================
# G — NEVER COUNTED AS A RENDER CANDIDATE
# ===========================================================================
def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def test_g_a_fetch_page_price_returns_the_render_sentinel_with_the_flag_off(monkeypatch):
    """``{"_got_html": True}`` is the page-level "we have bytes but no price"
    token — the thing that says a renderer might help. Flag OFF, a NOT-A-PDP
    page still emits it, exactly as on main."""
    monkeypatch.delenv("ENABLE_NOT_A_PDP_FILTER", raising=False)
    monkeypatch.setattr(ps, "ENABLE_PAGE_SCRAPE", True)

    async def _fake(url, domain, **kw):
        if isinstance(kw.get("final_url_out"), list):
            kw["final_url_out"].append(url)
        return load(BOUTIQAAT)

    monkeypatch.setattr(ps, "curl_fetch_html_same_site", _fake)
    got = _run(ps.fetch_page_price(BOUTIQAAT_URL, "Dior Sauvage", "BHD"))
    assert got == {"_got_html": True}


def test_g_b_a_not_a_pdp_page_is_not_a_render_candidate(monkeypatch):
    """Flag ON, the same page returns an honest None: no renderer, no
    extractor, no paid escalation will ever find a product on it."""
    _f1(monkeypatch, "true")
    monkeypatch.setattr(ps, "ENABLE_PAGE_SCRAPE", True)

    async def _fake(url, domain, **kw):
        if isinstance(kw.get("final_url_out"), list):
            kw["final_url_out"].append(url)
        return load(BOUTIQAAT)

    monkeypatch.setattr(ps, "curl_fetch_html_same_site", _fake)
    assert _run(ps.fetch_page_price(BOUTIQAAT_URL, "Dior Sauvage", "BHD")) is None


def test_g_c_the_search_decoy_needs_the_final_url_and_gets_it(monkeypatch):
    """The runtime half of B-c: the same-site fetch FOLLOWS a same-host
    redirect, so the only place the search-decoy fact exists is the terminal
    url — and ``curl_fetch_html_same_site`` now reports it on request."""
    _f1(monkeypatch, "true")
    monkeypatch.setattr(ps, "ENABLE_PAGE_SCRAPE", True)

    async def _fake(url, domain, **kw):
        if isinstance(kw.get("final_url_out"), list):
            kw["final_url_out"].append(SEPHORA_SEARCH_FINAL)
        return load(SEPHORA_SEARCH)

    monkeypatch.setattr(ps, "curl_fetch_html_same_site", _fake)
    assert _run(ps.fetch_page_price(SEPHORA_SEARCH_URL, "Dior Sauvage", "BHD")) is None


def test_g_d_a_real_pdp_still_reaches_the_price_path(monkeypatch):
    _f1(monkeypatch, "true")
    monkeypatch.setattr(ps, "ENABLE_PAGE_SCRAPE", True)

    async def _fake(url, domain, **kw):
        if isinstance(kw.get("final_url_out"), list):
            kw["final_url_out"].append(url)
        return load(NISHANE)

    monkeypatch.setattr(ps, "curl_fetch_html_same_site", _fake)
    got = _run(ps.fetch_page_price(NISHANE_URL, "Nishane Hacivat", "EUR"))
    assert got and got.get("amount")


def test_g_e_the_final_url_out_channel_is_opt_in(monkeypatch):
    """``curl_fetch_html_same_site`` reports the terminal url only when a list
    is handed to it; every existing caller is untouched."""
    import inspect
    sig = inspect.signature(ps.curl_fetch_html_same_site)
    assert "final_url_out" in sig.parameters
    assert sig.parameters["final_url_out"].default is None


# ===========================================================================
# H — THE CORPUS PIN. The fail-open claim is a measured number, so it is
# asserted as one on the fixtures that stand in for each side.
# ===========================================================================
def test_h_every_fixture_has_provenance():
    meta = json.loads((FIXTURES / "SOURCES.json").read_text(encoding="utf-8"))
    on_disk = {p.name for p in FIXTURES.glob("*.html")}
    assert on_disk == set(meta["files"])
    for name, row in meta["files"].items():
        assert row.get("url") and row.get("cached_bytes") and row.get("kept")
