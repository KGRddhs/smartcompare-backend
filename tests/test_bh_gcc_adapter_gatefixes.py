"""Wave-B adversarial-review gate-fixes — pin the two KPI-corruption traps so
they cannot silently regress.

Both are the #1 risk the BUILD SPEC §3.0 calls out: a CONVERTED (non-BHD) price
banked as a GENUINE BHD price (7d TTL, showable, no-negcache, counted in the
genuine-share KPI). The fixes require the genuine stamp to be gated on the
RESPONSE's actual currency == BHD, never on the caller-supplied currency arg or a
missing-currency default.
"""
import pytest

import app.services.salla_service as salla
import app.services.rest_json_service as rj


# ---------------------------------------------------------------------------
# salla — a hit with NO/empty currency must NOT default to genuine BHD
# ---------------------------------------------------------------------------

class _Resp:
    def __init__(self, status_code=200, text="", json_obj=None):
        self.status_code = status_code
        self._text = text
        self._json = json_obj

    @property
    def text(self):
        return self._text

    def json(self):
        return self._json if self._json is not None else {}


@pytest.fixture(autouse=True)
def _enable(monkeypatch):
    monkeypatch.setattr(salla, "ENABLE_PAGE_SCRAPE", True, raising=False)
    salla._STORE_ID_CACHE.clear()


def test_salla_missing_currency_is_omitted_not_genuine(monkeypatch):
    # Storefront HTML carries a store id; the API hit MATCHES the query but omits
    # `currency`. Before the fix this banked 440 as "440 BHD genuine salla_api".
    storefront = '<script>{"store":{"id":999111}}</script>'
    api = {"data": [{"name": "Acme Widget XYZ", "price": 440,
                     "url": "https://store.example/p/x"}]}  # NO currency key

    def fake_get(url, *a, **k):
        if "api.salla.dev" in url:
            return _Resp(200, json_obj=api)
        return _Resp(200, text=storefront)

    import curl_cffi.requests as curl_requests
    monkeypatch.setattr(curl_requests, "get", fake_get, raising=True)

    import asyncio
    out = asyncio.get_event_loop().run_until_complete(
        salla.fetch_salla_api_price("store.example", "Acme Widget XYZ")
    )
    assert out is None, "a hit with no currency must be omitted, never genuine-BHD"


def test_salla_explicit_bhd_still_genuine(monkeypatch):
    storefront = '<script>{"store":{"id":999111}}</script>'
    api = {"data": [{"name": "Acme Widget XYZ", "price": 12.5, "currency": "BHD",
                     "url": "https://store.example/p/x", "is_out_of_stock": False}]}

    def fake_get(url, *a, **k):
        if "api.salla.dev" in url:
            return _Resp(200, json_obj=api)
        return _Resp(200, text=storefront)

    import curl_cffi.requests as curl_requests
    monkeypatch.setattr(curl_requests, "get", fake_get, raising=True)
    import asyncio
    out = asyncio.get_event_loop().run_until_complete(
        salla.fetch_salla_api_price("store.example", "Acme Widget XYZ")
    )
    assert out is not None and out["source_method"] == "salla_api"
    assert out["currency"] == "BHD" and out["amount"] == pytest.approx(12.5)


# ---------------------------------------------------------------------------
# rest_json — genuine stamp requires RESPONSE currency == BHD, not caller match
# ---------------------------------------------------------------------------

def test_restjson_caller_currency_cannot_force_genuine():
    # Wave-C passes the Source row's real currency (a panda row = "SAR"). A SAR
    # response with target "SAR" must NOT stamp genuine — it converts.
    out = rj._stamp_genuine_or_converted(100.0, "SAR", "SAR")
    assert out is not None
    assert out["source_method"] == "converted_usd"
    assert out["source_method"] != rj._GENUINE_METHOD
    assert out.get("original_currency") == "SAR"


def test_restjson_bhd_response_is_genuine():
    out = rj._stamp_genuine_or_converted(10.0, "BHD", "SAR")
    assert out is not None
    assert out["source_method"] == rj._GENUINE_METHOD
    assert out["currency"] == "BHD"
