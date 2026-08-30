"""UNIT B5 — abdulsamadalqurashi cross-country Salla slug resolution
(ENABLE_SALLA_SLUG_RESOLVE, default OFF).

MEASURED (B4): ``ae.abdulsamadalqurashi.com`` parses cleanly (227.81 AED via the
Salla @graph JSON-LD) but the kw/om/qa hosts FAILED only because the AE product
slug does not exist there and the request REDIRECTS to the storefront HOMEPAGE
(proof: the PDP byte counts were identical to the homepage rows). That is a
RESOLUTION problem, not a wall.

FIX: when a Salla PDP slug collapses to the storefront homepage (HTML present, a
Salla store, no Product structured data), resolve the product via the Salla
storefront SEARCH API for that store-id + product name — REUSING the existing
``fetch_salla_api_price`` client (store-id + keyword search) — then price the
resolved PDP. No second Salla client.

Offline — NO network. The Salla search is mocked two ways:
  * the delegation/flag/collapse-detection pins patch ``fetch_salla_api_price``
    itself (proving the resolver reuses that one client and gates correctly);
  * one end-to-end pin patches ``curl_cffi.requests.get`` (the same seam the
    existing salla adapter test uses) so the REAL ``fetch_salla_api_price`` runs:
    store-id seeded from the homepage bytes -> one search GET -> the right
    product priced.

Pins:
  (a) homepage-collapse detection: the KW homepage IS a collapse; the AE PDP is
      NOT; a non-salla / empty page is NOT;
  (b) flag-OFF: the resolver returns None and NEVER calls the Salla search
      (byte-identical dead-slug behaviour);
  (c) flag-ON + collapse: the resolver delegates to fetch_salla_api_price and
      returns its resolved price; the seeded store-id comes from the homepage;
  (d) flag-ON + a real PDP (AE): NOT a collapse -> no search (AE unchanged);
  (e) flag-ON end-to-end: the real client resolves the KW product via a single
      mocked search GET -> converted BHD (converted_usd);
  (f) fetch_page_price wiring: a Salla homepage-collapse recovers via the
      resolver with the flag ON, is the plain ``{"_got_html": True}`` sentinel
      with it OFF (byte-identical), and a real AE PDP never triggers the search.
"""

import asyncio
import json
import os

import pytest

import app.services.salla_service as salla
import app.services.price_service as ps

FIX = os.path.join(os.path.dirname(__file__), "fixtures", "salla_slug_b5")

QUERY = "Al Qurashi Blend Perfume 90ml"
KW_URL = "https://kw.abdulsamadalqurashi.com/en/al-qurashi-blend-perfume-90ml/p495814384"
AE_URL = "https://ae.abdulsamadalqurashi.com/en/al-qurashi-blend-perfume-90ml/p495814384"


def _read(name: str) -> str:
    with open(os.path.join(FIX, name), encoding="utf-8") as fh:
        return fh.read()


AE_PDP = _read("abdulsamadalqurashi_ae_pdp_aed.html")
KW_HOME = _read("abdulsamadalqurashi_kw_homepage_collapse.html")
NOT_SALLA = _read("not_salla_no_price.html")
SEARCH_KW = json.loads(_read("salla_api_search_kw.json"))


def _run(coro):
    return asyncio.run(coro)


class _FakeResp:
    def __init__(self, status_code=200, text="", json_obj=None):
        self.status_code = status_code
        self._text = text
        self._json = json_obj

    @property
    def text(self):
        return self._text

    def json(self):
        if self._json is not None:
            return self._json
        return json.loads(self._text)


@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    # The underlying salla client is gated by ENABLE_PAGE_SCRAPE — force it on.
    monkeypatch.setattr(salla, "ENABLE_PAGE_SCRAPE", True, raising=False)
    monkeypatch.setattr(ps, "ENABLE_PAGE_SCRAPE", True, raising=False)
    salla._STORE_ID_CACHE.clear()
    # Default: flag OFF (each test opts in).
    monkeypatch.delenv("ENABLE_SALLA_SLUG_RESOLVE", raising=False)


def _spy_search(monkeypatch, ret):
    """Patch the ONE reused Salla client and record its calls."""
    calls = []

    async def fake(domain, product_name, currency="BHD", resolved_category=None):
        calls.append((domain, product_name, currency, resolved_category))
        return ret

    monkeypatch.setattr(salla, "fetch_salla_api_price", fake)
    return calls


# ---------------------------------------------------------------------------
# (a) homepage-collapse detection
# ---------------------------------------------------------------------------

def test_kw_homepage_is_a_collapse():
    assert salla._is_salla_homepage_collapse(KW_HOME, KW_URL) is True


def test_ae_pdp_is_not_a_collapse():
    assert salla._is_salla_homepage_collapse(AE_PDP, AE_URL) is False


def test_non_salla_and_empty_are_not_collapses():
    assert salla._is_salla_homepage_collapse(NOT_SALLA, "https://x.example/p/1") is False
    assert salla._is_salla_homepage_collapse("", KW_URL) is False
    assert salla._is_salla_homepage_collapse(None, KW_URL) is False


# ---------------------------------------------------------------------------
# (b) flag-OFF — never resolves, never searches
# ---------------------------------------------------------------------------

def test_flag_off_no_resolution_no_search(monkeypatch):
    calls = _spy_search(monkeypatch, {"amount": 1.0, "currency": "BHD"})
    res = _run(salla.fetch_salla_slug_resolved_price(KW_URL, QUERY, "BHD", html=KW_HOME))
    assert res is None
    assert calls == []


def test_enabled_helper_reads_env_per_call(monkeypatch):
    monkeypatch.delenv("ENABLE_SALLA_SLUG_RESOLVE", raising=False)
    assert salla.salla_slug_resolve_enabled() is False
    monkeypatch.setenv("ENABLE_SALLA_SLUG_RESOLVE", "true")
    assert salla.salla_slug_resolve_enabled() is True


# ---------------------------------------------------------------------------
# (c) flag-ON + collapse -> delegates to the reused client; store-id seeded
# ---------------------------------------------------------------------------

def test_flag_on_collapse_delegates_to_search(monkeypatch):
    monkeypatch.setenv("ENABLE_SALLA_SLUG_RESOLVE", "true")
    sentinel = {"amount": 30.75, "currency": "BHD", "source_method": "converted_usd"}
    calls = _spy_search(monkeypatch, sentinel)
    res = _run(salla.fetch_salla_slug_resolved_price(KW_URL, QUERY, "BHD", html=KW_HOME))
    assert res is sentinel
    assert len(calls) == 1
    domain, name, currency, _cat = calls[0]
    assert domain == "kw.abdulsamadalqurashi.com"
    assert name == QUERY
    assert currency == "BHD"
    # store-id came from the homepage bytes we already held (no extra fetch).
    assert salla._STORE_ID_CACHE.get("kw.abdulsamadalqurashi.com") == "1246890663"


# ---------------------------------------------------------------------------
# (d) flag-ON + a real PDP (AE) -> NOT a collapse -> no search (AE unchanged)
# ---------------------------------------------------------------------------

def test_flag_on_real_pdp_never_searches(monkeypatch):
    monkeypatch.setenv("ENABLE_SALLA_SLUG_RESOLVE", "true")
    calls = _spy_search(monkeypatch, {"amount": 1.0, "currency": "BHD"})
    res = _run(salla.fetch_salla_slug_resolved_price(AE_URL, QUERY, "BHD", html=AE_PDP))
    assert res is None
    assert calls == []


# ---------------------------------------------------------------------------
# (e) flag-ON end-to-end — the REAL client resolves via ONE mocked search GET
# ---------------------------------------------------------------------------

def test_flag_on_end_to_end_real_client_resolves(monkeypatch):
    monkeypatch.setenv("ENABLE_SALLA_SLUG_RESOLVE", "true")
    monkeypatch.setattr(salla, "is_price_showable", lambda *a, **k: True)

    gets = []

    def fake_get(url, *args, **kwargs):
        gets.append(url)
        if "api.salla.dev" in url:
            return _FakeResp(200, json_obj=SEARCH_KW)
        return _FakeResp(200, text=KW_HOME)  # storefront fallback (if reached)

    import curl_cffi.requests as curl_requests
    monkeypatch.setattr(curl_requests, "get", fake_get, raising=True)

    res = _run(salla.fetch_salla_slug_resolved_price(
        KW_URL, QUERY, "BHD", resolved_category="fragrances", html=KW_HOME))
    assert res is not None
    # 25 KWD -> BHD, converted branch stamps converted_usd.
    assert res["currency"] == "BHD"
    assert res["source_method"] == "converted_usd"
    assert res["original_currency"] == "KWD"
    assert res["amount"] == pytest.approx(round(25 * 1.23, 3))
    # The resolved product's own PDP url, not the dead AE slug.
    assert "p495814399" in res["url"]
    # store-id was seeded from the homepage -> only the search GET was issued.
    assert all("api.salla.dev" in u for u in gets)
    assert len(gets) == 1


# ---------------------------------------------------------------------------
# (f) fetch_page_price wiring
# ---------------------------------------------------------------------------

def test_fetch_page_price_collapse_recovers_flag_on(monkeypatch):
    monkeypatch.setenv("ENABLE_SALLA_SLUG_RESOLVE", "true")
    price = {"amount": 30.75, "currency": "BHD", "source_method": "converted_usd"}
    calls = _spy_search(monkeypatch, price)

    async def fake_fetch(url, domain):
        return KW_HOME

    monkeypatch.setattr(ps, "curl_fetch_html_same_site", fake_fetch)
    res = _run(ps.fetch_page_price(KW_URL, QUERY, "BHD"))
    assert res is price
    assert len(calls) == 1
    assert calls[0][0] == "kw.abdulsamadalqurashi.com"


def test_fetch_page_price_collapse_flag_off_is_sentinel(monkeypatch):
    monkeypatch.delenv("ENABLE_SALLA_SLUG_RESOLVE", raising=False)
    calls = _spy_search(monkeypatch, {"amount": 1.0, "currency": "BHD"})

    async def fake_fetch(url, domain):
        return KW_HOME

    monkeypatch.setattr(ps, "curl_fetch_html_same_site", fake_fetch)
    res = _run(ps.fetch_page_price(KW_URL, QUERY, "BHD"))
    assert res == {"_got_html": True}   # byte-identical dead-slug behaviour
    assert calls == []


def test_fetch_page_price_ae_pdp_never_searches_flag_on(monkeypatch):
    monkeypatch.setenv("ENABLE_SALLA_SLUG_RESOLVE", "true")
    calls = _spy_search(monkeypatch, {"amount": 1.0, "currency": "BHD"})

    async def fake_fetch(url, domain):
        return AE_PDP

    monkeypatch.setattr(ps, "curl_fetch_html_same_site", fake_fetch)
    res = _run(ps.fetch_page_price(AE_URL, QUERY, "BHD"))
    # AE PDP is a real product page: whatever the extractor returns, the Salla
    # search is NEVER consulted -> AE behaviour is unchanged.
    assert calls == []
    assert res is not None
