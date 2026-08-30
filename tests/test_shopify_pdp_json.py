"""Shopify ``{pdp_url}.js`` adapter - offline tests (STEP 5).

ZERO NETWORK. Every HTTP interaction goes through the single seam
``shopify_pdp_service._curl_get``, which each test monkeypatches with a fake
response object. The four ``tests/fixtures/shopify_js/*.json`` payloads are real
production bytes captured once (see that directory's SOURCES.json) and are
replayed here verbatim.

What the measured rules are, and which test pins each one:

  * ALWAYS divide the minor-unit integer by 100 - INCLUDING the 3-decimal Gulf
    currencies. ``bh.taifalemarat`` ships 6066 for a 60.66 BHD box and
    ``alhajisoman`` ships 3000 for 30.00 OMR. A currency-table divisor would
    read those as 6.066 / 3.000.  -> TestThreeDecimalGulfCurrencies
  * The price is the minimum over the AVAILABLE variants, never over all of
    them.  -> TestVariantSelection
  * With NO available variant we still return a price, but flagged
    ``in_stock=False`` and labelled ``price_basis="product_price_no_stock"``, so
    a caller can never mistake a sold-out range floor for a shelf price.
    -> TestZeroAvailableVariants
  * ``compare_at_price`` becomes ``list_price`` only when it EXCEEDS the price;
    Shopify writes a literal 0 for "no compare-at" on many themes.
    -> TestCompareAtPrice
  * 503 is the burst-throttle signal: retry once, then None so the caller falls
    through to the HTML cascade.  -> TestRetryAndStatusHandling
  * >=1s per-domain spacing, reserved before the request so concurrent callers
    queue instead of colliding.  -> TestPerDomainSpacing
  * SSRF: the initial URL and EVERY redirect hop must pass the repo's own
    ``validate_external_url`` + same-site pin.  -> TestSsrf
  * The flag is DEFAULT OFF and gates the NETWORK, not the parser.
    -> TestFeatureFlag
"""

import socket
from pathlib import Path

import pytest

from app.services import shopify_pdp_service as svc
from app.utils import url_validator


FIXTURES = Path(__file__).parent / "fixtures" / "shopify_js"

# Deterministic, OFFLINE DNS. `validate_external_url` resolves the hostname for
# real before it can classify the IP, so without this the SSRF tests would make
# live DNS queries and their outcome would depend on whether
# `cdn.bh.mubkhar.com` happens to exist today. Stubbing the resolver — and only
# the resolver — keeps the REAL validator logic (scheme check, ip_address
# classification, private/loopback/link-local/reserved rejection) under test
# while the suite stays hermetic.
_PUBLIC_IP = "93.184.216.34"
_FAKE_DNS = {
    "bh.mubkhar.com": _PUBLIC_IP,
    "cdn.bh.mubkhar.com": _PUBLIC_IP,
    "evil.example": _PUBLIC_IP,
    "a.com": _PUBLIC_IP,
    "b.com": _PUBLIC_IP,
    "127.0.0.1": "127.0.0.1",
    "169.254.169.254": "169.254.169.254",
}


@pytest.fixture(autouse=True)
def _offline_dns(monkeypatch):
    def _fake_getaddrinfo(host, port, *args, **kwargs):
        ip = _FAKE_DNS.get((host or "").lower())
        if ip is None:
            raise socket.gaierror("offline test resolver: unknown host %r" % (host,))
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, port or 0))]

    monkeypatch.setattr(url_validator.socket, "getaddrinfo", _fake_getaddrinfo)


def load_fixture(name: str) -> str:
    """Raw fixture TEXT (the adapter is handed a body string, not a dict)."""
    return (FIXTURES / name).read_text(encoding="utf-8")


class FakeResponse:
    """Minimal stand-in for a curl_cffi response."""

    def __init__(self, status_code, text="", headers=None):
        self.status_code = status_code
        self.text = text
        self.headers = headers or {}


@pytest.fixture(autouse=True)
def _flag_on(monkeypatch):
    """Most tests exercise the ON path. TestFeatureFlag deletes it again."""
    monkeypatch.setenv("ENABLE_SHOPIFY_PDP_JSON", "true")


@pytest.fixture(autouse=True)
def _reset_spacing():
    """The per-domain spacing table is module state - never leak it across tests."""
    svc.reset_domain_spacing()
    yield
    svc.reset_domain_spacing()


@pytest.fixture
def no_sleep(monkeypatch):
    """Record every spacing sleep instead of actually waiting."""
    slept = []

    async def _fake_sleep(seconds):
        slept.append(seconds)

    monkeypatch.setattr(svc.asyncio, "sleep", _fake_sleep)
    return slept


def serve(monkeypatch, *responses):
    """Point the single HTTP seam at a scripted list of responses.

    Returns the list of URLs actually requested, so a test can assert that a
    blocked hop produced NO request at all.
    """
    calls = []
    queue = list(responses)

    def _fake_get(url, timeout):
        calls.append(url)
        if not queue:
            raise AssertionError("unexpected extra HTTP call to %s" % url)
        return queue.pop(0)

    monkeypatch.setattr(svc, "_curl_get", _fake_get)
    return calls


# ---------------------------------------------------------------- URL building


class TestBuildPdpJsonUrl:
    def test_appends_dot_js(self):
        assert (
            svc.build_pdp_json_url("https://bh.mubkhar.com/products/california-gold")
            == "https://bh.mubkhar.com/products/california-gold.js"
        )

    def test_strips_query_and_fragment(self):
        assert (
            svc.build_pdp_json_url(
                "https://bh.mubkhar.com/products/x?variant=123&utm_source=serper#reviews"
            )
            == "https://bh.mubkhar.com/products/x.js"
        )

    def test_strips_trailing_slash_before_appending(self):
        assert (
            svc.build_pdp_json_url("https://bh.mubkhar.com/products/x/")
            == "https://bh.mubkhar.com/products/x.js"
        )

    def test_path_already_dot_js_is_not_doubled(self):
        assert (
            svc.build_pdp_json_url("https://bh.mubkhar.com/products/x.js?v=1")
            == "https://bh.mubkhar.com/products/x.js"
        )

    def test_uppercase_dot_js_also_recognised(self):
        assert (
            svc.build_pdp_json_url("https://bh.mubkhar.com/products/X.JS")
            == "https://bh.mubkhar.com/products/X.JS"
        )

    @pytest.mark.parametrize(
        "bad",
        [
            "",
            None,
            "ftp://bh.mubkhar.com/products/x",
            "file:///etc/passwd",
            "javascript:alert(1)",
            "/products/x",
            "not a url",
        ],
    )
    def test_unusable_input_returns_none(self, bad):
        assert svc.build_pdp_json_url(bad) is None


# ------------------------------------------------------------------ divide/100


class TestThreeDecimalGulfCurrencies:
    """The single most expensive thing to get wrong: BHD/OMR/KWD are 3-decimal
    currencies, but Shopify's minor unit on these stores is still 1/100."""

    def test_bhd_6066_is_60_66_not_6_066(self):
        out = svc.parse_shopify_pdp_json(load_fixture("bh_taifalemarat_com.json"))
        assert out["price"] == 60.66
        assert out["price_minor"] == 6066

    def test_omr_3000_is_30_00_not_3_000(self):
        out = svc.parse_shopify_pdp_json(load_fixture("alhajisoman_com.json"))
        assert out["price"] == 30.00
        assert out["price_minor"] == 3000

    def test_bhd_620_is_6_20(self):
        out = svc.parse_shopify_pdp_json(load_fixture("bh_mubkhar_com.json"))
        assert out["price"] == 6.20


# -------------------------------------------------------------- zero available


class TestZeroAvailableVariants:
    """``www.watsons.sa`` has five variants spanning 20.10 - 70.00 and NOT ONE of
    them is available. Returning 20.10 as if it were purchasable is exactly the
    failure mode this rule exists to prevent."""

    def test_price_is_returned_but_flagged_out_of_stock(self):
        out = svc.parse_shopify_pdp_json(load_fixture("www_watsons_sa.json"))
        assert out is not None
        assert out["in_stock"] is False
        assert out["price"] is not None

    def test_price_basis_names_the_sold_out_provenance(self):
        out = svc.parse_shopify_pdp_json(load_fixture("www_watsons_sa.json"))
        assert out["price_basis"] == "product_price_no_stock"

    def test_available_variant_count_is_zero_over_five_variants(self):
        out = svc.parse_shopify_pdp_json(load_fixture("www_watsons_sa.json"))
        assert out["variant_count"] == 5
        assert out["available_variant_count"] == 0

    def test_single_variant_sold_out_product_also_flagged(self):
        out = svc.parse_shopify_pdp_json(load_fixture("bh_taifalemarat_com.json"))
        assert out["in_stock"] is False
        assert out["available_variant_count"] == 0
        assert out["price_basis"] == "product_price_no_stock"

    def test_sold_out_price_is_the_declared_price_not_a_computed_floor(self):
        """THE rule: with nothing available we never widen the min-over-available
        filter into a min-over-everything. We read the price the store itself
        declares and flag it.

        Constructed so the two answers differ - Shopify's own ``price`` field is
        normally ``price_min``, which is why the real ``watsons.sa`` fixture
        cannot tell a declared price apart from a computed floor. Here the
        declared price is 5000 while the cheapest sold-out variant is 1000, so a
        regression that reaches for the cheapest overall returns 10.00 and this
        test catches it."""
        payload = {
            "id": 1,
            "handle": "t",
            "available": False,
            "price": 5000,
            "price_min": 1000,
            "price_max": 5000,
            "variants": [
                {"id": 11, "price": 5000, "available": False, "sku": "DEFAULT"},
                {"id": 12, "price": 1000, "available": False, "sku": "CHEAPEST-GONE"},
            ],
        }
        out = svc.parse_shopify_pdp_json(payload)
        assert out["price"] == 50.00
        assert out["in_stock"] is False
        assert out["price_basis"] == "product_price_no_stock"

    def test_the_variant_range_is_exposed_so_the_caller_can_see_it(self):
        """A sold-out price is advisory, so the caller gets the whole range too
        rather than one number stripped of its context."""
        out = svc.parse_shopify_pdp_json(load_fixture("www_watsons_sa.json"))
        assert out["price_min"] == 20.10
        assert out["price_max"] == 70.00


# ------------------------------------------------------------- variant picking


class TestVariantSelection:
    def test_min_is_taken_over_available_variants_only(self):
        payload = {
            "id": 1,
            "title": "T",
            "handle": "t",
            "available": True,
            "price": 1000,
            "variants": [
                {"id": 11, "price": 1000, "available": False, "sku": "CHEAP-GONE"},
                {"id": 12, "price": 5000, "available": True, "sku": "PRICEY-HERE"},
                {"id": 13, "price": 7000, "available": True, "sku": "PRICIEST"},
            ],
        }
        out = svc.parse_shopify_pdp_json(payload)
        assert out["price"] == 50.00
        assert out["in_stock"] is True
        assert out["price_basis"] == "available_variant_min"

    def test_sku_comes_from_the_selected_variant(self):
        payload = {
            "id": 1,
            "handle": "t",
            "available": True,
            "price": 1000,
            "variants": [
                {"id": 11, "price": 1000, "available": False, "sku": "CHEAP-GONE"},
                {"id": 12, "price": 5000, "available": True, "sku": "PRICEY-HERE"},
            ],
        }
        out = svc.parse_shopify_pdp_json(payload)
        assert out["sku"] == "PRICEY-HERE"
        assert out["variant_id"] == 12

    def test_top_level_unavailable_vetoes_variant_flags(self):
        """Availability is the AND of the top-level flag and the variant flags."""
        payload = {
            "id": 1,
            "handle": "t",
            "available": False,
            "price": 5000,
            "variants": [{"id": 12, "price": 5000, "available": True, "sku": "S"}],
        }
        out = svc.parse_shopify_pdp_json(payload)
        assert out["in_stock"] is False

    def test_real_sold_out_fixture_sku_still_captured(self):
        out = svc.parse_shopify_pdp_json(load_fixture("bh_taifalemarat_com.json"))
        assert out["sku"] == "6290360258195"


# ------------------------------------------------------------ compare_at_price


class TestCompareAtPrice:
    def test_compare_at_above_price_becomes_list_price(self):
        out = svc.parse_shopify_pdp_json(load_fixture("alhajisoman_com.json"))
        assert out["price"] == 30.00
        assert out["list_price"] == 45.00

    def test_compare_at_zero_is_not_a_list_price(self):
        """Many themes write a literal 0 rather than null for 'no compare-at'."""
        out = svc.parse_shopify_pdp_json(load_fixture("bh_mubkhar_com.json"))
        assert out["list_price"] is None

    def test_compare_at_null_is_not_a_list_price(self):
        out = svc.parse_shopify_pdp_json(load_fixture("bh_taifalemarat_com.json"))
        assert out["list_price"] is None

    def test_compare_at_equal_to_price_is_not_a_discount(self):
        payload = {
            "id": 1,
            "handle": "t",
            "available": True,
            "price": 5000,
            "variants": [
                {
                    "id": 12,
                    "price": 5000,
                    "compare_at_price": 5000,
                    "available": True,
                    "sku": "S",
                }
            ],
        }
        assert svc.parse_shopify_pdp_json(payload)["list_price"] is None


# ----------------------------------------------------------------- wide fields


class TestNormalisedFields:
    def test_vendor_product_type_and_tags(self):
        out = svc.parse_shopify_pdp_json(load_fixture("bh_mubkhar_com.json"))
        assert out["vendor"] == "Mubkhar"
        assert out["product_type"] == "Essential Oils 2.0"
        assert "Essential Oils 2.0" in out["tags"]

    def test_body_html_is_populated_from_the_js_description_key(self):
        """``{pdp}.js`` names it ``description``; ``products.json`` names it
        ``body_html``. The adapter normalises to ``body_html`` so both feeds
        look the same to a caller."""
        out = svc.parse_shopify_pdp_json(load_fixture("bh_taifalemarat_com.json"))
        assert out["body_html"]
        assert isinstance(out["body_html"], str)

    def test_options_images_and_featured_image(self):
        out = svc.parse_shopify_pdp_json(load_fixture("bh_taifalemarat_com.json"))
        assert out["featured_image"]
        assert len(out["images"]) == 5
        assert out["options"][0]["name"] == "Title"

    def test_full_variant_list_is_carried_through(self):
        out = svc.parse_shopify_pdp_json(load_fixture("www_watsons_sa.json"))
        assert len(out["variants"]) == 5
        assert out["variants"][0]["sku"] == "ASW200001973"

    def test_title_handle_and_product_id(self):
        out = svc.parse_shopify_pdp_json(load_fixture("alhajisoman_com.json"))
        assert out["handle"] == "ch-212-vip-party-fever-edt-ladies-80ml"
        assert out["product_id"] == 8084236042521
        assert out["title"] == "Ch 212 Vip Party Fever Edt Ladies 80Ml"

    def test_source_is_stamped(self):
        out = svc.parse_shopify_pdp_json(load_fixture("alhajisoman_com.json"))
        assert out["source"] == "shopify_pdp_json"


class TestParserRejects:
    @pytest.mark.parametrize(
        "bad",
        [
            "",
            "not json at all",
            "<!doctype html><html>404</html>",
            "[]",
            '{"products": []}',
            '{"variants": []}',
            '{"variants": "nope"}',
            None,
        ],
    )
    def test_non_product_payloads_return_none(self, bad):
        assert svc.parse_shopify_pdp_json(bad) is None

    def test_never_raises_on_garbage_variant_rows(self):
        payload = {
            "id": 1,
            "handle": "t",
            "available": True,
            "price": None,
            "variants": [{"price": "abc", "available": True}, "not-a-dict"],
        }
        assert svc.parse_shopify_pdp_json(payload) is None


# -------------------------------------------------------------------- the flag


class TestFeatureFlag:
    def test_default_is_off(self, monkeypatch):
        monkeypatch.delenv("ENABLE_SHOPIFY_PDP_JSON", raising=False)
        assert svc.shopify_pdp_json_enabled() is False

    @pytest.mark.parametrize("val", ["true", "1", "yes", "on", "TRUE", " On "])
    def test_truthy_values_turn_it_on(self, monkeypatch, val):
        monkeypatch.setenv("ENABLE_SHOPIFY_PDP_JSON", val)
        assert svc.shopify_pdp_json_enabled() is True

    @pytest.mark.parametrize("val", ["", "false", "0", "no", "off", "maybe"])
    def test_everything_else_stays_off(self, monkeypatch, val):
        monkeypatch.setenv("ENABLE_SHOPIFY_PDP_JSON", val)
        assert svc.shopify_pdp_json_enabled() is False

    def test_flag_is_read_per_call_never_cached_at_import(self, monkeypatch):
        monkeypatch.setenv("ENABLE_SHOPIFY_PDP_JSON", "true")
        assert svc.shopify_pdp_json_enabled() is True
        monkeypatch.setenv("ENABLE_SHOPIFY_PDP_JSON", "false")
        assert svc.shopify_pdp_json_enabled() is False

    @pytest.mark.asyncio
    async def test_flag_off_makes_no_network_call_at_all(self, monkeypatch):
        monkeypatch.delenv("ENABLE_SHOPIFY_PDP_JSON", raising=False)

        def _boom(url, timeout):
            raise AssertionError("network touched while the flag was OFF")

        monkeypatch.setattr(svc, "_curl_get", _boom)
        out = await svc.fetch_shopify_pdp_json(
            "https://bh.mubkhar.com/products/california-gold-home-perfume-oil-15ml"
        )
        assert out is None


# ------------------------------------------------------------------- the fetch


@pytest.mark.asyncio
class TestFetchHappyPath:
    async def test_fetches_the_dot_js_url_and_parses_it(self, monkeypatch, no_sleep):
        body = load_fixture("bh_mubkhar_com.json")
        calls = serve(monkeypatch, FakeResponse(200, body))
        out = await svc.fetch_shopify_pdp_json(
            "https://bh.mubkhar.com/products/california-gold-home-perfume-oil-15ml"
            "?variant=51199838028057"
        )
        assert calls == [
            "https://bh.mubkhar.com/products/california-gold-home-perfume-oil-15ml.js"
        ]
        assert out["price"] == 6.20
        assert out["in_stock"] is True

    async def test_result_carries_the_urls_and_domain(self, monkeypatch, no_sleep):
        serve(monkeypatch, FakeResponse(200, load_fixture("bh_mubkhar_com.json")))
        out = await svc.fetch_shopify_pdp_json(
            "https://bh.mubkhar.com/products/california-gold-home-perfume-oil-15ml"
        )
        assert out["domain"] == "bh.mubkhar.com"
        assert out["json_url"].endswith(".js")
        assert out["product_url"] == (
            "https://bh.mubkhar.com/products/california-gold-home-perfume-oil-15ml"
        )

    async def test_follows_a_same_site_redirect(self, monkeypatch, no_sleep):
        calls = serve(
            monkeypatch,
            FakeResponse(301, headers={"Location": "/products/moved.js"}),
            FakeResponse(200, load_fixture("bh_mubkhar_com.json")),
        )
        out = await svc.fetch_shopify_pdp_json("https://bh.mubkhar.com/products/x")
        assert calls[-1] == "https://bh.mubkhar.com/products/moved.js"
        assert out["price"] == 6.20


@pytest.mark.asyncio
class TestRetryAndStatusHandling:
    async def test_503_is_retried_once_and_succeeds(self, monkeypatch, no_sleep):
        calls = serve(
            monkeypatch,
            FakeResponse(503, "x" * 12194),
            FakeResponse(200, load_fixture("bh_mubkhar_com.json")),
        )
        out = await svc.fetch_shopify_pdp_json("https://bh.mubkhar.com/products/x")
        assert len(calls) == 2
        assert out["price"] == 6.20

    async def test_two_consecutive_503s_return_none(self, monkeypatch, no_sleep):
        calls = serve(
            monkeypatch, FakeResponse(503, "x" * 12194), FakeResponse(503, "x" * 12194)
        )
        out = await svc.fetch_shopify_pdp_json("https://bh.mubkhar.com/products/x")
        assert len(calls) == 2, "503 is retried exactly once, never twice"
        assert out is None

    async def test_the_503_retry_still_respects_domain_spacing(
        self, monkeypatch, no_sleep
    ):
        serve(monkeypatch, FakeResponse(503, ""), FakeResponse(503, ""))
        await svc.fetch_shopify_pdp_json("https://bh.mubkhar.com/products/x")
        # The wall clock advances a few microseconds between the two attempts, so
        # the reserved wait is a hair under the full window - hence 0.9x, not ==.
        assert any(
            s >= 0.9 * svc.MIN_DOMAIN_INTERVAL_S for s in no_sleep
        ), "the retry must wait out the per-domain window, not hammer the 503"

    @pytest.mark.parametrize("status", [400, 401, 403, 404, 429, 500, 502])
    async def test_other_non_200_statuses_are_not_retried(
        self, monkeypatch, no_sleep, status
    ):
        calls = serve(monkeypatch, FakeResponse(status, ""))
        out = await svc.fetch_shopify_pdp_json("https://bh.mubkhar.com/products/x")
        assert out is None
        assert len(calls) == 1

    async def test_html_error_page_with_200_returns_none(self, monkeypatch, no_sleep):
        serve(monkeypatch, FakeResponse(200, "<!doctype html><html>oops</html>"))
        out = await svc.fetch_shopify_pdp_json("https://bh.mubkhar.com/products/x")
        assert out is None

    async def test_transport_exception_returns_none(self, monkeypatch, no_sleep):
        def _raise(url, timeout):
            raise RuntimeError("connection reset")

        monkeypatch.setattr(svc, "_curl_get", _raise)
        out = await svc.fetch_shopify_pdp_json("https://bh.mubkhar.com/products/x")
        assert out is None

    async def test_unusable_pdp_url_short_circuits_before_any_request(
        self, monkeypatch, no_sleep
    ):
        def _boom(url, timeout):
            raise AssertionError("should not have fetched")

        monkeypatch.setattr(svc, "_curl_get", _boom)
        assert (
            await svc.fetch_shopify_pdp_json("ftp://bh.mubkhar.com/products/x") is None
        )


# ----------------------------------------------------------- per-domain spacing


class TestPerDomainSpacing:
    def test_first_call_on_a_domain_waits_nothing(self):
        assert svc.reserve_domain_slot("a.com", now=100.0) == 0.0

    def test_second_call_waits_out_the_window(self):
        svc.reserve_domain_slot("a.com", now=100.0)
        assert svc.reserve_domain_slot("a.com", now=100.0) == pytest.approx(
            svc.MIN_DOMAIN_INTERVAL_S
        )

    def test_reservations_stack_so_concurrent_callers_queue(self):
        svc.reserve_domain_slot("a.com", now=100.0)
        svc.reserve_domain_slot("a.com", now=100.0)
        assert svc.reserve_domain_slot("a.com", now=100.0) == pytest.approx(
            2 * svc.MIN_DOMAIN_INTERVAL_S
        )

    def test_a_caller_arriving_after_the_window_waits_nothing(self):
        svc.reserve_domain_slot("a.com", now=100.0)
        assert (
            svc.reserve_domain_slot("a.com", now=100.0 + svc.MIN_DOMAIN_INTERVAL_S)
            == 0.0
        )

    def test_spacing_is_per_domain_not_global(self):
        svc.reserve_domain_slot("a.com", now=100.0)
        assert svc.reserve_domain_slot("b.com", now=100.0) == 0.0

    def test_domain_key_is_case_and_www_insensitive(self):
        svc.reserve_domain_slot("WWW.A.com", now=100.0)
        assert svc.reserve_domain_slot("a.com", now=100.0) == pytest.approx(
            svc.MIN_DOMAIN_INTERVAL_S
        )

    def test_the_window_is_at_least_one_second(self):
        assert svc.MIN_DOMAIN_INTERVAL_S >= 1.0

    @pytest.mark.asyncio
    async def test_back_to_back_fetches_sleep_between_requests(
        self, monkeypatch, no_sleep
    ):
        body = load_fixture("bh_mubkhar_com.json")
        serve(monkeypatch, FakeResponse(200, body), FakeResponse(200, body))
        await svc.fetch_shopify_pdp_json("https://bh.mubkhar.com/products/x")
        await svc.fetch_shopify_pdp_json("https://bh.mubkhar.com/products/y")
        assert any(s >= 0.9 * svc.MIN_DOMAIN_INTERVAL_S for s in no_sleep)


# ------------------------------------------------------------------------ SSRF


@pytest.mark.asyncio
class TestSsrf:
    async def test_loopback_host_is_blocked_before_any_request(
        self, monkeypatch, no_sleep
    ):
        def _boom(url, timeout):
            raise AssertionError("SSRF: fetched a loopback address")

        monkeypatch.setattr(svc, "_curl_get", _boom)
        assert await svc.fetch_shopify_pdp_json("http://127.0.0.1/products/x") is None

    async def test_link_local_metadata_host_is_blocked(self, monkeypatch, no_sleep):
        def _boom(url, timeout):
            raise AssertionError("SSRF: fetched the cloud metadata endpoint")

        monkeypatch.setattr(svc, "_curl_get", _boom)
        assert (
            await svc.fetch_shopify_pdp_json("http://169.254.169.254/products/x") is None
        )

    async def test_offsite_redirect_is_refused(self, monkeypatch, no_sleep):
        calls = serve(
            monkeypatch,
            FakeResponse(302, headers={"Location": "http://127.0.0.1/products/x.js"}),
        )
        out = await svc.fetch_shopify_pdp_json("https://bh.mubkhar.com/products/x")
        assert out is None
        assert len(calls) == 1, "the off-domain hop must never be requested"

    async def test_cross_domain_redirect_is_refused(self, monkeypatch, no_sleep):
        calls = serve(
            monkeypatch,
            FakeResponse(
                302, headers={"Location": "https://evil.example/products/x.js"}
            ),
        )
        assert (
            await svc.fetch_shopify_pdp_json("https://bh.mubkhar.com/products/x") is None
        )
        assert len(calls) == 1

    async def test_subdomain_redirect_is_allowed(self, monkeypatch, no_sleep):
        serve(
            monkeypatch,
            FakeResponse(
                302, headers={"Location": "https://cdn.bh.mubkhar.com/products/x.js"}
            ),
            FakeResponse(200, load_fixture("bh_mubkhar_com.json")),
        )
        out = await svc.fetch_shopify_pdp_json("https://bh.mubkhar.com/products/x")
        assert out["price"] == 6.20

    async def test_redirect_loop_is_capped(self, monkeypatch, no_sleep):
        hops = [
            FakeResponse(302, headers={"Location": "/products/x.js"}) for _ in range(12)
        ]
        calls = serve(monkeypatch, *hops)
        out = await svc.fetch_shopify_pdp_json("https://bh.mubkhar.com/products/x")
        assert out is None
        assert len(calls) <= 6, "redirect chain must be capped, not followed forever"

    async def test_redirect_without_a_location_header_returns_none(
        self, monkeypatch, no_sleep
    ):
        serve(monkeypatch, FakeResponse(302, headers={}))
        assert (
            await svc.fetch_shopify_pdp_json("https://bh.mubkhar.com/products/x") is None
        )


# --------------------------------------------------------- no accidental wiring


class TestWiringStaysFlagGated:
    """ADJUDICATED at M10 UNIT A4, 2026-08-31 — this class replaces the STEP 5
    tripwire ``TestStillDormant::test_nothing_in_app_imports_this_module_yet``.

    That test asserted this module had ZERO call sites under ``app/``, and its
    own docstring named the condition for it to change: "if this test starts
    failing, that wiring landed without its own flag review." UNIT A4 landed the
    wiring WITH its flag review — ``ENABLE_UCP_JSON_PRICE``, default OFF,
    reviewed against the M9 `measure-ucp-free` evidence — so the tripwire fired
    for the reason it was built to allow, not for the reason it was built to
    catch.

    It is REPLACED rather than deleted, because "zero call sites" was only ever
    a proxy for the property that actually matters and that still holds: no call
    site may reach this module's network without a default-OFF flag in front of
    it. A deleted guard would have left that property untested."""

    def _importers(self):
        root = Path(__file__).resolve().parents[1] / "app"
        found = []
        for path in root.rglob("*.py"):
            if path.name == "shopify_pdp_service.py":
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            if "shopify_pdp_service" in text:
                found.append((path, text))
        return found

    def test_every_call_site_is_behind_a_default_off_flag(self):
        """The invariant the old tripwire was standing in for. Any module that
        reaches this one must consult a flag gate in the same file, so a fetch
        can never become reachable by import alone."""
        gates = ("ucp_json_price_enabled", "shopify_pdp_json_enabled")
        ungated = [
            str(path) for path, text in self._importers()
            if not any(gate in text for gate in gates)
        ]
        assert ungated == [], (
            "these modules reach shopify_pdp_service without consulting a flag "
            "gate: %s" % ungated
        )

    def test_the_only_wired_call_site_is_the_a4_cascade_shim(self):
        """Kept deliberately narrow. The point of the original tripwire was that
        a NEW call site is a decision someone must make on purpose; naming the
        one that exists preserves that, while a bare 'more than zero is fine'
        would throw the guard away."""
        wired = sorted(path.name for path, _ in self._importers())
        assert wired == ["price_service.py"]

    def test_both_flags_are_default_off(self, monkeypatch):
        """Neither gate may drift to default-ON without this file noticing —
        each adds a network round-trip per PDP on a throttle that answers a
        burst with 503."""
        for name in ("ENABLE_SHOPIFY_PDP_JSON", "ENABLE_UCP_JSON_PRICE"):
            monkeypatch.delenv(name, raising=False)
        assert svc.shopify_pdp_json_enabled() is False
        assert svc.ucp_json_price_enabled() is False
