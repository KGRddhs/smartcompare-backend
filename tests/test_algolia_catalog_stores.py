"""R3c — Algolia EXPLICIT-KEY catalog-store path (sharafdg BH/UAE, danube, nahdi).

These stores do NOT expose their appId via the DSN-preconnect harvest path, so
``fetch_algolia_price`` carries a per-store pinned config (appId + searchKey +
index + currency + genuine flag) in ``ALGOLIA_STORES``. This suite covers the
NEW multi-shape price parser + the genuine(BHD)-vs-converted(GCC) stamping +
the strict-match no-fab gate + the oman.sharafdg price=0 OMIT.

All HTTP mocked off the captured fixtures (offline-deterministic). The existing
6thStreet harvest path lives in test_algolia_service.py and is untouched.
"""
import json
import os
from pathlib import Path

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

_FX = Path(__file__).parent / "fixtures" / "bh_gcc"


def _load(name):
    return json.loads((_FX / f"{name}.json").read_text(encoding="utf-8"))


def _mock_post(hits_payload):
    """Build a curl_cffi.requests.post replacement returning a 200 with the
    given Algolia response body (a dict already shaped {hits: [...]})."""
    resp = MagicMock()
    resp.status_code = 200
    resp.json = MagicMock(return_value=hits_payload)
    resp.text = json.dumps(hits_payload)
    return MagicMock(return_value=resp)


@pytest.fixture(autouse=True)
def _no_live_cache():
    # Review gate-fix: ALSO patch is_circuit_closed True. conftest.py does
    # load_dotenv(override=True) → live prod Upstash Redis, where the 'algolia'
    # circuit may be OPEN, making fetch_algolia_price short-circuit to None and
    # the orchestrator tests RED on a non-code defect. (Mirrors the unbxd suite's
    # _circuit_closed fixture.) Offline-deterministic regardless of prod state.
    with patch("app.services.algolia_service.get_cached", return_value=None), \
         patch("app.services.algolia_service.set_cached", return_value=True), \
         patch("app.services.algolia_service.is_circuit_closed", return_value=True):
        yield


# ---------------------------------------------------------------------------
# Multi-shape parser
# ---------------------------------------------------------------------------

def test_multishape_flat_float_sharafdg():
    import app.services.algolia_service as alg
    hit = _load("algolia_sharafdg_bh")["hits"][0]
    # sharafdg: hit['price'] is a flat float (239.99); CUR=BHD.
    assert alg._parse_algolia_price_multishape(hit, "BHD") == pytest.approx(239.99)


def test_multishape_nested_nahdi_sar():
    import app.services.algolia_service as alg
    hit = _load("algolia_nahdi")["hits"][0]
    # nahdi: hit['price']['SAR']['default'] == 10.9
    assert alg._parse_algolia_price_multishape(hit, "SAR") == pytest.approx(10.9)


def test_multishape_flat_float_danube():
    import app.services.algolia_service as alg
    hit = _load("algolia_danube")["hits"][0]
    assert alg._parse_algolia_price_multishape(hit, "SAR") == pytest.approx(24.0)


def test_multishape_keeps_6thstreet_list_shape():
    """Back-compat: the existing 6thStreet list shape still parses (CUR=BHD)."""
    import app.services.algolia_service as alg
    hit = {"price": [{"BHD": {"default": 21.0}}]}
    assert alg._parse_algolia_price_multishape(hit, "BHD") == pytest.approx(21.0)


def test_multishape_zero_and_garbage_return_none():
    import app.services.algolia_service as alg
    assert alg._parse_algolia_price_multishape({"price": 0}, "BHD") is None
    assert alg._parse_algolia_price_multishape({"price": None}, "BHD") is None
    assert alg._parse_algolia_price_multishape({}, "BHD") is None
    assert alg._parse_algolia_price_multishape({"price": "abc"}, "BHD") is None
    # nested but missing the pinned currency
    assert alg._parse_algolia_price_multishape(
        {"price": {"USD": {"default": 9}}}, "SAR") is None


def test_legacy_parse_algolia_price_untouched():
    """The original list-shape-only parser the existing suite pins must still
    behave identically (6thStreet back-compat)."""
    import app.services.algolia_service as alg
    assert alg._parse_algolia_price({"price": [{"BHD": {"default": 21.0}}]}) == 21.0
    assert alg._parse_algolia_price({"price": 239.99}) is None  # list-only


# ---------------------------------------------------------------------------
# Genuine BHD path — bahrain.sharafdg
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_sharafdg_bh_genuine_local_bhd():
    import app.services.algolia_service as alg
    payload = _load("algolia_sharafdg_bh")
    with patch("curl_cffi.requests.post", _mock_post(payload)):
        out = await alg.fetch_algolia_price(
            "bahrain.sharafdg.com", "Apple iPhone 15 128GB", "electronics")
    assert out is not None
    assert out["currency"] == "BHD"
    assert out["source_method"] == "local_bhd"
    assert out["estimated"] is False
    assert out["amount"] == pytest.approx(239.99)
    assert "original_currency" not in out
    assert out["retailer"] == "bahrain.sharafdg.com"
    assert out["url"].startswith("https://bahrain.sharafdg.com/")
    assert out["in_stock"] is True
    assert 0.7 <= out["confidence"] <= 0.95


# ---------------------------------------------------------------------------
# Converted GCC path — uae.sharafdg (AED) + danube (SAR)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_sharafdg_uae_converted_usd():
    import app.services.algolia_service as alg
    payload = _load("algolia_sharafdg_uae")
    with patch("curl_cffi.requests.post", _mock_post(payload)):
        out = await alg.fetch_algolia_price(
            "uae.sharafdg.com", "Apple iPhone 15 128GB", "electronics")
    assert out is not None
    assert out["currency"] == "BHD"
    assert out["source_method"] == "converted_usd"  # LITERAL, not a per-platform string
    assert out["original_currency"] == "AED"
    # 2335 AED * 0.1024 = 239.104 BHD
    assert out["amount"] == pytest.approx(2335 * 0.1024, abs=0.01)
    assert out["estimated"] is False


@pytest.mark.asyncio
async def test_danube_converted_sar_and_relative_url():
    import app.services.algolia_service as alg
    payload = _load("algolia_danube")
    captured = {}

    def _post(*a, **k):
        captured["data"] = k.get("data")
        resp = MagicMock()
        resp.status_code = 200
        resp.json = MagicMock(return_value=payload)
        resp.text = json.dumps(payload)
        return resp

    with patch("curl_cffi.requests.post", side_effect=_post):
        out = await alg.fetch_algolia_price("danube.sa", "Milka Daim Snax 145g", "grocery")
    assert out is not None
    assert out["currency"] == "BHD"
    assert out["source_method"] == "converted_usd"
    assert out["original_currency"] == "SAR"
    assert out["amount"] == pytest.approx(24.0 * 0.1003, abs=0.01)
    # RELATIVE url_en -> prepended host
    assert out["url"] == "https://danube.sa/en/products/milka-daim-snax-145g"
    # danube requires the tenant_id filter in the request body
    assert captured["data"] is not None
    assert "tenant_id" in captured["data"]


@pytest.mark.asyncio
async def test_nahdi_converted_sar_nested_price():
    import app.services.algolia_service as alg
    payload = _load("algolia_nahdi")
    with patch("curl_cffi.requests.post", _mock_post(payload)):
        out = await alg.fetch_algolia_price("nahdionline.com", "Adol-Sinus 24 Caplets", "supplements")
    assert out is not None
    assert out["currency"] == "BHD"
    assert out["source_method"] == "converted_usd"
    assert out["original_currency"] == "SAR"
    assert out["amount"] == pytest.approx(10.9 * 0.1003, abs=0.01)


# ---------------------------------------------------------------------------
# OMIT / no-fab / error paths
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_oman_sharafdg_price_zero_returns_none():
    """oman.sharafdg systematically prices 0.000 -> every hit must yield None."""
    import app.services.algolia_service as alg
    payload = _load("algolia_sharafdg_oman")
    with patch("curl_cffi.requests.post", _mock_post(payload)):
        out = await alg.fetch_algolia_price(
            "oman.sharafdg.com", "iPhone SE", "electronics")
    assert out is None


@pytest.mark.asyncio
async def test_wrong_brand_no_fab_returns_none():
    """A real sharafdg iPhone payload queried for an unrelated product must NOT
    ship a wrong-brand price (strict_title_match rejects)."""
    import app.services.algolia_service as alg
    payload = _load("algolia_sharafdg_bh")
    with patch("curl_cffi.requests.post", _mock_post(payload)):
        out = await alg.fetch_algolia_price(
            "bahrain.sharafdg.com", "Samsung Galaxy Watch Ultra", "electronics")
    assert out is None


@pytest.mark.asyncio
async def test_non_200_returns_none_never_raises():
    import app.services.algolia_service as alg
    resp = MagicMock()
    resp.status_code = 503
    resp.json = MagicMock(side_effect=ValueError("no json"))
    resp.text = "upstream error"
    with patch("curl_cffi.requests.post", MagicMock(return_value=resp)):
        out = await alg.fetch_algolia_price(
            "bahrain.sharafdg.com", "Apple iPhone 15", "electronics")
    assert out is None


@pytest.mark.asyncio
async def test_garbage_body_returns_none_never_raises():
    import app.services.algolia_service as alg
    resp = MagicMock()
    resp.status_code = 200
    resp.json = MagicMock(side_effect=ValueError("not json"))
    resp.text = "<<garbage>>"
    with patch("curl_cffi.requests.post", MagicMock(return_value=resp)):
        out = await alg.fetch_algolia_price(
            "bahrain.sharafdg.com", "Apple iPhone 15", "electronics")
    assert out is None


@pytest.mark.asyncio
async def test_disabled_by_flag(monkeypatch):
    import app.services.algolia_service as alg
    monkeypatch.setattr(alg, "ENABLE_PAGE_SCRAPE", False)
    post = MagicMock()
    with patch("curl_cffi.requests.post", post):
        out = await alg.fetch_algolia_price(
            "bahrain.sharafdg.com", "Apple iPhone 15", "electronics")
    assert out is None
    post.assert_not_called()
