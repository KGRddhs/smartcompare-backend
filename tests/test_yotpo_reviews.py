"""UNIT B6 — Yotpo review + ratings adapter (ENABLE_YOTPO_REVIEWS, default OFF).

MEASURED (research/B6/adapter_yotpo.json): Yotpo's PUBLIC read endpoint
``GET https://api-cdn.yotpo.com/v1/widget/{app_key}/products/{product_id}/reviews.json?per_page=150``
returns full review text + score + title + verified_buyer + PRE-COMPUTED sentiment
+ language in ONE unauthenticated call. Yotpo robots ALLOWS exactly this path.

Offline — NO network. The Yotpo endpoints are mocked at the ``curl_cffi.requests.get``
seam (the same seam the salla/magento adapter tests use); the PDP HTML + JSON
response shapes come from cached fixtures.

Pins (the B6 HARD RULES):
  (a) app_key extraction from all three PDP patterns (cdn-widgetsrepository
      loader / data-appkey / staticw2 widget.js); the 40-char [A-Za-z0-9] gate
      REJECTS the 32-hex decoy; the bare 'yotpo' substring is NOT an install;
  (b) product_id extraction (Shopify numeric id / non-Shopify data-product-id);
  (c) the hard ALLOWLIST of robots-allowed paths admits the reviews/site/bottomline
      URLs and REJECTS an arbitrary Yotpo path (never a denylist);
  (d) flag-OFF: fetch returns None and NEVER issues a network call;
  (e) flag-ON end-to-end: a valid install resolves real reviews + aggregate rating,
      with the pre-computed sentiment/language carried (replacing the LLM pass);
  (f) total_review==0 fires exactly ONE yotpo_site_reviews liveness call and
      classifies bad-key (dead) vs empty-product (live);
  (g) ratings-only bottomline endpoint.
"""

import asyncio
import json
import os

import pytest

import app.services.yotpo_service as yotpo

FIX = os.path.join(os.path.dirname(__file__), "fixtures", "yotpo_b6")

SHOP_KEY = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJ0123"
SHOP_PID = "8096434946323"
BT_KEY = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghij0123"
BT_PID = "2000055407"
STATICW2_KEY = "0123456789abcdefghijklmnopqrstuvwxyzABCD"
DECOY_32HEX = "e51a4e2686c9072bb405bf25837fe8f7"


def _read(name: str) -> str:
    with open(os.path.join(FIX, name), encoding="utf-8") as fh:
        return fh.read()


SHOPIFY_PDP = _read("shopify_demeter_yotpo_pdp.html")
NONSHOPIFY_PDP = _read("non_shopify_brownthomas_yotpo_pdp.html")
STATICW2_PDP = _read("staticw2_widgetjs_yotpo_pdp.html")
DECOY_PDP = _read("decoy_32hex_key_stock_snippet.html")
CONTROL_PDP = _read("no_yotpo_install_control.html")

REVIEWS_DEMETER = json.loads(_read("reviews_demeter.json"))
REVIEWS_ZERO = json.loads(_read("reviews_zero.json"))
SITE_LIVE = json.loads(_read("site_reviews_live.json"))
SITE_DEAD = json.loads(_read("site_reviews_dead.json"))
BOTTOMLINE = json.loads(_read("bottomline_demeter.json"))


def _run(coro):
    return asyncio.run(coro)


class _FakeResp:
    def __init__(self, status_code=200, json_obj=None, text=""):
        self.status_code = status_code
        self._json = json_obj
        self.text = text

    def json(self):
        if self._json is not None:
            return self._json
        return json.loads(self.text)


@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    # Default: flag OFF (each test opts in).
    monkeypatch.delenv("ENABLE_YOTPO_REVIEWS", raising=False)


def _route(monkeypatch, mapping, default=None):
    """Patch curl_cffi.requests.get to route by URL substring. Records calls."""
    calls = []

    def fake_get(url, *args, **kwargs):
        calls.append(url)
        for needle, resp in mapping.items():
            if needle in url:
                return resp
        if default is not None:
            return default
        return _FakeResp(404, json_obj={"status": {"code": 404}})

    import curl_cffi.requests as curl_requests
    monkeypatch.setattr(curl_requests, "get", fake_get, raising=True)
    return calls


# ---------------------------------------------------------------------------
# (a) app_key extraction + the 40-char gate + bare-'yotpo' rejection
# ---------------------------------------------------------------------------

def test_app_key_from_cdn_widgetsrepository_loader():
    assert yotpo.extract_yotpo_app_key(SHOPIFY_PDP) == SHOP_KEY


def test_app_key_from_data_appkey_attribute():
    assert yotpo.extract_yotpo_app_key(NONSHOPIFY_PDP) == BT_KEY


def test_app_key_from_staticw2_widgetjs():
    assert yotpo.extract_yotpo_app_key(STATICW2_PDP) == STATICW2_KEY


def test_32hex_decoy_key_is_rejected():
    # The 32-hex boilerplate must NOT be accepted (it 404s 'Account not found').
    assert yotpo.extract_yotpo_app_key(DECOY_PDP) is None
    assert yotpo._is_valid_app_key(DECOY_32HEX) is False
    assert yotpo._is_valid_app_key(SHOP_KEY) is True


def test_bare_yotpo_substring_is_not_an_install():
    # A page carrying only the stock MetafieldYotpoRating snippet has no install.
    assert yotpo.extract_yotpo_install(DECOY_PDP) is None
    assert yotpo.extract_yotpo_install(CONTROL_PDP) is None


def test_app_key_rejects_wrong_length_and_nonalnum():
    assert yotpo._is_valid_app_key("short") is False
    assert yotpo._is_valid_app_key("a" * 41) is False
    assert yotpo._is_valid_app_key("a" * 39) is False
    # 40 chars but contains a non-alphanumeric char.
    assert yotpo._is_valid_app_key("a" * 39 + "-") is False


# ---------------------------------------------------------------------------
# (b) product_id extraction
# ---------------------------------------------------------------------------

def test_product_id_shopify_numeric():
    assert yotpo.extract_yotpo_product_id(SHOPIFY_PDP) == SHOP_PID


def test_product_id_non_shopify_div():
    assert yotpo.extract_yotpo_product_id(NONSHOPIFY_PDP) == BT_PID


def test_install_returns_key_and_id():
    assert yotpo.extract_yotpo_install(SHOPIFY_PDP) == (SHOP_KEY, SHOP_PID)
    assert yotpo.extract_yotpo_install(NONSHOPIFY_PDP) == (BT_KEY, BT_PID)


# ---------------------------------------------------------------------------
# (c) the hard ALLOWLIST of robots-allowed paths
# ---------------------------------------------------------------------------

def test_allowlist_admits_the_read_paths():
    assert yotpo.robots_allows_path(
        f"/v1/widget/{SHOP_KEY}/products/{SHOP_PID}/reviews.json")
    assert yotpo.robots_allows_path(
        f"/v1/widget/{SHOP_KEY}/products/yotpo_site_reviews/reviews.json")
    assert yotpo.robots_allows_path(
        f"/products/{SHOP_KEY}/{SHOP_PID}/bottomline")


def test_allowlist_rejects_arbitrary_and_disallowed_paths():
    # A path outside the explicit Allow set is rejected (allowlist, not denylist).
    assert yotpo.robots_allows_path("/") is False
    assert yotpo.robots_allows_path("/account/settings") is False
    assert yotpo.robots_allows_path("/v1/private/dump") is False
    assert yotpo.robots_allows_path("/products/x/y/delete") is False


def test_get_json_refuses_a_non_allowlisted_url(monkeypatch):
    calls = _route(monkeypatch, {}, default=_FakeResp(200, json_obj={"ok": True}))
    # A URL whose path is not on the allowlist must NOT be fetched.
    res = _run(yotpo._yotpo_get_json("https://api-cdn.yotpo.com/account/settings"))
    assert res is None
    assert calls == []  # never issued the request


# ---------------------------------------------------------------------------
# (d) flag-OFF — never fetches
# ---------------------------------------------------------------------------

def test_flag_off_returns_none_and_never_fetches(monkeypatch):
    calls = _route(monkeypatch, {"reviews.json": _FakeResp(200, json_obj=REVIEWS_DEMETER)})
    res = _run(yotpo.fetch_yotpo_reviews(SHOPIFY_PDP, url="https://demeterfragrance.com/products/pumpkin-pie"))
    assert res is None
    assert calls == []


def test_enabled_helper_reads_env_per_call(monkeypatch):
    monkeypatch.delenv("ENABLE_YOTPO_REVIEWS", raising=False)
    assert yotpo.yotpo_reviews_enabled() is False
    monkeypatch.setenv("ENABLE_YOTPO_REVIEWS", "true")
    assert yotpo.yotpo_reviews_enabled() is True
    monkeypatch.setenv("ENABLE_YOTPO_REVIEWS", "off")
    assert yotpo.yotpo_reviews_enabled() is False


# ---------------------------------------------------------------------------
# (e) flag-ON end-to-end — real reviews + aggregate rating + pre-computed sentiment
# ---------------------------------------------------------------------------

def test_flag_on_resolves_reviews_and_rating(monkeypatch):
    monkeypatch.setenv("ENABLE_YOTPO_REVIEWS", "true")
    calls = _route(monkeypatch, {
        f"/products/{SHOP_PID}/reviews.json": _FakeResp(200, json_obj=REVIEWS_DEMETER),
    })
    res = _run(yotpo.fetch_yotpo_reviews(SHOPIFY_PDP, url="https://demeterfragrance.com/x"))
    assert res is not None
    assert res["source"] == "yotpo"
    assert res["app_key"] == SHOP_KEY
    assert res["product_id"] == SHOP_PID
    # aggregate rating is the PRIMARY target
    assert res["rating"]["total_reviews"] == 3
    assert res["rating"]["average_score"] == pytest.approx(4.67)
    assert res["rating"]["star_distribution"]["5"] == 2
    # real review bodies + PRE-COMPUTED sentiment/language (replaces LLM pass)
    assert len(res["reviews"]) == 3
    first = res["reviews"][0]
    assert "real thing" in first["title"]
    assert "gourmand" in first["content"]
    assert first["score"] == 5
    assert first["sentiment"] == pytest.approx(0.97)
    assert first["language"] == "en"
    assert first["verified_buyer"] is True
    assert res["sentiment_source"] == "yotpo_precomputed"
    assert res["llm_sentiment_required"] is False
    # exactly one request — the product reviews call (no liveness needed).
    assert len(calls) == 1
    assert "reviews.json" in calls[0]
    # the URL relied on the robots-allowed /v1/widget/* path + per_page cap.
    assert "/v1/widget/" in calls[0]
    assert "per_page=150" in calls[0]


def test_flag_on_language_preserved_for_arabic_review(monkeypatch):
    monkeypatch.setenv("ENABLE_YOTPO_REVIEWS", "true")
    _route(monkeypatch, {
        f"/products/{SHOP_PID}/reviews.json": _FakeResp(200, json_obj=REVIEWS_DEMETER),
    })
    res = _run(yotpo.fetch_yotpo_reviews(SHOPIFY_PDP, url="https://demeterfragrance.com/x"))
    ar = [r for r in res["reviews"] if r["language"] == "ar"]
    assert len(ar) == 1


def test_no_install_returns_none_without_fetch(monkeypatch):
    monkeypatch.setenv("ENABLE_YOTPO_REVIEWS", "true")
    calls = _route(monkeypatch, {"reviews.json": _FakeResp(200, json_obj=REVIEWS_DEMETER)})
    res = _run(yotpo.fetch_yotpo_reviews(CONTROL_PDP, url="https://x.example/p"))
    assert res is None
    assert calls == []


# ---------------------------------------------------------------------------
# (f) total_review==0 -> one liveness call classifying bad-key vs empty-product
# ---------------------------------------------------------------------------

def test_zero_reviews_live_key_is_empty_product(monkeypatch):
    monkeypatch.setenv("ENABLE_YOTPO_REVIEWS", "true")
    calls = _route(monkeypatch, {
        f"/products/{SHOP_PID}/reviews.json": _FakeResp(200, json_obj=REVIEWS_ZERO),
        "/products/yotpo_site_reviews/reviews.json": _FakeResp(200, json_obj=SITE_LIVE),
    })
    res = _run(yotpo.fetch_yotpo_reviews(SHOPIFY_PDP, url="https://demeterfragrance.com/x"))
    assert res is None
    # exactly two calls: the product reviews + ONE liveness call.
    assert len(calls) == 2
    assert "/products/yotpo_site_reviews/reviews.json" in calls[1]


def test_zero_reviews_dead_key_is_bad_key(monkeypatch):
    monkeypatch.setenv("ENABLE_YOTPO_REVIEWS", "true")
    calls = _route(monkeypatch, {
        f"/products/{SHOP_PID}/reviews.json": _FakeResp(200, json_obj=REVIEWS_ZERO),
        "/products/yotpo_site_reviews/reviews.json": _FakeResp(404, json_obj=SITE_DEAD),
    })
    res = _run(yotpo.fetch_yotpo_reviews(SHOPIFY_PDP, url="https://demeterfragrance.com/x"))
    assert res is None
    assert len(calls) == 2


def test_classify_key_live_vs_dead(monkeypatch):
    _route(monkeypatch, {
        "/products/yotpo_site_reviews/reviews.json": _FakeResp(200, json_obj=SITE_LIVE),
    })
    assert _run(yotpo.classify_yotpo_key(SHOP_KEY)) == "live"

    _route(monkeypatch, {
        "/products/yotpo_site_reviews/reviews.json": _FakeResp(404, json_obj=SITE_DEAD),
    })
    assert _run(yotpo.classify_yotpo_key(SHOP_KEY)) == "dead"


# ---------------------------------------------------------------------------
# (g) ratings-only bottomline endpoint
# ---------------------------------------------------------------------------

def test_bottomline_ratings_only(monkeypatch):
    monkeypatch.setenv("ENABLE_YOTPO_REVIEWS", "true")
    calls = _route(monkeypatch, {
        f"/{SHOP_PID}/bottomline": _FakeResp(200, json_obj=BOTTOMLINE),
    })
    res = _run(yotpo.fetch_yotpo_bottomline(SHOPIFY_PDP))
    assert res is not None
    assert res["total_reviews"] == 3
    assert res["average_score"] == pytest.approx(4.67)
    assert len(calls) == 1
    assert "/bottomline" in calls[0]


def test_bottomline_flag_off(monkeypatch):
    calls = _route(monkeypatch, {"bottomline": _FakeResp(200, json_obj=BOTTOMLINE)})
    res = _run(yotpo.fetch_yotpo_bottomline(SHOPIFY_PDP))
    assert res is None
    assert calls == []


# ---------------------------------------------------------------------------
# transport hygiene — a non-200 / non-JSON is a miss, never a crash
# ---------------------------------------------------------------------------

def test_non_200_is_a_miss(monkeypatch):
    monkeypatch.setenv("ENABLE_YOTPO_REVIEWS", "true")
    _route(monkeypatch, {
        f"/products/{SHOP_PID}/reviews.json": _FakeResp(403, text="blocked"),
    })
    res = _run(yotpo.fetch_yotpo_reviews(SHOPIFY_PDP, url="https://demeterfragrance.com/x"))
    assert res is None


def test_fetch_exception_is_a_miss(monkeypatch):
    monkeypatch.setenv("ENABLE_YOTPO_REVIEWS", "true")

    def boom(url, *a, **k):
        raise RuntimeError("network down")

    import curl_cffi.requests as curl_requests
    monkeypatch.setattr(curl_requests, "get", boom, raising=True)
    res = _run(yotpo.fetch_yotpo_reviews(SHOPIFY_PDP, url="https://demeterfragrance.com/x"))
    assert res is None
