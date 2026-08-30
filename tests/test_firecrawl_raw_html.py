"""Firecrawl must fetch rawHtml, not Firecrawl-CLEANED html (#92, P1).

MEASURED DEFECT (bake-off 2026-08-25, `docs/investigations/2026-08-25-scraper-bakeoff.md`):
``firecrawl_service`` hardcoded ``formats: ["html"]`` — Firecrawl's *cleaned*
HTML, which by contract strips ``<script>``/``<style>``/``<meta>``/``<head>``.
Every successful fetch came back with **0 script tags and 0 ld+json blocks**,
and this repo's extractor reads ``<script type="application/ld+json">``. So the
integration could not price a page **by construction** — 0/9 on the bake-off —
while billing 1 Firecrawl credit per call. With ``formats: ["rawHtml"]`` the
same URL priced (1.400 BHD) and was 5.4x faster.

Three things are pinned here, per the assignment:
  (a) the request payload asks for ``rawHtml``, not ``html``;
  (b) the parser reads the ``rawHtml`` response key;
  (c) the rollback state (``ENABLE_FIRECRAWL_RAW_HTML=false``) still does
      exactly what ``main`` did — legacy format, legacy key, no upstream-status
      short-circuit.

Plus the fourth acceptance criterion from #92: an upstream 404 that Firecrawl
reports as its own HTTP 200 (and bills for) is not handed to the caller as a
successful scrape.

The HTTP layer is mocked throughout — these tests never call Firecrawl and
never spend a credit.
"""
import json

import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from app.services import firecrawl_service
from app.services.firecrawl_service import scrape_page, scrape_page_with_status


# ---------------------------------------------------------------------------
# Fixture pair — SYNTHETIC (not cut from a corpus), but faithful to the
# measured defect: one page, expressed the two ways Firecrawl can return it.
# `RAW_PAGE` is what `formats:["rawHtml"]` yields; `CLEANED_PAGE` is derived
# from it by the documented cleaning contract (script tags removed), which is
# what `formats:["html"]` yielded on every bake-off target. The price lives in
# the JSON-LD block, so it survives in exactly one of them.
# ---------------------------------------------------------------------------
_LD_JSON = json.dumps(
    {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": "Matalan Kids Cotton Tee",
        "brand": {"@type": "Brand", "name": "Matalan"},
        "offers": {
            "@type": "Offer",
            "price": "1.400",
            "priceCurrency": "BHD",
            "availability": "https://schema.org/InStock",
            "url": "https://www.matalanme.com/p/kids-cotton-tee",
        },
    }
)

RAW_PAGE = (
    "<html><head>"
    "<title>Matalan Kids Cotton Tee</title>"
    '<meta property="og:title" content="Matalan Kids Cotton Tee" />'
    f'<script type="application/ld+json">{_LD_JSON}</script>'
    "</head><body>"
    '<h1>Matalan Kids Cotton Tee</h1><span class="price">1.400 BHD</span>'
    + ("<p>filler copy so the response clears the 500-byte floor.</p>" * 20)
    + "</body></html>"
)

# Firecrawl's cleaned `html` format, per its own OpenAPI description: script,
# style, noscript, meta and head tags removed. The ld+json goes with them.
CLEANED_PAGE = (
    "<html><body>"
    '<h1>Matalan Kids Cotton Tee</h1><span class="price">1.400 BHD</span>'
    + ("<p>filler copy so the response clears the 500-byte floor.</p>" * 20)
    + "</body></html>"
)


def _resp(payload: dict, status_code: int = 200) -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = payload
    return mock_resp


def _client(mock_client_cls, mock_resp):
    mock_client = AsyncMock()
    mock_client.post.return_value = mock_resp
    mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
    return mock_client


def _sent_payload(mock_client) -> dict:
    call = mock_client.post.call_args
    return call.kwargs.get("json") or call[1].get("json")


@pytest.fixture
def key(monkeypatch):
    monkeypatch.setenv("FIRECRAWL_API_KEY", "test-key")
    monkeypatch.delenv("ENABLE_FIRECRAWL_RAW_HTML", raising=False)


@pytest.fixture
def rollback(monkeypatch):
    """The documented rollback state: legacy Firecrawl behaviour, byte-identical
    to `main`."""
    monkeypatch.setenv("FIRECRAWL_API_KEY", "test-key")
    monkeypatch.setenv("ENABLE_FIRECRAWL_RAW_HTML", "false")


# ===========================================================================
# (a) the request payload asks for rawHtml
# ===========================================================================
class TestRequestAsksForRawMarkup:
    @pytest.mark.asyncio
    async def test_scrape_page_requests_raw_html(self, key):
        with patch("app.services.firecrawl_service.httpx.AsyncClient") as cls:
            c = _client(cls, _resp({"success": True, "data": {"rawHtml": RAW_PAGE}}))
            await scrape_page("https://www.matalanme.com/p/kids-cotton-tee")
            payload = _sent_payload(c)
            assert payload["formats"] == ["rawHtml"], (
                "formats:['html'] is Firecrawl's CLEANED html — 0 script tags, "
                "0 ld+json, and therefore 0 prices, ever (#92)."
            )
            assert "html" not in payload["formats"]

    @pytest.mark.asyncio
    async def test_scrape_page_with_status_requests_raw_html(self, key):
        with patch("app.services.firecrawl_service.httpx.AsyncClient") as cls:
            c = _client(cls, _resp({"success": True, "data": {"rawHtml": RAW_PAGE}}))
            await scrape_page_with_status("https://www.matalanme.com/p/kids-cotton-tee")
            assert _sent_payload(c)["formats"] == ["rawHtml"]

    @pytest.mark.asyncio
    async def test_rest_of_payload_is_unchanged(self, key):
        with patch("app.services.firecrawl_service.httpx.AsyncClient") as cls:
            c = _client(cls, _resp({"success": True, "data": {"rawHtml": RAW_PAGE}}))
            await scrape_page("https://example.com/product")
            payload = _sent_payload(c)
            assert payload["url"] == "https://example.com/product"
            assert payload["waitFor"] == firecrawl_service.FIRECRAWL_WAIT_MS
            assert set(payload) == {"url", "formats", "waitFor"}


# ===========================================================================
# (b) the parser reads the rawHtml response key
# ===========================================================================
class TestParserReadsRawHtmlKey:
    @pytest.mark.asyncio
    async def test_scrape_page_returns_raw_html_value(self, key):
        with patch("app.services.firecrawl_service.httpx.AsyncClient") as cls:
            _client(cls, _resp({"success": True, "data": {"rawHtml": RAW_PAGE}}))
            assert await scrape_page("https://example.com/p") == RAW_PAGE

    @pytest.mark.asyncio
    async def test_scrape_page_with_status_returns_raw_html_value(self, key):
        with patch("app.services.firecrawl_service.httpx.AsyncClient") as cls:
            _client(cls, _resp({"success": True, "data": {"rawHtml": RAW_PAGE}}))
            assert await scrape_page_with_status("https://example.com/p") == (RAW_PAGE, 200)

    @pytest.mark.asyncio
    async def test_cleaned_html_key_is_not_a_fallback(self, key):
        """We asked for rawHtml; a body carrying only the cleaned `html` key is
        the exact 0/9 payload. Consuming it would silently restore the defect,
        so it must read as no content rather than as a successful render."""
        with patch("app.services.firecrawl_service.httpx.AsyncClient") as cls:
            _client(cls, _resp({"success": True, "data": {"html": CLEANED_PAGE}}))
            assert await scrape_page("https://example.com/p") is None

    @pytest.mark.asyncio
    async def test_flag_is_read_per_call_not_cached_at_import(self, key, monkeypatch):
        with patch("app.services.firecrawl_service.httpx.AsyncClient") as cls:
            c = _client(cls, _resp({"success": True, "data": {"rawHtml": RAW_PAGE}}))
            await scrape_page("https://example.com/p")
            assert _sent_payload(c)["formats"] == ["rawHtml"]

            monkeypatch.setenv("ENABLE_FIRECRAWL_RAW_HTML", "false")
            c.post.return_value = _resp({"success": True, "data": {"html": CLEANED_PAGE}})
            await scrape_page("https://example.com/p")
            assert _sent_payload(c)["formats"] == ["html"]


# ===========================================================================
# The controlled proof: the same page, priced through the repo's own extractor.
# This is #92's "extract_price_from_html returns a price from a Firecrawl
# response" acceptance criterion, on a recorded fixture rather than live.
# ===========================================================================
class TestExtractorPricesTheFirecrawlResponse:
    @pytest.mark.asyncio
    async def test_raw_html_response_yields_a_price(self, key, monkeypatch):
        from app.services.price_service import extract_price_from_html

        monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "false")
        with patch("app.services.firecrawl_service.httpx.AsyncClient") as cls:
            _client(cls, _resp({"success": True, "data": {"rawHtml": RAW_PAGE}}))
            html = await scrape_page("https://www.matalanme.com/p/kids-cotton-tee")

        assert html is not None
        price = extract_price_from_html(
            html, "Matalan Kids Cotton Tee", "BHD", "matalanme.com",
            "https://www.matalanme.com/p/kids-cotton-tee",
        )
        assert price and price.get("amount") == pytest.approx(1.400)
        assert price.get("currency") == "BHD"

    def test_cleaned_html_cannot_be_priced(self, monkeypatch):
        """The other half of the controlled proof — the cleaned body this
        integration used to fetch carries no ld+json, so the extractor has
        nothing to read. This is why the bake-off score was 0/9."""
        from app.services.price_service import extract_price_from_html

        monkeypatch.setenv("ENABLE_EXACT_PRICE_GATE", "false")
        assert "ld+json" not in CLEANED_PAGE
        price = extract_price_from_html(
            CLEANED_PAGE, "Matalan Kids Cotton Tee", "BHD", "matalanme.com",
            "https://www.matalanme.com/p/kids-cotton-tee",
        )
        assert not (price and price.get("amount"))


# ===========================================================================
# #92 acceptance criterion 3 — Firecrawl returns HTTP 200 (and bills) on a real
# upstream 404, so a dead registry row currently looks like a successful render.
# ===========================================================================
class TestUpstreamErrorPageShortCircuit:
    @staticmethod
    def _body(status_code: int) -> dict:
        return {
            "success": True,
            "data": {
                "rawHtml": RAW_PAGE,
                "metadata": {"sourceURL": "https://letoile.ae/gone", "statusCode": status_code},
            },
        }

    @pytest.mark.asyncio
    async def test_upstream_404_is_not_a_successful_scrape(self, key):
        with patch("app.services.firecrawl_service.httpx.AsyncClient") as cls:
            _client(cls, _resp(self._body(404)))
            assert await scrape_page("https://letoile.ae/gone") is None

    @pytest.mark.asyncio
    async def test_upstream_404_reports_status_200_so_the_billed_credit_is_recorded(self, key):
        """Firecrawl's own call succeeded and was BILLED. The caller records a
        credit only on status 200 and opens the breaker on 429/503/0, so an
        upstream 404 must surface as (None, 200): no content, credit counted,
        breaker untouched."""
        with patch("app.services.firecrawl_service.httpx.AsyncClient") as cls:
            _client(cls, _resp(self._body(404)))
            assert await scrape_page_with_status("https://letoile.ae/gone") == (None, 200)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("upstream", [400, 403, 410, 451, 500, 503])
    async def test_any_upstream_4xx_5xx_is_a_miss(self, key, upstream):
        with patch("app.services.firecrawl_service.httpx.AsyncClient") as cls:
            _client(cls, _resp(self._body(upstream)))
            assert await scrape_page("https://example.com/dead") is None

    @pytest.mark.asyncio
    @pytest.mark.parametrize("upstream", [200, 201, 301, 304])
    async def test_upstream_success_still_returns_html(self, key, upstream):
        with patch("app.services.firecrawl_service.httpx.AsyncClient") as cls:
            _client(cls, _resp(self._body(upstream)))
            assert await scrape_page("https://example.com/live") == RAW_PAGE

    @pytest.mark.asyncio
    async def test_missing_metadata_fails_open(self, key):
        """No metadata at all — do not invent a failure. Fail open."""
        with patch("app.services.firecrawl_service.httpx.AsyncClient") as cls:
            _client(cls, _resp({"success": True, "data": {"rawHtml": RAW_PAGE}}))
            assert await scrape_page("https://example.com/p") == RAW_PAGE

    @pytest.mark.asyncio
    @pytest.mark.parametrize("junk", [None, "", "n/a", [], {}, True])
    async def test_unparseable_status_code_fails_open(self, key, junk):
        body = {
            "success": True,
            "data": {"rawHtml": RAW_PAGE, "metadata": {"statusCode": junk}},
        }
        with patch("app.services.firecrawl_service.httpx.AsyncClient") as cls:
            _client(cls, _resp(body))
            assert await scrape_page("https://example.com/p") == RAW_PAGE

    @pytest.mark.asyncio
    async def test_string_status_code_is_honoured(self, key):
        body = {
            "success": True,
            "data": {"rawHtml": RAW_PAGE, "metadata": {"statusCode": "404"}},
        }
        with patch("app.services.firecrawl_service.httpx.AsyncClient") as cls:
            _client(cls, _resp(body))
            assert await scrape_page("https://example.com/p") is None

    @pytest.mark.asyncio
    async def test_non_dict_metadata_does_not_raise(self, key):
        body = {"success": True, "data": {"rawHtml": RAW_PAGE, "metadata": "oops"}}
        with patch("app.services.firecrawl_service.httpx.AsyncClient") as cls:
            _client(cls, _resp(body))
            assert await scrape_page("https://example.com/p") == RAW_PAGE


# ===========================================================================
# (c) legacy behaviour under the rollback state — byte-identical to `main`
# ===========================================================================
class TestRollbackStateIsLegacyBehaviour:
    @pytest.mark.asyncio
    async def test_requests_cleaned_html(self, rollback):
        with patch("app.services.firecrawl_service.httpx.AsyncClient") as cls:
            c = _client(cls, _resp({"success": True, "data": {"html": CLEANED_PAGE}}))
            await scrape_page("https://example.com/p")
            payload = _sent_payload(c)
            assert payload == {
                "url": "https://example.com/p",
                "formats": ["html"],
                "waitFor": firecrawl_service.FIRECRAWL_WAIT_MS,
            }

    @pytest.mark.asyncio
    async def test_reads_the_html_key(self, rollback):
        with patch("app.services.firecrawl_service.httpx.AsyncClient") as cls:
            _client(cls, _resp({"success": True, "data": {"html": CLEANED_PAGE}}))
            assert await scrape_page("https://example.com/p") == CLEANED_PAGE

    @pytest.mark.asyncio
    async def test_with_status_reads_the_html_key(self, rollback):
        with patch("app.services.firecrawl_service.httpx.AsyncClient") as cls:
            _client(cls, _resp({"success": True, "data": {"html": CLEANED_PAGE}}))
            assert await scrape_page_with_status("https://example.com/p") == (CLEANED_PAGE, 200)

    @pytest.mark.asyncio
    async def test_does_not_read_raw_html_key(self, rollback):
        with patch("app.services.firecrawl_service.httpx.AsyncClient") as cls:
            _client(cls, _resp({"success": True, "data": {"rawHtml": RAW_PAGE}}))
            assert await scrape_page("https://example.com/p") is None

    @pytest.mark.asyncio
    async def test_upstream_404_is_not_short_circuited(self, rollback):
        """`main` never looked at metadata. The rollback must not either."""
        body = {
            "success": True,
            "data": {
                "html": CLEANED_PAGE,
                "metadata": {"statusCode": 404},
            },
        }
        with patch("app.services.firecrawl_service.httpx.AsyncClient") as cls:
            _client(cls, _resp(body))
            assert await scrape_page("https://letoile.ae/gone") == CLEANED_PAGE

    @pytest.mark.asyncio
    @pytest.mark.parametrize("off", ["false", "0", "no", "off", "FALSE", "Off", " false "])
    async def test_off_spellings(self, monkeypatch, off):
        monkeypatch.setenv("FIRECRAWL_API_KEY", "test-key")
        monkeypatch.setenv("ENABLE_FIRECRAWL_RAW_HTML", off)
        with patch("app.services.firecrawl_service.httpx.AsyncClient") as cls:
            c = _client(cls, _resp({"success": True, "data": {"html": CLEANED_PAGE}}))
            await scrape_page("https://example.com/p")
            assert _sent_payload(c)["formats"] == ["html"]

    @pytest.mark.asyncio
    @pytest.mark.parametrize("on", ["true", "1", "yes", "on", "TRUE", "anything-else"])
    async def test_on_spellings(self, monkeypatch, on):
        monkeypatch.setenv("FIRECRAWL_API_KEY", "test-key")
        monkeypatch.setenv("ENABLE_FIRECRAWL_RAW_HTML", on)
        with patch("app.services.firecrawl_service.httpx.AsyncClient") as cls:
            c = _client(cls, _resp({"success": True, "data": {"rawHtml": RAW_PAGE}}))
            await scrape_page("https://example.com/p")
            assert _sent_payload(c)["formats"] == ["rawHtml"]


# ===========================================================================
# Error paths that must be unaffected by any of the above.
# ===========================================================================
class TestUnchangedErrorPaths:
    @pytest.mark.asyncio
    async def test_no_key_returns_none_without_calling(self, monkeypatch):
        monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)
        with patch("app.services.firecrawl_service.httpx.AsyncClient") as cls:
            c = _client(cls, _resp({"success": True, "data": {"rawHtml": RAW_PAGE}}))
            assert await scrape_page("https://example.com/p") is None
            assert await scrape_page_with_status("https://example.com/p") == (None, 0)
            c.post.assert_not_called()

    @pytest.mark.asyncio
    async def test_short_raw_html_is_rejected(self, key):
        with patch("app.services.firecrawl_service.httpx.AsyncClient") as cls:
            _client(cls, _resp({"success": True, "data": {"rawHtml": "<html></html>"}}))
            assert await scrape_page("https://example.com/p") is None

    @pytest.mark.asyncio
    async def test_success_false_returns_none(self, key):
        with patch("app.services.firecrawl_service.httpx.AsyncClient") as cls:
            _client(cls, _resp({"success": False, "error": "blocked"}))
            assert await scrape_page("https://example.com/p") is None

    @pytest.mark.asyncio
    async def test_http_500_propagates_status(self, key):
        with patch("app.services.firecrawl_service.httpx.AsyncClient") as cls:
            _client(cls, _resp({}, status_code=500))
            assert await scrape_page_with_status("https://example.com/p") == (None, 500)
