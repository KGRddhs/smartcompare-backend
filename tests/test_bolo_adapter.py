"""Wave 3a (BH Source-Intelligence, 2026-06-23) — bolo.bh adapter.

bolo.bh is a Nuxt SSR storefront whose PDPs are PLAIN-CURL READABLE. The genuine
BHD price is in the PDP's schema.org JSON-LD `@graph` → Product → offers
(priceCurrency=BHD) AND mirrored in a Nuxt `"price":N` token next to a
`<sup class="currency">BHD</sup>`.

THE BINDING TRAP (F3a): the real PDP HTML carries MULTIPLE "price" values (the
main product + a related-items carousel, e.g. 24.89 main vs 132/133 related). The
adapter MUST bind the MAIN product. Two live-verified facts make this safe:
the FIRST `@graph` Product is the PDP's primary product, and the FIRST Nuxt
`"price"` token is the main price (carousel prices trail it).

`fetch_bolo_price(name, currency)` resolves the PDP via the Wave-2 sitemap index
(Redis read, no crawl) → curl-fetches it → parses the JSON-LD main-product offer
(then the Nuxt `"price"` fallback) → a genuine
`source_method="page_scrape_jsonld"` price dict, or `None` (a no-resolve/no-price
returns None, NOT a pending dict — the WS-2 _price_fallback_on_miss revert lesson).

LIVE-VERIFIED 2026-06-23 (out-of-band probe):
  - Kensington Wireless Presenter K33272WW → 24.89 BHD (@graph offer)
  - e.l.f. SKIN Holy Hydration Triple Bounce Serum → 8.16 BHD (@graph offer; the
    generic brand-gated extract_jsonld_price false-negatives here — its
    accessory/brand guards reject the long marketing name — proving the adapter
    needs the bolo-specific @graph main-product extractor, NOT the generic one).

The fixtures (tests/fixtures/bolo_pdp_*.html) are SLIM REAL slices (the live
JSON-LD offer + a multi-price Nuxt blob carrying the carousel trap). NO network.
"""

from pathlib import Path

import pytest

from app.services.price_service import (
    _bolo_jsonld_main_price,
    _bolo_nuxt_main_price,
    fetch_bolo_price,
)

FX_ELF = Path(__file__).parent / "fixtures" / "bolo_pdp_elf_serum.html"
FX_KENSINGTON = Path(__file__).parent / "fixtures" / "bolo_pdp_kensington.html"


@pytest.fixture
def elf_html():
    return FX_ELF.read_text(encoding="utf-8")


@pytest.fixture
def kensington_html():
    return FX_KENSINGTON.read_text(encoding="utf-8")


# --- JSON-LD main-product extractor (the primary path) -------------------

class TestBoloJsonldMainPrice:
    def test_extracts_kensington_main_offer_bhd(self, kensington_html):
        """@graph Product offers → 24.89 BHD, binding the MAIN product (NOT the
        carousel 132/133)."""
        res = _bolo_jsonld_main_price(
            kensington_html, "Kensington Wireless Presenter K33272WW", "BHD",
        )
        assert res is not None
        assert res["amount"] == pytest.approx(24.89)
        assert res["currency"] == "BHD"
        assert res["in_stock"] is True

    def test_extracts_elf_serum_where_generic_jsonld_fails(self, elf_html):
        """The proof the bolo-specific extractor is needed: the @graph offer is
        8.16 BHD even though the generic brand-gated extract_jsonld_price returns
        None (accessory/brand guards reject the long marketing name)."""
        res = _bolo_jsonld_main_price(
            elf_html, "e.l.f. Holy Hydration Triple Bounce Serum", "BHD",
        )
        assert res is not None
        assert res["amount"] == pytest.approx(8.16)
        assert res["currency"] == "BHD"
        # cross-check: the generic extractor really does miss this one
        from app.services.price_service import extract_jsonld_price
        generic = extract_jsonld_price(
            elf_html, "elf", "BHD",
            query_name="e.l.f. Holy Hydration Triple Bounce Serum",
        )
        assert generic is None

    def test_binds_main_not_carousel_multiprice(self, kensington_html):
        """With multiple prices on the page, the @graph main Product offer wins —
        never a 132/133 carousel item."""
        res = _bolo_jsonld_main_price(kensington_html, "Kensington Wireless Presenter", "BHD")
        assert res["amount"] == pytest.approx(24.89)
        assert res["amount"] not in (132.0, 133.0)

    def test_variant_mismatch_query_rejects(self, kensington_html):
        """A query naming a different model-line variant than the PDP product is
        rejected (no wrong-SKU price attribution)."""
        # The PDP product has no variant qualifier; a 'Pro' query mismatches.
        res = _bolo_jsonld_main_price(kensington_html, "Kensington Pro Presenter", "BHD")
        assert res is None

    def test_malformed_html_returns_none(self):
        assert _bolo_jsonld_main_price("", "x", "BHD") is None
        assert _bolo_jsonld_main_price("<html>no ld</html>", "x", "BHD") is None

    def test_nameless_product_node_is_not_attributed(self):
        """Source-intel review 2026-06-23 (no-fab fail-closed): a JSON-LD Product
        node with NO `name` is UNVALIDATABLE — its offer must NOT be returned (the
        query can't be bound to it), even though a BHD offer is present. Returns
        None → honest miss, NOT a wrong-product price stamped genuine."""
        nameless = (
            '<html><body><script type="application/ld+json">'
            '{"@graph":[{"@type":"Product",'
            '"offers":{"@type":"Offer","price":"24.89","priceCurrency":"BHD",'
            '"availability":"https://schema.org/InStock"}}]}'
            '</script></body></html>'
        )
        assert _bolo_jsonld_main_price(nameless, "CeraVe Vitamin C Serum", "BHD") is None

    def test_empty_token_query_does_not_vacuously_pass(self):
        """An all-punctuation query normalizes to NO tokens — the word-overlap bind
        must fail-closed (not vacuously accept the first BHD offer)."""
        named = (
            '<html><body><script type="application/ld+json">'
            '{"@graph":[{"@type":"Product","name":"Kensington Wireless Presenter",'
            '"offers":{"price":"24.89","priceCurrency":"BHD"}}]}'
            '</script></body></html>'
        )
        assert _bolo_jsonld_main_price(named, "---", "BHD") is None

    def test_wrong_product_jsonld_with_matching_numbers_is_rejected(self):
        """Codex HIGH-1 (no-fab / WORST failure): a sitemap mis-resolve to a
        DIFFERENT fragrance whose name shares the size number but NOT the key
        product word must NOT have its price stamped genuine.

        "Tom Ford Oud Wood 100ml" vs an "Oud Minerale Eau de Parfum 100ml" PDP:
        the OLD guards all PASS — numbers_match passes VACUOUSLY ("100ml" yields no
        \\b\\d{2,}\\b token, so there is no number to compare), no variant qualifier
        differs, and the word-overlap is 4/5 == 0.8 ({tom,ford,oud,100ml} shared,
        only "wood" missing) — far above the 0.4 floor, so raising that floor would
        NOT catch it → 94 BHD was accepted as a genuine page_scrape_jsonld price.
        strict_title_match is the discriminating guard: "wood" is absent from "Oud
        Minerale" → every key word does NOT appear → rejected."""
        wrong = (
            '<html><body><script type="application/ld+json">'
            '{"@graph":[{"@type":"Product",'
            '"name":"Tom Ford Oud Minerale Eau de Parfum 100ml",'
            '"offers":{"@type":"Offer","price":"94","priceCurrency":"BHD",'
            '"availability":"https://schema.org/InStock"}}]}'
            '</script></body></html>'
        )
        # Sanity-check the trap really is a trap under the OLD guards:
        from app.services.price_service import (
            numbers_match,
            variant_mismatch,
            normalize_words,
        )
        q = "Tom Ford Oud Wood 100ml"
        ld = "Tom Ford Oud Minerale Eau de Parfum 100ml"
        assert numbers_match(q, ld) is True  # vacuous: "100ml" yields no \d{2,} token
        assert variant_mismatch(q, ld) is False
        pw = normalize_words(q)
        # The real overlap is 0.8 (only "wood" missing) — the 0.4 word-overlap guard
        # was never close to catching this; strict_title_match is what closes it.
        assert pw and (len(pw & normalize_words(ld)) / len(pw)) == pytest.approx(0.8)
        # With strict_title_match in place the wrong product is rejected → None,
        # NOT the 94 BHD offer.
        assert _bolo_jsonld_main_price(wrong, q, "BHD") is None


# --- Nuxt fallback (only fires when JSON-LD has no offer) -----------------

class TestBoloNuxtMainPrice:
    def test_binds_first_price_token_main_product(self, elf_html):
        """The FIRST Nuxt `"price"` token is the main product (8.16), NOT a
        trailing carousel value (205/130/139)."""
        res = _bolo_nuxt_main_price(elf_html, "BHD")
        assert res is not None
        assert res["amount"] == pytest.approx(8.16)
        assert res["amount"] not in (205.0, 130.0, 139.0)

    def test_requires_bhd_currency_sup(self):
        """Without a `<sup class="currency">BHD</sup>` marker, a Nuxt number is
        NOT BHD-stamped (no blind currency stamp)."""
        no_bhd = '<html><body><script>x={"price":42}</script></body></html>'
        assert _bolo_nuxt_main_price(no_bhd, "BHD") is None

    def test_no_price_token_returns_none(self):
        assert _bolo_nuxt_main_price("<sup class='currency'>BHD</sup>", "BHD") is None


# --- Network wrapper (monkeypatched resolve + fetch — NO live network) ----

class TestFetchBoloPrice:
    @pytest.mark.asyncio
    async def test_resolve_then_fetch_genuine_jsonld(self, kensington_html, monkeypatch):
        """Happy path: resolve a PDP URL → curl-fetch → JSON-LD main price →
        genuine page_scrape_jsonld dict bound to bolo.bh."""
        import app.services.price_service as ps
        monkeypatch.setattr(
            "app.services.sitemap_discovery_service.resolve_pdp_via_sitemap",
            lambda domain, query: "https://www.bolo.bh/products/UO0872Z3OMT-kensington-wireless-presenter",
        )

        async def fake_fetch(url, domain):
            return kensington_html
        monkeypatch.setattr(ps, "curl_fetch_html_same_site", fake_fetch)

        res = await fetch_bolo_price("Kensington Wireless Presenter K33272WW", "BHD")
        assert res is not None
        assert res["amount"] == pytest.approx(24.89)
        assert res["currency"] == "BHD"
        assert res["source_method"] == "page_scrape_jsonld"
        assert res["retailer"] == "bolo.bh"
        assert res["estimated"] is False
        assert res["url"].startswith("https://www.bolo.bh/products/")

    @pytest.mark.asyncio
    async def test_no_resolve_returns_none_not_pending(self, monkeypatch):
        """A cold/missing sitemap index (resolve → None) → None, NOT a pending
        dict (the cascade continues to an honest pending downstream)."""
        monkeypatch.setattr(
            "app.services.sitemap_discovery_service.resolve_pdp_via_sitemap",
            lambda domain, query: None,
        )
        res = await fetch_bolo_price("CeraVe Vitamin C Serum", "BHD")
        assert res is None  # not a {"unavailable": True} pending dict

    @pytest.mark.asyncio
    async def test_resolve_but_fetch_empty_returns_none(self, monkeypatch):
        import app.services.price_service as ps
        monkeypatch.setattr(
            "app.services.sitemap_discovery_service.resolve_pdp_via_sitemap",
            lambda domain, query: "https://www.bolo.bh/products/x",
        )

        async def fake_fetch(url, domain):
            return None
        monkeypatch.setattr(ps, "curl_fetch_html_same_site", fake_fetch)
        assert await fetch_bolo_price("anything", "BHD") is None

    @pytest.mark.asyncio
    async def test_nuxt_fallback_when_jsonld_absent(self, monkeypatch):
        """When the PDP has NO JSON-LD offer but a Nuxt price + BHD sup, the
        fallback yields the genuine main price."""
        import app.services.price_service as ps
        # Real bolo Nuxt SSR uses QUOTED "price":N (verified live 2026-06-23). The
        # main product token leads; a related-items carousel token trails it.
        nuxt_only = (
            '<html><body><div class="product-main"><sup class="currency">BHD</sup></div>'
            '<script>window.__NUXT__={data:[{product:{"price":12.50,"currency":"BHD"},'
            '"related":[{"price":99}]}]}</script></body></html>'
        )
        monkeypatch.setattr(
            "app.services.sitemap_discovery_service.resolve_pdp_via_sitemap",
            lambda domain, query: "https://www.bolo.bh/products/x-foo",
        )

        async def fake_fetch(url, domain):
            return nuxt_only
        monkeypatch.setattr(ps, "curl_fetch_html_same_site", fake_fetch)
        res = await fetch_bolo_price("Foo Product", "BHD")
        assert res is not None
        assert res["amount"] == pytest.approx(12.50)
        assert res["source_method"] == "page_scrape_jsonld"

    @pytest.mark.asyncio
    async def test_jsonld_mismatch_does_not_fall_to_nuxt(self, kensington_html, monkeypatch):
        """Wave-3 reviewer ISSUE 1 (no-fab / wrong-SKU): a sitemap mis-resolve to a
        WRONG-product PDP — whose JSON-LD product is REJECTED (numbers/variant/
        word-overlap mismatch) — must NOT fall through to the unvalidated Nuxt
        "price". The kensington PDP's JSON-LD product is a Kensington Presenter;
        querying a completely different product must return None, NEVER the Nuxt
        carousel/main number."""
        import app.services.price_service as ps
        monkeypatch.setattr(
            "app.services.sitemap_discovery_service.resolve_pdp_via_sitemap",
            lambda domain, query: "https://www.bolo.bh/products/x-wrong-resolve",
        )

        async def fake_fetch(url, domain):
            return kensington_html
        monkeypatch.setattr(ps, "curl_fetch_html_same_site", fake_fetch)
        # A completely unrelated product (no shared tokens with the kensington PDP).
        res = await fetch_bolo_price("Logitech MX Master 3S Wireless Mouse", "BHD")
        assert res is None, f"wrong-product PDP must not yield a price, got {res}"


# --- SSRF-via-redirect regression (Codex HIGH-5) -----------------------------
# curl_fetch_html_same_site validates EVERY redirect hop. The old curl_fetch_html
# used allow_redirects=True, so a same-site bolo.bh PDP could 30x-redirect to a
# private IP / off-host. We mock at the curl_cffi.requests.get layer (a fake
# response with status_code/headers/text) — NO live network, NO DNS.

class _FakeCurlResp:
    def __init__(self, status_code, headers=None, text=""):
        self.status_code = status_code
        self.headers = headers or {}
        self.text = text


def _install_curl_redirect_chain(monkeypatch, chain):
    """Mock curl_cffi.requests.get with a url→response map and capture the call
    order. ``chain`` is a dict of {url: _FakeCurlResp}. Unknown urls 404."""
    calls = []

    def fake_get(url, **kwargs):
        # The same-site fetcher MUST disable curl's own redirect-following.
        assert kwargs.get("allow_redirects") is False, (
            "curl_fetch_html_same_site must call curl with allow_redirects=False"
        )
        calls.append(url)
        return chain.get(url, _FakeCurlResp(404))

    import curl_cffi.requests as curl_requests
    monkeypatch.setattr(curl_requests, "get", fake_get)
    return calls


def _stub_validator_blocking_link_local(monkeypatch):
    """Replace validate_external_url with a DNS-free stub that mirrors the real
    semantics for these tests: reject non-http(s) and link-local/private/loopback
    LITERAL-IP hosts; accept public hostnames (no socket call). Keeps the test
    fully offline while still proving the same-site fetcher's per-hop gate."""
    import ipaddress
    from urllib.parse import urlparse as _up

    def fake_validate(url):
        p = _up(url)
        if p.scheme not in ("http", "https"):
            return False
        host = p.hostname
        if not host:
            return False
        try:
            ip = ipaddress.ip_address(host)
        except ValueError:
            return True  # a hostname (not a literal IP) → treated as public here
        return not (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved)

    monkeypatch.setattr("app.utils.url_validator.validate_external_url", fake_validate)


class TestCurlFetchHtmlSameSiteSSRF:
    @pytest.mark.asyncio
    async def test_redirect_to_link_local_metadata_ip_blocked(self, monkeypatch):
        """(a) A same-site bolo.bh PDP that 302-redirects to the cloud-metadata
        link-local IP 169.254.169.254 → None (no SSRF, no fetch of the metadata
        endpoint)."""
        from app.services.price_service import curl_fetch_html_same_site
        _stub_validator_blocking_link_local(monkeypatch)
        start = "https://www.bolo.bh/products/x-evil"
        chain = {
            start: _FakeCurlResp(
                302, headers={"Location": "http://169.254.169.254/latest/meta-data/"},
            ),
            "http://169.254.169.254/latest/meta-data/": _FakeCurlResp(
                200, text="SECRET-CREDS",
            ),
        }
        calls = _install_curl_redirect_chain(monkeypatch, chain)
        res = await curl_fetch_html_same_site(start, "bolo.bh")
        assert res is None
        # The metadata endpoint was NEVER fetched (only the initial same-site url).
        assert "http://169.254.169.254/latest/meta-data/" not in calls

    @pytest.mark.asyncio
    async def test_redirect_to_off_host_blocked(self, monkeypatch):
        """(b) A same-site PDP that 302-redirects to an off-host (evil.example.com)
        → None, even though that host is a perfectly public, resolvable IP."""
        from app.services.price_service import curl_fetch_html_same_site
        _stub_validator_blocking_link_local(monkeypatch)
        start = "https://www.bolo.bh/products/x-offhost"
        chain = {
            start: _FakeCurlResp(
                301, headers={"Location": "https://evil.example.com/steal"},
            ),
            "https://evil.example.com/steal": _FakeCurlResp(200, text="EXFIL"),
        }
        calls = _install_curl_redirect_chain(monkeypatch, chain)
        res = await curl_fetch_html_same_site(start, "bolo.bh")
        assert res is None
        assert "https://evil.example.com/steal" not in calls

    @pytest.mark.asyncio
    async def test_same_site_to_same_site_redirect_followed(self, monkeypatch):
        """(c) A same-site bolo.bh → same-site bolo.bh 302 IS followed to the final
        200 body (the fix must not break legitimate same-host canonical redirects,
        e.g. www→apex or trailing-slash)."""
        from app.services.price_service import curl_fetch_html_same_site
        _stub_validator_blocking_link_local(monkeypatch)
        start = "https://www.bolo.bh/products/x"
        final = "https://www.bolo.bh/products/x/"
        chain = {
            start: _FakeCurlResp(302, headers={"Location": final}),
            final: _FakeCurlResp(200, text="<html>GENUINE-PDP-BODY</html>"),
        }
        calls = _install_curl_redirect_chain(monkeypatch, chain)
        res = await curl_fetch_html_same_site(start, "bolo.bh")
        assert res == "<html>GENUINE-PDP-BODY</html>"
        assert final in calls

    @pytest.mark.asyncio
    async def test_initial_off_domain_url_blocked_before_fetch(self, monkeypatch):
        """An initial url already off the source domain is rejected BEFORE any
        network call (the _host_on_domain initial gate)."""
        from app.services.price_service import curl_fetch_html_same_site
        _stub_validator_blocking_link_local(monkeypatch)
        calls = _install_curl_redirect_chain(monkeypatch, {})
        res = await curl_fetch_html_same_site(
            "https://attacker.example.com/x", "bolo.bh",
        )
        assert res is None
        assert calls == []  # never even called curl

    @pytest.mark.asyncio
    async def test_relative_location_resolved_against_current(self, monkeypatch):
        """A relative Location (`/products/x/`) resolves against the current url and
        stays same-site → followed to the 200 body."""
        from app.services.price_service import curl_fetch_html_same_site
        _stub_validator_blocking_link_local(monkeypatch)
        start = "https://www.bolo.bh/products/x"
        final = "https://www.bolo.bh/products/x-final/"
        chain = {
            start: _FakeCurlResp(302, headers={"Location": "/products/x-final/"}),
            final: _FakeCurlResp(200, text="REL-OK"),
        }
        _install_curl_redirect_chain(monkeypatch, chain)
        res = await curl_fetch_html_same_site(start, "bolo.bh")
        assert res == "REL-OK"
