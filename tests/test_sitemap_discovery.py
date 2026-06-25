"""Wave 2 (BH Source-Intelligence) — sitemap DISCOVERY channel.

The bolo/boutiqaat storefronts have NO clean public JSON search API (Finders 2+3
probed: bolo /api/v1/* -> 500, boutiqaat searchplus/rest -> 404). Their OWN
products-sitemap IS the name->PDP-URL resolver: an OFF-CLOCK job
(scripts/cron_index_sitemaps.py, flag-gated) fetches the sitemap-index -> child
sitemaps -> extracts <loc> PDP URLs -> builds a {normalized_slug -> pdp_url} map ->
BUCKETS it into a token-bucket inverted index in Redis (Codex HIGH-2): each slug
token -> discovery:sitemap:{domain}:t:{token} (≤4000 entries each) + a
discovery:sitemap:{domain}:meta key (24h TTL). The 15s request clock NEVER fetches
a sitemap (bolo = 16 children ~336k URLs / ~20MB) AND never reads the full catalog
— it reads META + up to 3 small per-token buckets and runs the matcher on each.

This suite drives:
  - the builder against recorded fixtures (NO live network — the fetcher is
    injected),
  - the pure matcher (_match_sitemap_slug) reusing the price_service title
    helpers (normalize_words / numbers_match / variant_mismatch),
  - the bounded-index contract (resolve reads small buckets, NOT the old
    whole-catalog key — Codex HIGH-2 45MB/2.4s path is gone),
  - the index-CACHE contract (a second resolve does ZERO HTTP — call-counter),
  - graceful behaviour on a cold/missing index (None, no raise, no crawl),
  - the negative-cache exemption (an adapter no-match is NOT 30d-negcached, so a
    later index refresh can upgrade it — exempt like converted_usd / SF-1).
"""

import asyncio
from pathlib import Path

import pytest

import app.services.sitemap_discovery_service as sd
from app.services.price_service import should_negative_cache

FIX = Path(__file__).parent / "fixtures"
INDEX_XML = (FIX / "bolo_sitemap_index.xml").read_text(encoding="utf-8")
PRODUCTS1_XML = (FIX / "bolo_sitemap_products1.xml").read_text(encoding="utf-8")

# The real bolo CeraVe Vitamin C Serum PDP (recon 2026-06-23).
CERAVE_PDP = (
    "https://www.bolo.bh/products/UO07CAPPYQ2-cerave-vitamin-c-serum-with-"
    "hyaluronic-acid-skin-brightening-serum-for-face-with-10-pure-vitamin-c-"
    "fragrance-free-1-fl-oz"
)

_BUCKET_PREFIX = "discovery:sitemap:bolo.bh:t:"
_META_KEY = "discovery:sitemap:bolo.bh:meta"
# The OLD whole-catalog key (Codex HIGH-2: it must no longer exist/be read).
_OLD_WHOLE_CATALOG_KEY = "discovery:sitemap:bolo.bh"


def _reconstruct_index(store: dict, prefix: str = _BUCKET_PREFIX) -> dict:
    """Rebuild the union {slug -> url} map from every token bucket in the in-memory
    Redis store — the token-bucket layout's stand-in for the old single dict."""
    index: dict = {}
    for key, bucket in store.items():
        if not key.startswith(prefix) or not isinstance(bucket, list):
            continue
        for entry in bucket:
            try:
                slug, url = entry[0], entry[1]
            except (TypeError, IndexError, ValueError):
                continue
            index[slug] = url
    return index


# ---------------------------------------------------------------------------
# Fake fetcher: maps a sitemap URL -> recorded XML. A call-counter proves the
# index is built once (off-clock) and the request path never re-fetches.
# ---------------------------------------------------------------------------
class _FakeFetcher:
    def __init__(self):
        self.calls = []
        self._map = {
            "https://www.bolo.bh/products-sitemap.xml": INDEX_XML,
            "https://www.bolo.bh/products-sitemap1.xml": PRODUCTS1_XML,
            # sitemap2 intentionally absent -> builder must tolerate a missing child
            "https://www.bolo.bh/products-sitemap2.xml": None,
        }

    async def __call__(self, url: str):
        self.calls.append(url)
        return self._map.get(url)


@pytest.fixture
def memory_redis(monkeypatch):
    """In-memory get_cached/set_cached so the index lands in a dict, not Redis."""
    store = {}
    monkeypatch.setattr(sd, "get_cached", lambda k: store.get(k))
    monkeypatch.setattr(
        sd, "set_cached", lambda k, v, ttl=0: store.__setitem__(k, v) or True
    )
    return store


# ===========================================================================
# Builder — produces {normalized_slug -> pdp_url}
# ===========================================================================
class TestBuilder:
    @pytest.mark.asyncio
    async def test_known_slug_maps_to_its_pdp_url(self, memory_redis):
        fetch = _FakeFetcher()
        count = await sd.build_sitemap_index(
            "bolo.bh",
            index_url="https://www.bolo.bh/products-sitemap.xml",
            fetch=fetch,
        )
        assert count > 0
        index = _reconstruct_index(memory_redis)
        assert isinstance(index, dict) and index
        # The CeraVe Vitamin C Serum slug resolves to its real /products/{id}-{slug} URL.
        assert CERAVE_PDP in index.values()
        # And it resolves via the bounded request path.
        assert sd.resolve_pdp_via_sitemap("bolo.bh", "CeraVe Vitamin C Serum") == CERAVE_PDP

    @pytest.mark.asyncio
    async def test_listing_and_collection_urls_are_excluded(self, memory_redis):
        """Only /products/ PDPs are indexed — a /collections/ listing is dropped."""
        await sd.build_sitemap_index(
            "bolo.bh",
            index_url="https://www.bolo.bh/products-sitemap.xml",
            fetch=_FakeFetcher(),
        )
        index = _reconstruct_index(memory_redis)
        assert all("/products/" in url for url in index.values())
        assert not any("/collections/" in url for url in index.values())

    @pytest.mark.asyncio
    async def test_missing_child_sitemap_is_tolerated(self, memory_redis):
        """sitemap2 fetch returns None -> builder still indexes sitemap1, no raise."""
        count = await sd.build_sitemap_index(
            "bolo.bh",
            index_url="https://www.bolo.bh/products-sitemap.xml",
            fetch=_FakeFetcher(),
        )
        assert count > 0  # sitemap1's PDPs are present despite sitemap2 missing

    @pytest.mark.asyncio
    async def test_all_bucket_writes_fail_reports_zero_not_phantom(self, monkeypatch):
        """MED-4 (review NIT): if EVERY bucket write fails but the META write would
        succeed, build_sitemap_index must report an HONEST 0 — the index has no
        request-path-readable bucket, so a pdp_count>0 'success' would be a phantom."""
        store = {}

        def _set(k, v, ttl=0):
            # bucket writes fail; only the meta write 'succeeds'.
            if ":t:" in k:
                return False
            store[k] = v
            return True

        monkeypatch.setattr(sd, "get_cached", lambda k: store.get(k))
        monkeypatch.setattr(sd, "set_cached", _set)
        count = await sd.build_sitemap_index(
            "bolo.bh",
            index_url="https://www.bolo.bh/products-sitemap.xml",
            fetch=_FakeFetcher(),
        )
        assert count == 0  # no phantom success
        assert _META_KEY not in store  # meta not written when the index is unusable


# ===========================================================================
# Matcher — pure, reuses the price_service title helpers
# ===========================================================================
class TestMatcher:
    @pytest.fixture
    def index(self, memory_redis):
        async def _build():
            await sd.build_sitemap_index(
                "bolo.bh",
                index_url="https://www.bolo.bh/products-sitemap.xml",
                fetch=_FakeFetcher(),
            )
        asyncio.run(_build())
        # The pure matcher takes a {slug: url} dict — reconstruct the union of all
        # token buckets (a small fixture set) to exercise it directly.
        return _reconstruct_index(memory_redis)

    def test_matcher_hits_a_product_name(self, index):
        url = sd._match_sitemap_slug(index, "CeraVe Vitamin C Serum")
        assert url == CERAVE_PDP

    def test_matcher_misses_an_absent_product(self, index):
        url = sd._match_sitemap_slug(index, "Dyson Airwrap Complete")
        assert url is None

    def test_variant_guard_fires_on_size_mismatch(self, index):
        """A 50ml query must NOT bind a 30ml slug (variant_mismatch guard).

        The index holds The Ordinary Vitamin C at both 50ml and 30ml. Asking for
        the 50ml must resolve to the 50ml PDP, never the 30ml one.
        """
        url = sd._match_sitemap_slug(index, "The Ordinary Vitamin C Suspension 50ml")
        assert url is not None
        assert "50ml" in url
        assert "30ml" not in url

    def test_empty_index_returns_none(self):
        assert sd._match_sitemap_slug({}, "CeraVe Vitamin C Serum") is None
        assert sd._match_sitemap_slug(None, "CeraVe Vitamin C Serum") is None


# ===========================================================================
# resolve_pdp_via_sitemap — request-path READ only (NO fetch on the clock)
# ===========================================================================
class TestResolveRequestPath:
    @pytest.mark.asyncio
    async def test_index_fetched_once_then_cache_only(self, memory_redis):
        """Build once (off-clock), then a request-time resolve does ZERO HTTP."""
        fetch = _FakeFetcher()
        await sd.build_sitemap_index(
            "bolo.bh",
            index_url="https://www.bolo.bh/products-sitemap.xml",
            fetch=fetch,
        )
        calls_after_build = len(fetch.calls)
        assert calls_after_build > 0  # the off-clock build DID fetch

        # Request-path resolve: must hit the Redis index, never the fetcher.
        url = sd.resolve_pdp_via_sitemap("bolo.bh", "CeraVe Vitamin C Serum")
        assert url == CERAVE_PDP
        # A second resolve: still ZERO additional HTTP.
        url2 = sd.resolve_pdp_via_sitemap("bolo.bh", "CeraVe Vitamin C Serum")
        assert url2 == CERAVE_PDP
        assert len(fetch.calls) == calls_after_build  # NO new fetches on the clock

    def test_cold_missing_index_returns_none_no_crawl(self, memory_redis):
        """No index built yet -> resolver returns None gracefully (no raise, no
        crawl). The cascade continues -> honest pending, NOT a fabricated price."""
        # memory_redis store is empty -> no discovery:sitemap:* key.
        assert sd.resolve_pdp_via_sitemap("bolo.bh", "CeraVe Vitamin C Serum") is None

    def test_resolver_no_match_returns_none(self, memory_redis):
        async def _build():
            await sd.build_sitemap_index(
                "bolo.bh",
                index_url="https://www.bolo.bh/products-sitemap.xml",
                fetch=_FakeFetcher(),
            )
        asyncio.run(_build())
        assert sd.resolve_pdp_via_sitemap("bolo.bh", "Nonexistent Widget 9000") is None

    @pytest.mark.asyncio
    async def test_resolve_does_not_fetch_full_catalog(self, memory_redis):
        """Codex HIGH-2 — resolve must read META + small per-token buckets, NEVER a
        single whole-catalog dict (the old 45MB/2.4s scan). Build a small index,
        then assert (a) the OLD whole-catalog key is absent/unused, and (b) every
        key resolve reads is the META key or a small (≤ _BUCKET_CAP) token bucket."""
        await sd.build_sitemap_index(
            "bolo.bh",
            index_url="https://www.bolo.bh/products-sitemap.xml",
            fetch=_FakeFetcher(),
        )
        # (a) The old whole-catalog key was never written.
        assert sd.get_cached(_OLD_WHOLE_CATALOG_KEY) is None

        # (b) Record every key the request path reads via get_cached.
        reads = []
        real_get = sd.get_cached
        sd.get_cached = lambda k: reads.append(k) or real_get(k)  # type: ignore[assignment]
        try:
            url = sd.resolve_pdp_via_sitemap("bolo.bh", "CeraVe Vitamin C Serum")
        finally:
            sd.get_cached = real_get  # type: ignore[assignment]

        assert url == CERAVE_PDP
        # Never reads the old whole-catalog key.
        assert _OLD_WHOLE_CATALOG_KEY not in reads
        # Every read is the META key or a bounded token bucket.
        for k in reads:
            assert k == _META_KEY or k.startswith(_BUCKET_PREFIX), k
        # Buckets are bounded.
        for key, bucket in memory_redis.items():
            if key.startswith(_BUCKET_PREFIX):
                assert len(bucket) <= sd._BUCKET_CAP

    @pytest.mark.asyncio
    async def test_index_is_built_reflects_meta_presence(self, memory_redis):
        """_index_is_built is False before a build, True after (consumed by a
        downstream wave's cold-detection)."""
        assert sd._index_is_built("bolo.bh") is False
        await sd.build_sitemap_index(
            "bolo.bh",
            index_url="https://www.bolo.bh/products-sitemap.xml",
            fetch=_FakeFetcher(),
        )
        assert sd._index_is_built("bolo.bh") is True


# ===========================================================================
# SSRF guard — every <loc>/child URL is bound to the source's own domain
# ===========================================================================
class TestSsrfGuard:
    """Source-intel review 2026-06-23 (MUST-FIX) — build_sitemap_index must bind
    every <loc>/child-sitemap URL to the source's OWN registrable domain. A
    poisoned/MITM'd sitemap <loc> to a private IP / *.railway.internal / a cloud
    metadata host must NEVER be indexed (it would later be curl-fetched on the
    request path — curl_fetch_html has no host allowlist + follows redirects)."""

    _NS = 'xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"'

    def test_same_site_unit(self):
        ok = ("https://www.bolo.bh/products/x", "https://bolo.bh/products/x",
              "https://cdn.bolo.bh/products/x")
        bad = ("https://notbolo.bh/products/x", "https://bolo.bh.evil.com/products/x",
               "http://169.254.169.254/products/x", "http://10.0.0.5/products/x",
               "http://metadata.railway.internal/products/x", "https://evil.example.com/products/x")
        for u in ok:
            assert sd._same_site(u, "bolo.bh") is True, u
        for u in bad:
            assert sd._same_site(u, "bolo.bh") is False, u
        # No expected host → reject (fail-closed).
        assert sd._same_site("https://www.bolo.bh/products/x", "") is False

    @pytest.mark.asyncio
    async def test_offdomain_pdp_loc_is_dropped(self, memory_redis):
        """A same-site flat urlset carrying one genuine bolo PDP and one off-domain
        PDP loc indexes ONLY the bolo PDP — the evil loc never lands in Redis."""
        good = "https://www.bolo.bh/products/UO1-cerave-vitamin-c-serum"
        evil = "http://169.254.169.254/products/UO2-cerave-vitamin-c-serum"
        urlset = (
            f'<urlset {self._NS}>'
            f'<url><loc>{good}</loc></url>'
            f'<url><loc>{evil}</loc></url>'
            '</urlset>'
        )

        async def fetch(url):
            return urlset  # index_url is itself a flat product urlset

        count = await sd.build_sitemap_index(
            "bolo.bh", index_url="https://www.bolo.bh/products-sitemap.xml", fetch=fetch,
        )
        index = _reconstruct_index(memory_redis)
        assert count == 1
        assert good in index.values()
        # The evil loc never lands in ANY token bucket.
        assert not any("169.254.169.254" in u for u in index.values())
        assert not any(
            "169.254.169.254" in str(bucket)
            for key, bucket in memory_redis.items()
            if key.startswith(_BUCKET_PREFIX)
        )

    @pytest.mark.asyncio
    async def test_offdomain_child_sitemap_is_never_fetched(self, memory_redis):
        """An index pointing to a same-site child AND an off-domain child must
        fetch ONLY the same-site child (no SSRF crawl to the evil host)."""
        same_child = "https://www.bolo.bh/products-sitemap1.xml"
        evil_child = "http://metadata.railway.internal/products-sitemap1.xml"
        index_xml = (
            f'<sitemapindex {self._NS}>'
            f'<sitemap><loc>{same_child}</loc></sitemap>'
            f'<sitemap><loc>{evil_child}</loc></sitemap>'
            '</sitemapindex>'
        )
        pdp = "https://www.bolo.bh/products/UO9-cerave-vitamin-c-serum"
        child_xml = f'<urlset {self._NS}><url><loc>{pdp}</loc></url></urlset>'
        calls = []

        async def fetch(url):
            calls.append(url)
            if url == "https://www.bolo.bh/products-sitemap.xml":
                return index_xml
            if url == same_child:
                return child_xml
            return None  # the evil child must never be requested

        count = await sd.build_sitemap_index(
            "bolo.bh", index_url="https://www.bolo.bh/products-sitemap.xml", fetch=fetch,
        )
        assert count == 1
        assert evil_child not in calls  # NO SSRF crawl
        assert same_child in calls


# ===========================================================================
# Multiple index URLs per domain (Codex MED-1) — boutiqaat splits its catalog
# across separate women + men section sitemaps; build_sitemap_index must accept
# a LIST of index_urls, fetch+validate EACH independently, and UNION the PDPs.
# ===========================================================================
class TestMultipleIndexUrls:
    _NS = 'xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"'

    @pytest.mark.asyncio
    async def test_list_of_two_index_urls_unions_pdps_from_both(self, memory_redis):
        """A LIST of two index_urls → the reconstructed union index contains PDPs
        from BOTH. Reuse the bolo fixtures for one index; a tiny inline second
        urlset (a distinct PDP) for the other."""
        women_index = "https://www.bolo.bh/products-sitemap.xml"
        men_index = "https://www.bolo.bh/men-sitemap.xml"
        # The second index is itself a flat urlset carrying one DISTINCT PDP not in
        # the bolo fixtures (a men's grooming product).
        men_pdp = (
            "https://www.bolo.bh/products/UO0MEN1234-mens-beard-oil-grooming-kit"
        )
        men_urlset = (
            f'<urlset {self._NS}>'
            f'<url><loc>{men_pdp}</loc></url>'
            '</urlset>'
        )

        class _TwoIndexFetcher:
            def __init__(self):
                self.calls = []
                self._map = {
                    women_index: INDEX_XML,
                    "https://www.bolo.bh/products-sitemap1.xml": PRODUCTS1_XML,
                    "https://www.bolo.bh/products-sitemap2.xml": None,
                    men_index: men_urlset,
                }

            async def __call__(self, url):
                self.calls.append(url)
                return self._map.get(url)

        fetch = _TwoIndexFetcher()
        count = await sd.build_sitemap_index(
            "bolo.bh", index_url=[women_index, men_index], fetch=fetch,
        )
        # UNION count = the bolo-fixture PDPs (women) + the one distinct men PDP.
        assert count > 1
        index = _reconstruct_index(memory_redis)
        # PDP from the FIRST index (women — bolo fixtures).
        assert CERAVE_PDP in index.values()
        # PDP from the SECOND index (men — the distinct inline urlset).
        assert men_pdp in index.values()
        # Both indexes were fetched off-clock.
        assert women_index in fetch.calls
        assert men_index in fetch.calls
        # Both resolve via the bounded request path.
        assert sd.resolve_pdp_via_sitemap("bolo.bh", "CeraVe Vitamin C Serum") == CERAVE_PDP
        assert sd.resolve_pdp_via_sitemap("bolo.bh", "mens beard oil grooming kit") == men_pdp

    @pytest.mark.asyncio
    async def test_single_str_index_url_behaves_exactly_as_before(self, memory_redis):
        """A str index_url keeps the exact current behavior (parity guard)."""
        count = await sd.build_sitemap_index(
            "bolo.bh",
            index_url="https://www.bolo.bh/products-sitemap.xml",
            fetch=_FakeFetcher(),
        )
        assert count > 0
        index = _reconstruct_index(memory_redis)
        assert CERAVE_PDP in index.values()
        assert sd.resolve_pdp_via_sitemap("bolo.bh", "CeraVe Vitamin C Serum") == CERAVE_PDP

    @pytest.mark.asyncio
    async def test_list_per_index_ssrf_guard_is_independent(self, memory_redis):
        """Each index in the LIST derives its OWN expected-site + SSRF guard. A
        second index whose host differs from the first must NOT smuggle an
        off-(its-own)-domain PDP through. Here the men index is a flat urlset
        carrying one genuine bolo PDP and one off-domain (metadata) loc — only the
        genuine bolo PDP lands."""
        women_index = "https://www.bolo.bh/products-sitemap.xml"
        men_index = "https://www.bolo.bh/men-sitemap.xml"
        good = "https://www.bolo.bh/products/UO0MEN1-mens-beard-oil"
        evil = "http://169.254.169.254/products/UO0MEN2-mens-beard-oil"
        men_urlset = (
            f'<urlset {self._NS}>'
            f'<url><loc>{good}</loc></url>'
            f'<url><loc>{evil}</loc></url>'
            '</urlset>'
        )

        async def fetch(url):
            if url == women_index:
                return INDEX_XML
            if url == "https://www.bolo.bh/products-sitemap1.xml":
                return PRODUCTS1_XML
            if url == men_index:
                return men_urlset
            return None

        await sd.build_sitemap_index(
            "bolo.bh", index_url=[women_index, men_index], fetch=fetch,
        )
        index = _reconstruct_index(memory_redis)
        assert good in index.values()
        assert not any("169.254.169.254" in u for u in index.values())


class TestNegativeCacheExemption:
    def test_sitemap_no_match_is_not_negative_cached(self):
        """A sitemap-discovery miss (no index yet / no PDP found) must be treated
        like converted_usd: NOT 30d-negcached, so a later index refresh can
        upgrade it (SF-1 exemption, price_service.should_negative_cache)."""
        # The honest shape the adapter returns on a discovery miss.
        no_match = sd.sitemap_no_match_price()
        assert should_negative_cache(no_match) is False

    def test_genuine_sitemap_price_is_not_a_dead_end(self):
        """A genuine page_scrape_jsonld price from a sitemap-discovered PDP is NOT
        a dead-end (it IS genuine)."""
        genuine = {"amount": 12.5, "currency": "BHD",
                   "source_method": "page_scrape_jsonld"}
        assert should_negative_cache(genuine) is False


# ===========================================================================
# SSRF-via-redirect regression (Codex HIGH-5, sitemap-CRAWL half)
# ---------------------------------------------------------------------------
# The off-clock builder fetches the sitemap-INDEX + child sitemaps via
# sd._default_fetch. The OLD impl called the generic curl_fetch_html, which
# follows redirects (allow_redirects=True) with NO per-hop host validation — a
# poisoned/MITM'd sitemap-index that 30x-redirects to a private/link-local IP or
# an off-host would be CRAWLED by the cron (SSRF). The fix routes _default_fetch
# through curl_fetch_html_same_site bound to the URL's OWN registrable domain,
# which disables auto-redirect and validates every hop.
# We mock at the curl_cffi.requests.get layer (a fake response with
# status_code/headers/text) — NO live network, NO DNS — exactly like the bolo
# SSRF regression suite.
# ===========================================================================

class _FakeCurlResp:
    def __init__(self, status_code, headers=None, text=""):
        self.status_code = status_code
        self.headers = headers or {}
        self.text = text


def _install_curl_redirect_chain(monkeypatch, chain, max_hops=10):
    """Mock curl_cffi.requests.get with a {url: _FakeCurlResp} map and capture the
    fetch order.

    Codex re-review #2 H5 (test-discrimination) — this mock HONORS the
    ``allow_redirects`` kwarg the way real curl_cffi does, so the SSRF-blocking
    tests genuinely FAIL-WITHOUT-FIX:
      * ``allow_redirects=False`` (the same-site fetcher ``curl_fetch_html_same_site``):
        return the single response for ``url`` WITHOUT following — the fetcher
        validates every hop itself and re-invokes us once per validated hop.
      * ``allow_redirects=True`` (the OLD vulnerable ``curl_fetch_html``):
        transparently FOLLOW the ``Location`` chain — fetching (and recording in
        ``calls``) each hop, including an off-host/private one — and return the
        TERMINAL response. So reverting ``_default_fetch`` to the
        redirect-following fetcher both RETURNS the evil body (``res is None``
        fails) AND crawls the evil host (``evil not in calls`` fails).

    The OLD mock asserted ``allow_redirects is False``, but that AssertionError is
    swallowed by ``curl_fetch_html``'s broad ``except Exception → return None``, so
    a revert still produced ``res is None`` and the blocking tests passed against
    vulnerable code. Honoring the kwarg is the outcome-based discriminator.
    Unknown urls 404."""
    calls = []

    def fake_get(url, **kwargs):
        calls.append(url)
        resp = chain.get(url, _FakeCurlResp(404))
        if kwargs.get("allow_redirects"):
            hops = 0
            while 300 <= resp.status_code < 400 and hops < max_hops:
                location = (
                    resp.headers.get("Location") or resp.headers.get("location")
                )
                if not location:
                    break
                calls.append(location)  # the followed hop IS crawled (network hit)
                resp = chain.get(location, _FakeCurlResp(404))
                hops += 1
        return resp

    import curl_cffi.requests as curl_requests
    monkeypatch.setattr(curl_requests, "get", fake_get)
    return calls


def _stub_validator_blocking_link_local(monkeypatch):
    """DNS-free validate_external_url stub: reject non-http(s) and
    link-local/private/loopback/reserved LITERAL-IP hosts; accept public
    hostnames (no socket call). Keeps the test fully offline while still proving
    the per-hop gate."""
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
            return True  # a hostname (not a literal IP) → public here
        return not (
            ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
        )

    monkeypatch.setattr(
        "app.utils.url_validator.validate_external_url", fake_validate
    )


class TestDefaultFetchSSRF:
    @pytest.mark.asyncio
    async def test_sitemap_redirect_to_link_local_metadata_ip_blocked(self, monkeypatch):
        """A same-site bolo.bh sitemap-index that 30x-redirects to the cloud-
        metadata link-local IP (169.254.169.254) → _default_fetch returns None and
        NEVER fetches the metadata endpoint (no SSRF crawl)."""
        _stub_validator_blocking_link_local(monkeypatch)
        start = "https://www.bolo.bh/products-sitemap.xml"
        evil = "http://169.254.169.254/latest/meta-data/"
        chain = {
            start: _FakeCurlResp(302, headers={"Location": evil}),
            evil: _FakeCurlResp(200, text="SECRET-CREDS"),
        }
        calls = _install_curl_redirect_chain(monkeypatch, chain)
        res = await sd._default_fetch(start)
        assert res is None
        assert evil not in calls  # metadata endpoint NEVER crawled

    @pytest.mark.asyncio
    async def test_sitemap_redirect_to_off_host_blocked(self, monkeypatch):
        """A same-site bolo.bh sitemap that 301-redirects to an off-host (a public,
        resolvable but DIFFERENT domain) → None, and the off-host is never crawled.
        Without the fix (generic curl_fetch_html, allow_redirects=True) the body
        WOULD have been returned + crawled for <loc>s."""
        _stub_validator_blocking_link_local(monkeypatch)
        start = "https://www.bolo.bh/sitemap_index.xml"
        evil = "https://evil.example.com/sitemap.xml"
        chain = {
            start: _FakeCurlResp(301, headers={"Location": evil}),
            evil: _FakeCurlResp(200, text="<urlset>EXFIL</urlset>"),
        }
        calls = _install_curl_redirect_chain(monkeypatch, chain)
        res = await sd._default_fetch(start)
        assert res is None
        assert evil not in calls

    @pytest.mark.asyncio
    async def test_sitemap_same_site_200_returns_body(self, monkeypatch):
        """A same-site 200 → _default_fetch returns the body (the fix must not break
        a legitimate same-host sitemap fetch — the cron's normal path)."""
        _stub_validator_blocking_link_local(monkeypatch)
        start = "https://www.bolo.bh/products-sitemap.xml"
        body = "<sitemapindex>GENUINE-INDEX</sitemapindex>"
        chain = {start: _FakeCurlResp(200, text=body)}
        calls = _install_curl_redirect_chain(monkeypatch, chain)
        res = await sd._default_fetch(start)
        assert res == body
        assert start in calls

    @pytest.mark.asyncio
    async def test_sitemap_same_site_redirect_followed(self, monkeypatch):
        """A same-site → same-site sitemap redirect (e.g. www→apex or .xml→.xml.gz
        canonical) IS followed to the final 200 body — same-host canonical redirects
        must still work."""
        _stub_validator_blocking_link_local(monkeypatch)
        start = "https://www.bolo.bh/products-sitemap.xml"
        final = "https://www.bolo.bh/products-sitemap-1.xml"
        chain = {
            start: _FakeCurlResp(302, headers={"Location": final}),
            final: _FakeCurlResp(200, text="<urlset>FINAL</urlset>"),
        }
        calls = _install_curl_redirect_chain(monkeypatch, chain)
        res = await sd._default_fetch(start)
        assert res == "<urlset>FINAL</urlset>"
        assert final in calls
