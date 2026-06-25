"""Wave 3b (BH Source-Intelligence, 2026-06-23) — nasserpharmacy.com adapter.

nasserpharmacy.com exposes its OWN JSON search API
(newapi.nasserpharmacy.com /v1/filterSearchs) returning genuine native-BHD
prices in a SINGLE authenticated GET — NO Serper, NO render, NO second call.
`page=1` is REQUIRED (422 without). `currency_code=BHD` drives server FX.

`fetch_nasser_price(name, currency)` fires that GET, matches the query to
`products[].name`, prefers the LOWER of price/special (special != "0" = active
offer), rounds to 3 decimals (BHD fils), and stamps
`source_method="local_bhd"` (an EXISTING genuine method — no new set entry).

This suite drives the PURE matcher `_match_nasser_product(payload, ...)` against
a REAL recorded fixture (tests/fixtures/nasser_filterSearchs_cerave.json — 8 real
rows live-captured 2026-06-23 + 1 synthetic active-offer row) — NO network. The
network fetch (`fetch_nasser_price`) is covered with a monkeypatched curl_cffi so
it stays free-tier (no live calls): it asserts the request carries the static
guest headers + page=1 + currency_code=BHD, and that 401/non-200/empty → None.

LIVE-VERIFIED 2026-06-23 (out-of-band probe): "Cerave Foaming Cleanser" →
13.341 BHD, special="0", price_symbol="BHD", decimal_places=3 (the fixture row 0).
"""

import json
from pathlib import Path

import pytest

from app.services.price_service import (
    _match_nasser_product,
    _derive_nasser_in_stock,
    fetch_nasser_price,
    _NASSER_GUEST_HEADERS,
    _NASSER_SEARCH_URL,
)

FIXTURE = Path(__file__).parent / "fixtures" / "nasser_filterSearchs_cerave.json"


@pytest.fixture
def payload():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


# --- Pure matcher --------------------------------------------------------

class TestMatchNasserProduct:
    def test_matches_real_cerave_foaming_cleanser_genuine_bhd(self, payload):
        """The LIVE-VERIFIED case: 'Cerave Foaming Cleanser' → 13.341 BHD,
        genuine source_method=local_bhd (the row 0 captured live 2026-06-23)."""
        res = _match_nasser_product(payload, "Cerave Foaming Cleanser", "BHD")
        assert res is not None
        assert res["amount"] == pytest.approx(13.341)
        assert res["currency"] == "BHD"
        assert res["source_method"] == "local_bhd"
        assert res["retailer"] == "nasserpharmacy.com"
        assert res["estimated"] is False
        # the product_alias drives a real PDP url
        assert res["url"].startswith("https://www.nasserpharmacy.com/bh-en/")
        assert "cerave-foaming-cleanser" in res["url"]

    def test_prefers_lower_of_price_special_when_offer_active(self, payload):
        """When special != "0" (an active offer) the LOWER of price/special is
        picked: the synthetic offer row 19.500/special 14.250 → 14.250."""
        res = _match_nasser_product(payload, "Cerave Moisturising Cream 340g", "BHD")
        assert res is not None
        assert res["amount"] == pytest.approx(14.250)  # the special, not 19.5
        assert res["source_method"] == "local_bhd"

    def test_special_zero_keeps_regular_price(self, payload):
        """special == "0" is NOT an offer — the regular price stands (13.341,
        never coerced toward a phantom 0)."""
        res = _match_nasser_product(payload, "Cerave Foaming Cleanser", "BHD")
        assert res["amount"] == pytest.approx(13.341)

    def test_rounds_to_decimal_places_3_bhd_fils(self, payload):
        """decimal_places=3 → BHD fils precision retained (13.341, not 13.34)."""
        res = _match_nasser_product(payload, "Cerave Foaming Cleanser", "BHD")
        # 3-decimal genuine fils amount
        assert round(res["amount"], 3) == res["amount"]
        assert res["amount"] == pytest.approx(13.341)

    def test_no_match_returns_none(self, payload):
        """A query with no matching product → None (no fabricated price)."""
        res = _match_nasser_product(payload, "iPhone 15 Pro Max 256GB", "BHD")
        assert res is None

    def test_empty_or_malformed_payload_returns_none(self):
        assert _match_nasser_product(None, "Cerave", "BHD") is None
        assert _match_nasser_product({}, "Cerave", "BHD") is None
        assert _match_nasser_product({"products": []}, "Cerave", "BHD") is None
        assert _match_nasser_product({"products": "bad"}, "Cerave", "BHD") is None

    def test_non_bhd_price_symbol_skipped(self):
        """A product whose price_symbol is not BHD is skipped (no blind stamp)."""
        bad = {"products": [{
            "name": "Cerave Foaming Cleanser 473ml",
            "product_alias": "x", "price": "13.341", "special": "0",
            "price_symbol": "USD", "decimal_places": 2,
        }]}
        assert _match_nasser_product(bad, "Cerave Foaming Cleanser", "BHD") is None


# --- Network wrapper (monkeypatched curl_cffi — NO live network) ---------

class _FakeResp:
    def __init__(self, status_code, body):
        self.status_code = status_code
        self._body = body

    def json(self):
        return self._body


class TestFetchNasserPrice:
    @pytest.mark.asyncio
    async def test_sends_guest_headers_page1_and_currency(self, payload, monkeypatch):
        """The GET MUST carry the guest headers + page=1 + currency_code=BHD
        (page omitted → 422 live; currency drives server FX). The token now
        defaults to "" (fail-closed) so we provide one to activate the adapter."""
        captured = {}

        def fake_get(url, params=None, headers=None, **kwargs):
            captured["url"] = url
            captured["params"] = params
            captured["headers"] = headers
            return _FakeResp(200, payload)

        import curl_cffi.requests as cr
        import app.services.price_service as _ps
        monkeypatch.setattr(cr, "get", fake_get)
        # token defaults to "" (fail-closed) — supply a header so the adapter runs
        monkeypatch.setattr(
            _ps, "_NASSER_GUEST_HEADERS",
            {"Nasser": "TEST_TOKEN", "MOBILEOS": "REACT", "APPVERSION": "1"},
        )
        res = await fetch_nasser_price("Cerave Foaming Cleanser", "BHD")
        assert res is not None
        assert res["amount"] == pytest.approx(13.341)
        assert res["source_method"] == "local_bhd"
        # request shape
        assert captured["url"] == _NASSER_SEARCH_URL
        assert captured["params"]["page"] == 1          # REQUIRED
        assert captured["params"]["currency_code"] == "BHD"
        assert captured["params"]["search_term"] == "Cerave Foaming Cleanser"
        assert captured["headers"]["Nasser"] == "TEST_TOKEN"
        assert captured["headers"]["MOBILEOS"] == "REACT"
        assert captured["headers"]["APPVERSION"] == "1"

    @pytest.mark.asyncio
    async def test_http_401_token_rotated_returns_none(self, monkeypatch):
        """A rotated/expired guest token → HTTP 401 → None (verify-or-omit; the
        one live-credential risk fails cleanly, never a fabricated price)."""
        def fake_get(url, params=None, headers=None, **kwargs):
            return _FakeResp(401, {})
        import curl_cffi.requests as cr
        monkeypatch.setattr(cr, "get", fake_get)
        assert await fetch_nasser_price("Cerave Foaming Cleanser", "BHD") is None

    @pytest.mark.asyncio
    async def test_http_422_missing_page_returns_none(self, monkeypatch):
        def fake_get(url, params=None, headers=None, **kwargs):
            return _FakeResp(422, {})
        import curl_cffi.requests as cr
        monkeypatch.setattr(cr, "get", fake_get)
        assert await fetch_nasser_price("Cerave Foaming Cleanser", "BHD") is None

    @pytest.mark.asyncio
    async def test_empty_products_returns_none(self, monkeypatch):
        def fake_get(url, params=None, headers=None, **kwargs):
            return _FakeResp(200, {"products": []})
        import curl_cffi.requests as cr
        monkeypatch.setattr(cr, "get", fake_get)
        assert await fetch_nasser_price("Cerave Foaming Cleanser", "BHD") is None


# --- MED-2: env token override / kill switch / 401 circuit breaker -------
#
# These are the REGRESSION tests that FAIL without the MED-2/MED-3 fix:
#  * before MED-2 the guest token was hard-baked into _NASSER_GUEST_HEADERS,
#    there was no ENABLE_NASSER_ADAPTER kill switch, and no 401 breaker;
#  * before MED-3 _match_nasser_product hard-coded "in_stock": True.

import app.services.price_service as ps


class TestNasserGuestTokenEnvOverride:
    def test_token_is_env_driven_with_empty_default_no_literal(self):
        """MED-2 (Codex re-review): the guest token is read from the
        NASSER_GUEST_TOKEN env with an EMPTY default — no embedded credential in
        tracked source — and the request header is built from it (FAIL CLOSED: a
        fresh process with no env var obtains NO credential).

        Asserted WITHOUT importlib.reload: a mid-suite reload of price_service
        corrupts cross-module references (sitemap_discovery_service imports
        normalize_words/curl_fetch_html_same_site from it), which flaked the H5
        sitemap-SSRF tests in the combined suite. In the test env NASSER_GUEST_TOKEN
        is unset → the loaded token is "" (fail-closed)."""
        import os
        from pathlib import Path

        # env-driven with an EMPTY default → in the (token-free) test env it is "".
        assert ps._NASSER_GUEST_TOKEN == os.environ.get("NASSER_GUEST_TOKEN", "")
        assert ps._NASSER_GUEST_HEADERS["Nasser"] == ps._NASSER_GUEST_TOKEN
        # the source uses an EMPTY default + the burned recon literal is REMOVED.
        src = Path(ps.__file__).read_text(encoding="utf-8").replace("'", '"')
        assert 'os.environ.get("NASSER_GUEST_TOKEN", "")' in src
        assert "eyJ0b2tlbiI" not in src  # the old embedded token literal is gone

    @pytest.mark.asyncio
    async def test_no_env_token_makes_adapter_inert_no_network(self, monkeypatch):
        """MED-2 (Codex re-review): with an empty token the
        `if not _NASSER_GUEST_HEADERS.get("Nasser")` guard short-circuits to None
        WITHOUT a network call — nasser is DORMANT until NASSER_GUEST_TOKEN is set
        on Railway. Patch the header to "" (no module reload needed) + assert no
        curl is issued."""
        monkeypatch.setattr(ps, "ENABLE_NASSER_ADAPTER", True)
        monkeypatch.setattr(ps, "ENABLE_PAGE_SCRAPE", True)
        monkeypatch.setattr(
            ps, "_NASSER_GUEST_HEADERS",
            {"Nasser": "", "MOBILEOS": "REACT", "APPVERSION": "1"},
        )
        called = {"n": 0}

        def fake_get(*a, **k):
            called["n"] += 1
            return _FakeResp(200, {"products": []})

        import curl_cffi.requests as cr
        monkeypatch.setattr(cr, "get", fake_get)

        assert await ps.fetch_nasser_price("Cerave Foaming Cleanser", "BHD") is None
        assert called["n"] == 0  # inert — no network without a token

    def test_no_literal_token_default_remains_in_source(self):
        """MED-2 (Codex re-review): no 80+char base64-looking credential lingers
        as a literal DEFAULT in price_service source. The token must come ONLY
        from the env var (default ""). Grep-style guard over the module source."""
        import re
        from pathlib import Path

        src = Path(ps.__file__).read_text(encoding="utf-8")
        # any 70+ char unbroken base64-url run = a likely embedded credential
        suspects = re.findall(r'"[A-Za-z0-9_\-]{70,}"', src)
        assert suspects == [], (
            f"embedded credential-looking literal(s) found in source: {suspects!r}"
        )


class TestNasserKillSwitch:
    @pytest.mark.asyncio
    async def test_disabled_adapter_returns_none_without_network(self, monkeypatch):
        """MED-2(b): ENABLE_NASSER_ADAPTER=false → fetch_nasser_price returns
        None WITHOUT a network call."""
        called = {"n": 0}

        def fake_get(*a, **k):
            called["n"] += 1
            return _FakeResp(200, {"products": []})

        import curl_cffi.requests as cr
        monkeypatch.setattr(cr, "get", fake_get)
        monkeypatch.setattr(ps, "ENABLE_NASSER_ADAPTER", False)

        assert await ps.fetch_nasser_price("Cerave Foaming Cleanser", "BHD") is None
        assert called["n"] == 0  # NO network call when killed


class TestNasser401CircuitBreaker:
    @pytest.mark.asyncio
    async def test_three_401s_short_circuit_fourth_without_network(self, monkeypatch):
        """MED-2(c): 3 consecutive 401s trip the breaker → the 4th call short-
        circuits to None WITHOUT hitting curl. Redis is mocked (no live network)."""
        # Make sure the kill switch + page-scrape gates are open for this test,
        # and supply a token (default is now "" — fail-closed).
        monkeypatch.setattr(ps, "ENABLE_NASSER_ADAPTER", True)
        monkeypatch.setattr(ps, "ENABLE_PAGE_SCRAPE", True)
        monkeypatch.setattr(
            ps, "_NASSER_GUEST_HEADERS",
            {"Nasser": "TEST_TOKEN", "MOBILEOS": "REACT", "APPVERSION": "1"},
        )

        # In-memory fake Redis counter (the breaker reads/writes via cache_service).
        store = {}
        import app.services.cache_service as cs

        def fake_incr(key):
            store[key] = int(store.get(key, 0)) + 1
            return store[key]

        def fake_get(key):
            v = store.get(key)
            return None if v is None else str(v)

        def fake_expire(key, seconds):
            return True

        monkeypatch.setattr(cs, "_redis_incr", fake_incr, raising=False)
        monkeypatch.setattr(cs, "_redis_get", fake_get, raising=False)
        monkeypatch.setattr(cs, "_redis_expire", fake_expire, raising=False)
        # reset() deletes via redis_client.delete — keep a no-op client that does NOT
        # clear on a 401 path (we never get a 200 here).
        class _FakeRedis:
            def delete(self, *keys):
                for k in keys:
                    store.pop(k, None)
        monkeypatch.setattr(cs, "redis_client", _FakeRedis(), raising=False)

        curl_calls = {"n": 0}

        def fake_curl_get(url, params=None, headers=None, **kwargs):
            curl_calls["n"] += 1
            return _FakeResp(401, {})

        import curl_cffi.requests as cr
        monkeypatch.setattr(cr, "get", fake_curl_get)

        # 3 calls each return 401 and increment the breaker counter (3 curl hits).
        for _ in range(3):
            assert await ps.fetch_nasser_price("Cerave Foaming Cleanser", "BHD") is None
        assert curl_calls["n"] == 3

        # 4th call: breaker tripped → short-circuit to None, NO 4th curl hit.
        assert await ps.fetch_nasser_price("Cerave Foaming Cleanser", "BHD") is None
        assert curl_calls["n"] == 3  # unchanged — no network on the 4th

    @pytest.mark.asyncio
    async def test_200_resets_the_401_streak(self, payload, monkeypatch):
        """A live 200 clears the consecutive-401 counter (token alive again)."""
        monkeypatch.setattr(ps, "ENABLE_NASSER_ADAPTER", True)
        monkeypatch.setattr(ps, "ENABLE_PAGE_SCRAPE", True)
        monkeypatch.setattr(
            ps, "_NASSER_GUEST_HEADERS",
            {"Nasser": "TEST_TOKEN", "MOBILEOS": "REACT", "APPVERSION": "1"},
        )

        store = {ps._NASSER_401_KEY: 2}  # a pre-existing streak (below threshold)
        import app.services.cache_service as cs

        def fake_get(key):
            v = store.get(key)
            return None if v is None else str(v)

        class _FakeRedis:
            def delete(self, *keys):
                for k in keys:
                    store.pop(k, None)

        monkeypatch.setattr(cs, "_redis_get", fake_get, raising=False)
        monkeypatch.setattr(cs, "_redis_incr", lambda k: store.get(k, 0), raising=False)
        monkeypatch.setattr(cs, "_redis_expire", lambda k, s: True, raising=False)
        monkeypatch.setattr(cs, "redis_client", _FakeRedis(), raising=False)

        def fake_curl_get(url, params=None, headers=None, **kwargs):
            return _FakeResp(200, payload)

        import curl_cffi.requests as cr
        monkeypatch.setattr(cr, "get", fake_curl_get)

        res = await ps.fetch_nasser_price("Cerave Foaming Cleanser", "BHD")
        assert res is not None
        assert res["amount"] == pytest.approx(13.341)
        # the 200 cleared the streak counter
        assert ps._NASSER_401_KEY not in store


# --- MED-3: in_stock derived from the real stock signal ------------------

class TestNasserInStockDerivation:
    def _row(self, **extra):
        row = {
            "name": "Cerave Foaming Cleanser 473ml",
            "product_alias": "cerave-foaming-cleanser",
            "price": "13.341", "special": "0",
            "price_symbol": "BHD", "decimal_places": 3,
        }
        row.update(extra)
        return {"products": [row]}

    def test_stock_count_zero_is_out_of_stock(self):
        """MED-3: stock_count=0 → in_stock False (was hard-coded True before)."""
        res = _match_nasser_product(
            self._row(stock_count=0), "Cerave Foaming Cleanser", "BHD",
        )
        assert res is not None
        assert res["in_stock"] is False

    def test_stock_count_99_is_in_stock(self):
        """MED-3: stock_count=99 → in_stock True (derived from the real int)."""
        res = _match_nasser_product(
            self._row(stock_count=99), "Cerave Foaming Cleanser", "BHD",
        )
        assert res is not None
        assert res["in_stock"] is True

    def test_stock_text_out_of_stock_marker_is_false(self):
        """MED-3: stock_text 'Out of Stock' (no numeric count) → in_stock False."""
        res = _match_nasser_product(
            self._row(stock_text="Out of Stock"), "Cerave Foaming Cleanser", "BHD",
        )
        assert res is not None
        assert res["in_stock"] is False

    def test_stock_text_many_in_stock_is_true(self):
        """MED-3: a non-OOS stock_text ('Many in Stock') → in_stock True."""
        res = _match_nasser_product(
            self._row(stock_text="Many in Stock"), "Cerave Foaming Cleanser", "BHD",
        )
        assert res is not None
        assert res["in_stock"] is True

    def test_no_stock_signal_omits_in_stock(self):
        """MED-3 re-review: no stock_count and no stock_text → the matched price
        dict carries NO ``in_stock`` key (was an optimistic hard-coded True). We
        omit rather than fabricate availability we can't verify — and we MUST NOT
        claim a falsy value downstream reads as out-of-stock either."""
        res = _match_nasser_product(
            self._row(), "Cerave Foaming Cleanser", "BHD",
        )
        assert res is not None
        # the key is absent entirely (no fabrication in either direction)
        assert "in_stock" not in res
        # and the .get-style read downstream uses never resolves to a hard False
        assert res.get("in_stock") is not False

    def test_derive_no_signal_returns_none(self):
        """MED-3 re-review (unit): _derive_nasser_in_stock with no stock signal at
        all → None (not the old optimistic True)."""
        assert _derive_nasser_in_stock({}) is None
        # an empty/whitespace stock_text is also no signal
        assert _derive_nasser_in_stock({"stock_text": "   "}) is None
        # a non-numeric, non-OOS stock_count string is no usable signal
        assert _derive_nasser_in_stock({"stock_count": None}) is None

    def test_derive_real_signals_still_resolve(self):
        """MED-3 re-review: the real-signal paths are UNCHANGED — only the
        no-signal default flipped from True to None."""
        assert _derive_nasser_in_stock({"stock_count": 0}) is False
        assert _derive_nasser_in_stock({"stock_count": 99}) is True
        assert _derive_nasser_in_stock({"stock_count": 0.0}) is False
        assert _derive_nasser_in_stock({"stock_text": "Out of Stock"}) is False
        assert _derive_nasser_in_stock({"stock_text": "Many in Stock"}) is True
