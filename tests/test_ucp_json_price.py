"""M10 TRACK A / UNIT A4 — the UCP free-channel price adapter, offline.

``ENABLE_UCP_JSON_PRICE``, DEFAULT OFF.

ZERO NETWORK. Every HTTP interaction goes through the single seam
``shopify_pdp_service._curl_get``, monkeypatched per test with a scripted
response. The four ``tests/fixtures/ucp_json/*.json`` payloads carry their own
provenance in that directory's SOURCES.json — one is verbatim production bytes,
one is rebuilt field-for-field from the M9 probe's measured record, and two are
DERIVED edits that pin branches the live corpus does not contain.

WHAT THIS UNIT IS, in one paragraph. The M9 `measure-ucp-free` probe (55 live
GETs across the 6 UCP-advertising Shopify hosts) found that
``GET /products/{handle}.json`` returns, per variant, a **major-unit decimal
string** ``price`` PLUS a self-declared ``price_currency`` — 32/32 present,
32/32 equal to the registry currency. That makes it the first channel in this
codebase where the currency is an OBSERVED FACT stated by the merchant rather
than a value the registry asks for. The BHD-ask inflation class (the faces.ae
9.8x that UNIT A1 fixes) cannot exist here, because nothing is asked.

The rules, and which class pins each:

  * the price is a MAJOR-UNIT decimal string and must route through the
    canonical money parser — there is NO minor-unit division on this channel.
    ``om.swissarabian.com/products/oud-malaki`` is the pin: ``.js`` ships the
    integer 1720, ``.json`` ships ``"17.200"`` OMR, and 1720/100 is 17.20 —
    NOT /1000. Feeding the decimal string to the ``.js`` helpers yields 0.17.
    -> TestMajorUnitNoDivision
  * a self-declared ``price_currency`` BEATS the registry row. On the measured
    corpus the two always agree, so only a disagreement can prove which one was
    actually read.  -> TestSelfDeclaredCurrencyWins
  * an ABSENT ``price_currency`` falls back to the registry row, and with
    neither the adapter abstains rather than stamping a guess.
    -> TestRegistryCurrencyFallback
  * ``.json`` carries no ``available``; ``.js`` carries availability but no
    currency. They are complementary, so ``.js`` is fetched ONLY when in-stock
    filtering is actually required.  -> TestJsFetchedOnlyForInStockFiltering
  * identity/size/label threading is the same machinery every other adapter
    uses — a wrong product is rejected, not priced.  -> TestIdentityThreading
  * the flag is DEFAULT OFF and gates the NETWORK: with it off the adapter
    never fires and never touches the seam.  -> TestFeatureFlag
"""

import logging
import socket
from pathlib import Path

import pytest

from app.services import price_service
from app.services import shopify_pdp_service as svc
from app.utils import url_validator


FIXTURES = Path(__file__).parent / "fixtures" / "ucp_json"

REAL_BHD = "bh_beautyandblends_com_bhd.json"
SWISS_OMR = "om_swissarabian_com_omr_major_unit.json"
CUR_ABSENT = "bh_beautyandblends_com_currency_absent_derived.json"
CUR_DISAGREES = "bh_beautyandblends_com_currency_disagrees_derived.json"

# The real product behind REAL_BHD / CUR_* (verbatim from the captured bytes).
BB_TITLE = "N 1 DEHN OUD MOATTAQ"
BB_HANDLE = "n-1-dehn-oud-moattaq"
BB_URL = "https://beautyandblends.com/products/" + BB_HANDLE
SWISS_URL = "https://om.swissarabian.com/products/oud-malaki"

_PUBLIC_IP = "93.184.216.34"
_FAKE_DNS = {
    "beautyandblends.com": _PUBLIC_IP,
    "om.swissarabian.com": _PUBLIC_IP,
    "evil.example": _PUBLIC_IP,
}


@pytest.fixture(autouse=True)
def _offline_dns(monkeypatch):
    """Deterministic OFFLINE DNS. ``validate_external_url`` resolves for real
    before it can classify the IP, so stubbing the resolver — and ONLY the
    resolver — keeps the real validator logic under test while the suite stays
    hermetic and never emits a DNS query."""

    def _fake_getaddrinfo(host, port, *args, **kwargs):
        ip = _FAKE_DNS.get((host or "").lower())
        if ip is None:
            raise socket.gaierror("offline test resolver: unknown host %r" % (host,))
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, port or 0))]

    monkeypatch.setattr(url_validator.socket, "getaddrinfo", _fake_getaddrinfo)


@pytest.fixture(autouse=True)
def _flag_on(monkeypatch):
    """Most tests exercise the ON path. TestFeatureFlag deletes it again."""
    monkeypatch.setenv("ENABLE_UCP_JSON_PRICE", "true")


@pytest.fixture(autouse=True)
def _reset_spacing():
    svc.reset_domain_spacing()
    yield
    svc.reset_domain_spacing()


@pytest.fixture
def no_sleep(monkeypatch):
    slept = []

    async def _fake_sleep(seconds):
        slept.append(seconds)

    monkeypatch.setattr(svc.asyncio, "sleep", _fake_sleep)
    return slept


def load_fixture(name: str) -> str:
    """Raw fixture TEXT — the adapter is handed a body string, not a dict."""
    return (FIXTURES / name).read_text(encoding="utf-8")


class FakeResponse:
    def __init__(self, status_code, text="", headers=None):
        self.status_code = status_code
        self.text = text
        self.headers = headers or {}


def serve(monkeypatch, *responses):
    """Point the single HTTP seam at a scripted list of responses; return the
    list of URLs actually requested, so a test can assert on what was NOT
    fetched as easily as on what was."""
    calls = []
    queue = list(responses)

    def _fake_get(url, timeout):
        calls.append(url)
        if not queue:
            raise AssertionError("unexpected extra HTTP call to %s" % url)
        return queue.pop(0)

    monkeypatch.setattr(svc, "_curl_get", _fake_get)
    return calls


# --------------------------------------------------------------- the URL shape


class TestBuildProductsJsonUrl:
    def test_appends_dot_json(self):
        assert svc.build_pdp_products_json_url(BB_URL) == BB_URL + ".json"

    def test_strips_query_and_fragment(self):
        assert (
            svc.build_pdp_products_json_url(BB_URL + "?variant=123&utm_source=x#buy")
            == BB_URL + ".json"
        )

    def test_strips_trailing_slash_before_appending(self):
        assert svc.build_pdp_products_json_url(BB_URL + "/") == BB_URL + ".json"

    def test_path_already_dot_json_is_not_doubled(self):
        assert svc.build_pdp_products_json_url(BB_URL + ".json") == BB_URL + ".json"

    def test_a_dot_js_feed_url_becomes_the_dot_json_sibling(self):
        """A caller holding the ``.js`` feed URL must get ``/x.json``, never the
        404 ``/x.js.json``. The two per-handle feeds are siblings, not layers."""
        assert svc.build_pdp_products_json_url(BB_URL + ".js") == BB_URL + ".json"

    @pytest.mark.parametrize(
        "bad", ["", None, 123, "ftp://x/products/y", "not a url", "https:///products/y"]
    )
    def test_unusable_input_returns_none(self, bad):
        assert svc.build_pdp_products_json_url(bad) is None

    def test_the_dot_js_builder_is_untouched(self):
        """UNIT A4 extends the family; it must not move the shipped ``.js``
        builder. Including its documented no-doubling behaviour."""
        assert svc.build_pdp_json_url(BB_URL) == BB_URL + ".js"
        assert svc.build_pdp_json_url(BB_URL + ".js") == BB_URL + ".js"
        assert svc.build_pdp_json_url(BB_URL + "?variant=1") == BB_URL + ".js"


class TestShopifyPdpPathProbe:
    """The cheap half of the channel probe. With the flag on, an ungated adapter
    would GET ``.json`` against every no-price page the cascade reaches — a cost
    spent on other people's servers to learn what the URL already says."""

    @pytest.mark.parametrize(
        "url",
        [
            BB_URL,
            BB_URL + ".json",
            BB_URL + ".js",
            BB_URL + "?variant=1",
            "https://om.swissarabian.com/collections/all/products/oud-malaki",
            "https://beautyandblends.com/en-bh/products/x",
        ],
    )
    def test_product_paths_are_accepted(self, url):
        assert svc.is_shopify_pdp_path(url) is True

    @pytest.mark.parametrize(
        "url",
        [
            "",
            None,
            "https://beautyandblends.com/",
            "https://beautyandblends.com/collections/all",
            "https://beautyandblends.com/search?q=oud",
            "https://beautyandblends.com/collections/all/products.json",
            "https://beautyandblends.com/products/",
            "https://example.com/shop/item/123",
        ],
    )
    def test_everything_else_is_rejected(self, url):
        assert svc.is_shopify_pdp_path(url) is False

    @pytest.mark.asyncio
    async def test_a_non_product_url_costs_no_request(self, monkeypatch, no_sleep):
        calls = serve(monkeypatch)
        assert await svc.fetch_ucp_json_product(
            "https://beautyandblends.com/collections/all",
        ) is None
        assert calls == []

    def test_the_collection_feed_is_a_discovery_channel_not_this_one(self):
        """Measured: ``/collections/all/products.json`` is currency-blind on all
        6 hosts. Accepting that envelope here would silently re-introduce the
        registry guess this unit exists to remove."""
        collection = (
            '{"products": [{"title": "x", "handle": "x",'
            ' "variants": [{"price": "20.000"}]}]}'
        )
        assert svc.parse_ucp_products_json(
            collection, registry_currency="BHD",
        ) is None


# ------------------------------------------- the major-unit decimal, no divisor


class TestMajorUnitNoDivision:
    def test_swissarabian_17_200_omr_is_17_2(self):
        """THE PIN. `.js` = 1720 minor units; `.json` = "17.200" OMR. The
        decimal string is already in major units and the correct answer is
        17.20 — reachable only by parsing, never by dividing."""
        out = svc.parse_ucp_products_json(
            load_fixture(SWISS_OMR), registry_currency="OMR"
        )
        assert out["price"] == pytest.approx(17.2)
        assert out["currency"] == "OMR"

    def test_the_dot_js_helpers_would_get_the_same_string_wrong(self):
        """Proves the two channels are genuinely incompatible rather than
        merely different, so routing `.json` through the `.js` money helpers is
        a real 100x bug and not a stylistic preference."""
        assert svc._to_major(svc._to_minor("17.200")) == pytest.approx(0.17)

    def test_beautyandblends_20_000_bhd_is_20_not_20000_and_not_0_02(self):
        """BHD's ISO 4217 minor unit is 3, which is exactly the case a
        last-separator rule without the currency fact gets wrong."""
        out = svc.parse_ucp_products_json(
            load_fixture(REAL_BHD), registry_currency="BHD"
        )
        assert out["price"] == pytest.approx(20.0)
        assert out["currency"] == "BHD"

    def test_the_parser_used_is_the_canonical_one(self):
        """The adapter must not grow a private money reading. Same string, same
        currency, same answer as ``price_service.parse_money``."""
        assert svc.parse_ucp_products_json(
            load_fixture(SWISS_OMR), registry_currency="OMR"
        )["price"] == price_service.parse_money("17.200", "OMR")


# -------------------------------------------------- currency: who wins, and why


class TestSelfDeclaredCurrencyWins:
    def test_a_disagreeing_self_declared_code_beats_the_registry(self):
        out = svc.parse_ucp_products_json(
            load_fixture(CUR_DISAGREES), registry_currency="BHD"
        )
        assert out["currency"] == "AED"
        assert out["currency_source"] == "self_declared"

    def test_agreement_is_also_stamped_self_declared_not_registry(self):
        """32/32 of the measured corpus agrees, so the provenance label is the
        only thing that distinguishes 'the merchant told us' from 'we assumed'.
        A coincidence must not be recorded as evidence."""
        out = svc.parse_ucp_products_json(
            load_fixture(REAL_BHD), registry_currency="BHD"
        )
        assert out["currency"] == "BHD"
        assert out["currency_source"] == "self_declared"

    def test_a_junk_self_declared_code_does_not_win(self):
        """Precedence applies to a RESOLVABLE ISO code. An unresolvable token
        is not evidence, so the registry still answers."""
        raw = load_fixture(REAL_BHD)
        payload = raw.replace('"price_currency":"BHD"',
                              '"price_currency":"\\u00a4\\u00a4\\u00a4"')
        # The captured bytes are COMPACT JSON. Assert the substitution actually
        # landed, so a re-capture with different whitespace fails loudly here
        # instead of silently re-testing the plain happy path.
        assert payload != raw
        out = svc.parse_ucp_products_json(payload, registry_currency="BHD")
        assert out["currency"] == "BHD"
        assert out["currency_source"] == "registry"


class TestRegistryCurrencyFallback:
    def test_absent_field_falls_back_to_the_registry_row(self):
        out = svc.parse_ucp_products_json(
            load_fixture(CUR_ABSENT), registry_currency="BHD"
        )
        assert out["price"] == pytest.approx(20.0)
        assert out["currency"] == "BHD"
        assert out["currency_source"] == "registry"

    def test_absent_field_and_no_registry_row_abstains(self):
        """Never fabricate a currency. Decision-F: an honest miss beats a
        wrong-price stamp, and an unlabelled amount is a wrong-price stamp
        waiting for a downstream default."""
        out = svc.parse_ucp_products_json(load_fixture(CUR_ABSENT))
        assert out is None

    def test_an_unresolvable_registry_row_also_abstains(self):
        assert svc.parse_ucp_products_json(
            load_fixture(CUR_ABSENT), registry_currency="not-a-currency"
        ) is None


# ------------------------------------------------------------- payload shapes


class TestPayloadShapes:
    def test_the_product_envelope_is_unwrapped(self):
        out = svc.parse_ucp_products_json(
            load_fixture(REAL_BHD), registry_currency="BHD"
        )
        assert out["title"] == BB_TITLE
        assert out["handle"] == BB_HANDLE
        assert out["vendor"] == "Beauty Blends"

    def test_source_is_stamped_distinctly_from_the_js_adapter(self):
        out = svc.parse_ucp_products_json(
            load_fixture(REAL_BHD), registry_currency="BHD"
        )
        assert out["source"] == "ucp_products_json"

    def test_availability_is_reported_unknown_never_invented(self):
        """`.json` carries no ``available``. Claiming True would be a
        fabrication and claiming False would pend a live product."""
        out = svc.parse_ucp_products_json(
            load_fixture(REAL_BHD), registry_currency="BHD"
        )
        assert out["in_stock"] is None
        assert out["availability_known"] is False

    @pytest.mark.parametrize(
        "bad",
        [
            None, "", "not json", b"\xff\xfe", [], 42,
            '{"products": [{"variants": []}]}',   # the COLLECTION feed, not a PDP
            '{"product": {}}',
            '{"product": {"variants": []}}',
            '{"product": {"variants": "nope"}}',
        ],
    )
    def test_non_product_payloads_return_none(self, bad):
        assert svc.parse_ucp_products_json(bad, registry_currency="BHD") is None

    def test_never_raises_on_garbage_variant_rows(self):
        payload = {
            "product": {
                "title": "x", "handle": "x",
                "variants": [None, 7, "s", [], {"price": None}, {"price": {}}],
            }
        }
        assert svc.parse_ucp_products_json(payload, registry_currency="BHD") is None


# ------------------------------------------------------- the feature flag gate


class TestFeatureFlag:
    def test_default_is_off(self, monkeypatch):
        monkeypatch.delenv("ENABLE_UCP_JSON_PRICE", raising=False)
        assert svc.ucp_json_price_enabled() is False

    @pytest.mark.parametrize("val", ["true", "TRUE", "1", "yes", "on", " True "])
    def test_truthy_values_turn_it_on(self, monkeypatch, val):
        monkeypatch.setenv("ENABLE_UCP_JSON_PRICE", val)
        assert svc.ucp_json_price_enabled() is True

    @pytest.mark.parametrize("val", ["", "false", "0", "no", "off", "maybe", "tru"])
    def test_everything_else_stays_off(self, monkeypatch, val):
        monkeypatch.setenv("ENABLE_UCP_JSON_PRICE", val)
        assert svc.ucp_json_price_enabled() is False

    def test_flag_is_read_per_call_never_cached_at_import(self, monkeypatch):
        monkeypatch.setenv("ENABLE_UCP_JSON_PRICE", "true")
        assert svc.ucp_json_price_enabled() is True
        monkeypatch.setenv("ENABLE_UCP_JSON_PRICE", "false")
        assert svc.ucp_json_price_enabled() is False

    @pytest.mark.asyncio
    async def test_flag_off_makes_no_network_call_at_all(self, monkeypatch):
        monkeypatch.delenv("ENABLE_UCP_JSON_PRICE", raising=False)
        calls = serve(monkeypatch)  # any call raises "unexpected extra HTTP call"
        assert await svc.fetch_ucp_json_product(BB_URL, registry_currency="BHD") is None
        assert await svc.fetch_ucp_json_price(BB_URL, BB_TITLE, "BHD") is None
        assert calls == []

    @pytest.mark.asyncio
    async def test_flag_off_is_byte_identical_at_the_price_service_shim(
        self, monkeypatch
    ):
        """The cascade shim must be inert with the flag off — same None the
        pre-A4 cascade produced, and no import-time side effect either."""
        monkeypatch.delenv("ENABLE_UCP_JSON_PRICE", raising=False)
        calls = serve(monkeypatch)
        assert await price_service._try_ucp_json_price(BB_URL, BB_TITLE, "BHD") is None
        assert calls == []


# --------------------------------------------------- the two complementary feeds


@pytest.mark.asyncio
class TestJsFetchedOnlyForInStockFiltering:
    async def test_the_default_path_fetches_only_the_dot_json_feed(
        self, monkeypatch, no_sleep
    ):
        calls = serve(monkeypatch, FakeResponse(200, load_fixture(REAL_BHD)))
        out = await svc.fetch_ucp_json_price(BB_URL, BB_TITLE, "BHD")
        assert out is not None
        assert calls == [BB_URL + ".json"]

    async def test_in_stock_filtering_adds_the_dot_js_call(
        self, monkeypatch, no_sleep
    ):
        js_body = (
            '{"id": 1, "title": "%s", "available": true, "price": 20000,'
            ' "variants": [{"id": 47867259715811, "title": "Default Title",'
            ' "price": 20000, "available": true}]}' % BB_TITLE
        )
        calls = serve(
            monkeypatch,
            FakeResponse(200, load_fixture(REAL_BHD)),
            FakeResponse(200, js_body),
        )
        out = await svc.fetch_ucp_json_price(
            BB_URL, BB_TITLE, "BHD", require_in_stock=True
        )
        assert calls == [BB_URL + ".json", BB_URL + ".js"]
        assert out is not None
        assert out["in_stock"] is True
        # The PRICE still comes from `.json` — `.js` only answers availability.
        assert out["amount"] == pytest.approx(20.0)

    async def test_a_sold_out_variant_is_dropped_when_in_stock_is_required(
        self, monkeypatch, no_sleep
    ):
        js_body = (
            '{"id": 1, "title": "%s", "available": false, "price": 20000,'
            ' "variants": [{"id": 47867259715811, "title": "Default Title",'
            ' "price": 20000, "available": false}]}' % BB_TITLE
        )
        serve(
            monkeypatch,
            FakeResponse(200, load_fixture(REAL_BHD)),
            FakeResponse(200, js_body),
        )
        assert await svc.fetch_ucp_json_price(
            BB_URL, BB_TITLE, "BHD", require_in_stock=True
        ) is None

    async def test_an_unavailable_dot_js_does_not_veto_the_default_path(
        self, monkeypatch, no_sleep
    ):
        """Availability is only consulted when it was asked for. Otherwise the
        adapter reports ``in_stock=None`` (unknown) and lets the display
        chokepoint decide — it must not spend a second GET to invent a flag."""
        calls = serve(monkeypatch, FakeResponse(200, load_fixture(REAL_BHD)))
        out = await svc.fetch_ucp_json_price(BB_URL, BB_TITLE, "BHD")
        assert out["in_stock"] is None
        assert len(calls) == 1


# ------------------------------------------------------- the end-to-end fetch


@pytest.mark.asyncio
class TestFetch:
    async def test_the_happy_path_returns_a_standard_price_dict(
        self, monkeypatch, no_sleep
    ):
        serve(monkeypatch, FakeResponse(200, load_fixture(REAL_BHD)))
        out = await svc.fetch_ucp_json_price(BB_URL, BB_TITLE, "BHD")
        assert out["amount"] == pytest.approx(20.0)
        assert out["currency"] == "BHD"
        assert out["original_currency"] == "BHD"
        assert out["retailer"] == "beautyandblends.com"
        assert out["url"] == BB_URL
        assert out["estimated"] is False
        assert out["source_method"] == "shopify_json"
        assert out["price_currency_source"] == "self_declared"

    async def test_a_native_currency_match_is_never_labelled_converted(
        self, monkeypatch, no_sleep
    ):
        serve(monkeypatch, FakeResponse(200, load_fixture(REAL_BHD)))
        out = await svc.fetch_ucp_json_price(BB_URL, BB_TITLE, "BHD")
        assert out["source_method"] != "converted_usd"

    async def test_a_non_target_currency_is_converted_and_relabelled(
        self, monkeypatch, no_sleep
    ):
        """OMR is not the BHD target, so the amount is converted and stamped
        with the canonical converted sentinel — a converted figure must never
        bank as a genuine BH price."""
        serve(monkeypatch, FakeResponse(200, load_fixture(SWISS_OMR)))
        out = await svc.fetch_ucp_json_price(
            SWISS_URL, "Swiss Arabian Oud Malaki", "BHD",
        )
        assert out is not None
        assert out["currency"] == "BHD"
        assert out["original_currency"] == "OMR"
        assert out["source_method"] == "converted_usd"
        assert out["amount"] != pytest.approx(17.2)

    async def test_non_200_returns_none(self, monkeypatch, no_sleep):
        serve(monkeypatch, FakeResponse(404, "<html>not found</html>"))
        assert await svc.fetch_ucp_json_price(BB_URL, BB_TITLE, "BHD") is None

    async def test_an_html_body_with_200_returns_none(self, monkeypatch, no_sleep):
        serve(monkeypatch, FakeResponse(200, "<!doctype html><html></html>"))
        assert await svc.fetch_ucp_json_price(BB_URL, BB_TITLE, "BHD") is None

    async def test_a_transport_exception_returns_none(self, monkeypatch, no_sleep):
        def _boom(url, timeout):
            raise RuntimeError("socket exploded")

        monkeypatch.setattr(svc, "_curl_get", _boom)
        assert await svc.fetch_ucp_json_price(BB_URL, BB_TITLE, "BHD") is None

    async def test_a_blocked_ssrf_hop_makes_no_request(self, monkeypatch, no_sleep):
        """Same-site pin: a `/products/...` URL on one host must never be
        fetched against another host's domain key."""
        calls = serve(monkeypatch)
        assert await svc.fetch_ucp_json_price(
            "http://169.254.169.254/products/x", "x", "BHD",
        ) is None
        assert calls == []


# ------------------------------------------------------------ identity threading


@pytest.mark.asyncio
class TestIdentityThreading:
    async def test_a_wrong_product_is_rejected_not_priced(
        self, monkeypatch, no_sleep
    ):
        """The adapter threads the SAME identity machinery as every sibling —
        a cheap free channel is not a licence to skip the exact-SKU gate."""
        serve(monkeypatch, FakeResponse(200, load_fixture(REAL_BHD)))
        assert await svc.fetch_ucp_json_price(
            BB_URL, "Tom Ford Oud Wood 100ml", "BHD",
        ) is None

    async def test_the_size_and_concentration_axes_are_captured(
        self, monkeypatch, no_sleep
    ):
        serve(monkeypatch, FakeResponse(200, load_fixture(SWISS_OMR)))
        out = await svc.fetch_ucp_json_price(
            SWISS_URL, "Swiss Arabian Oud Malaki", "BHD",
        )
        assert "size" in out and "concentration" in out
        assert "title" in out and "match_score" in out


# --------------------------------------------------------------- the cascade shim


@pytest.mark.asyncio
class TestCascadeFlagOffIsByteIdentical:
    """House rule 1, proven rather than asserted. UNIT A4 adds two call sites to
    ``fetch_page_price``; with the flag off each must produce the EXACT sentinel
    the pre-A4 cascade produced, and must not cost a request."""

    @pytest.fixture(autouse=True)
    def _no_html_price(self, monkeypatch):
        monkeypatch.setattr(price_service, "ENABLE_PAGE_SCRAPE", True)
        monkeypatch.setattr(
            price_service, "extract_price_from_html", lambda *a, **k: None,
        )

    def _html_returns(self, monkeypatch, value):
        async def _fetch(url, domain, **kwargs):
            return value

        monkeypatch.setattr(price_service, "curl_fetch_html_same_site", _fetch)

    async def test_the_got_html_sentinel_is_unchanged(self, monkeypatch, no_sleep):
        """HTML present, no structured price -> ``{"_got_html": True}``, the
        page-level RENDER-CANDIDATE token, exactly as before."""
        monkeypatch.delenv("ENABLE_UCP_JSON_PRICE", raising=False)
        self._html_returns(monkeypatch, "<html>no price here</html>")
        calls = serve(monkeypatch)
        assert await price_service.fetch_page_price(
            BB_URL, BB_TITLE, "BHD",
        ) == {"_got_html": True}
        assert calls == []

    async def test_the_walled_none_is_unchanged(self, monkeypatch, no_sleep):
        """HTML route walled -> ``None``, exactly as before."""
        monkeypatch.delenv("ENABLE_UCP_JSON_PRICE", raising=False)
        self._html_returns(monkeypatch, None)
        calls = serve(monkeypatch)
        assert await price_service.fetch_page_price(BB_URL, BB_TITLE, "BHD") is None
        assert calls == []

    async def test_flag_on_the_no_price_branch_recovers_the_price(
        self, monkeypatch, no_sleep
    ):
        """The other half of the contract: the rung is inert OFF because it is
        gated, not because it is broken."""
        self._html_returns(monkeypatch, "<html>no price here</html>")
        serve(monkeypatch, FakeResponse(200, load_fixture(REAL_BHD)))
        out = await price_service.fetch_page_price(BB_URL, BB_TITLE, "BHD")
        assert out["amount"] == pytest.approx(20.0)
        assert out["currency"] == "BHD"

    async def test_flag_on_the_walled_branch_recovers_the_price(
        self, monkeypatch, no_sleep
    ):
        """om.swissarabian.com is both a measured UCP host and one of UNIT A2's
        wall false-positives, so a wall verdict on this family is exactly where
        a free JSON feed earns its keep."""
        self._html_returns(monkeypatch, None)
        serve(monkeypatch, FakeResponse(200, load_fixture(SWISS_OMR)))
        out = await price_service.fetch_page_price(
            SWISS_URL, "Swiss Arabian Oud Malaki", "BHD",
        )
        assert out is not None
        assert out["original_currency"] == "OMR"


@pytest.mark.asyncio
class TestPriceServiceShim:
    async def test_the_shim_delegates_when_the_flag_is_on(
        self, monkeypatch, no_sleep
    ):
        serve(monkeypatch, FakeResponse(200, load_fixture(REAL_BHD)))
        out = await price_service._try_ucp_json_price(BB_URL, BB_TITLE, "BHD")
        assert out is not None
        assert out["amount"] == pytest.approx(20.0)

    async def test_the_shim_never_raises(self, monkeypatch):
        def _boom(*a, **k):
            raise RuntimeError("adapter exploded")

        monkeypatch.setattr(svc, "fetch_ucp_json_price", _boom)
        assert await price_service._try_ucp_json_price(BB_URL, BB_TITLE, "BHD") is None


@pytest.mark.asyncio
class TestShimExceptionTriage:
    """M11 backlog item 1 (recorded M10 verify finding). The shim's single bare
    ``except Exception: return None`` collapsed three DISTINCT states into one
    silent None: the flag being off, an expected miss (404 / non-JSON body / no
    matching variant), and a genuine defect. The first two are routine; the
    third was invisible — a bug in the adapter would be indistinguishable from
    "the flag is off". Split:

      * flag OFF        -> quiet None, byte-identical pre-A4 path, ZERO log
      * expected miss   -> None with a DEBUG line only (never WARNING)
      * genuine defect  -> None (the live path must never raise) plus ONE
                           WARNING naming the host and the exception class
    """

    async def test_flag_off_is_completely_silent(self, monkeypatch, caplog):
        """The untouched pre-A4 path: no request, no log record at any level."""
        monkeypatch.delenv("ENABLE_UCP_JSON_PRICE", raising=False)
        calls = serve(monkeypatch)
        with caplog.at_level(logging.DEBUG):
            out = await price_service._try_ucp_json_price(BB_URL, BB_TITLE, "BHD")
        assert out is None
        assert calls == []
        assert [r for r in caplog.records if "[UCP_JSON]" in r.getMessage()] == []

    async def test_an_expected_miss_is_debug_not_warning(
        self, monkeypatch, no_sleep, caplog
    ):
        """A 404 on the feed is the channel working as designed (the M9 probe
        measured 2 of 34 handles missing). It must not cry wolf."""
        serve(monkeypatch, FakeResponse(404, "<html>not found</html>"))
        with caplog.at_level(logging.DEBUG):
            out = await price_service._try_ucp_json_price(BB_URL, BB_TITLE, "BHD")
        assert out is None
        assert [
            r for r in caplog.records
            if r.levelno >= logging.WARNING and "[UCP_JSON]" in r.getMessage()
        ] == []
        assert [
            r for r in caplog.records
            if r.levelno == logging.DEBUG
            and r.name == "app.services.price_service"
            and "[UCP_JSON]" in r.getMessage()
        ], "the shim must leave a DEBUG trace of an expected miss"

    async def test_a_non_matching_variant_is_also_an_expected_miss(
        self, monkeypatch, no_sleep, caplog
    ):
        """The identity gate rejecting a wrong product is a miss, not a defect."""
        serve(monkeypatch, FakeResponse(200, load_fixture(REAL_BHD)))
        with caplog.at_level(logging.DEBUG):
            out = await price_service._try_ucp_json_price(
                BB_URL, "Tom Ford Oud Wood 100ml", "BHD",
            )
        assert out is None
        assert [
            r for r in caplog.records
            if r.levelno >= logging.WARNING and "[UCP_JSON]" in r.getMessage()
        ] == []

    async def test_a_genuine_defect_warns_with_host_and_exception_class(
        self, monkeypatch, caplog
    ):
        """An exception escaping the adapter is a DEFECT: still return None
        (the live path must never raise) but say so — host + exception class."""
        def _boom(*a, **k):
            raise RuntimeError("adapter exploded")

        monkeypatch.setattr(svc, "fetch_ucp_json_price", _boom)
        with caplog.at_level(logging.DEBUG):
            out = await price_service._try_ucp_json_price(BB_URL, BB_TITLE, "BHD")
        assert out is None
        warnings = [
            r for r in caplog.records
            if r.levelno == logging.WARNING
            and r.name == "app.services.price_service"
            and "[UCP_JSON]" in r.getMessage()
        ]
        assert len(warnings) == 1
        msg = warnings[0].getMessage()
        assert "RuntimeError" in msg
        assert "beautyandblends.com" in msg

    async def test_a_defect_of_a_different_class_names_that_class(
        self, monkeypatch, caplog
    ):
        """The class is in the message so triage can bucket without a repro."""
        def _boom(*a, **k):
            raise KeyError("variants")

        monkeypatch.setattr(svc, "fetch_ucp_json_price", _boom)
        with caplog.at_level(logging.WARNING):
            out = await price_service._try_ucp_json_price(BB_URL, BB_TITLE, "BHD")
        assert out is None
        msgs = [
            r.getMessage() for r in caplog.records
            if r.levelno == logging.WARNING and "[UCP_JSON]" in r.getMessage()
        ]
        assert any("KeyError" in m for m in msgs)

    async def test_a_recovered_price_leaves_no_miss_log(
        self, monkeypatch, no_sleep, caplog
    ):
        serve(monkeypatch, FakeResponse(200, load_fixture(REAL_BHD)))
        with caplog.at_level(logging.DEBUG):
            out = await price_service._try_ucp_json_price(BB_URL, BB_TITLE, "BHD")
        assert out is not None
        assert [
            r for r in caplog.records
            if r.name == "app.services.price_service"
            and "[UCP_JSON]" in r.getMessage()
        ] == []
