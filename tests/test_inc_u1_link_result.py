"""INC-U1 LINK-RESULT (ENABLE_URL_LINK_RESULT) -- the RED file (S97 lane).

Spec: INC_U1_UNIT_SPEC.md section 9 (RED rows R01..R26) as amended by
RULINGS_INC_U1.md (U-1 the flag name, U-2 a degraded 200 keeps the credit, U-3 no
retry on 404 / 410, U-4 an unknown currency is pending, U-6 rule F, U-10 no log line
prints more of a pasted link than its host, in any flag state: row R27) and by the
relay ruling ORCH-U1-B (no retry through curl_fetch_html_same_site or any
browser-imitating client; 401 / 403 / 429 and a challenge are a coded refusal with
zero retries and zero LLM calls; 404 / 410 a coded not-found; a timeout or a 5xx gets
ONE retry through the same fetch with the same headers; br stays dropped).
Base: 5cd93c6aaa4e80e4b0ab36a43e6fa1f657d797c9.

Every row here is RED: it fails at base on an AssertionError only. Every symbol the
unit adds is read with getattr and asserted, never imported blind. Rows run with the
flag ON (house idiom) unless they say otherwise; each ON row ends with the reader
precondition (_link_on), so a row whose behaviour is already base (R07, R22, R23)
still fails at base on the missing reader.

Route rows drive POST /api/v1/url/compare through the app with stubs: an httpx
MockTransport injected into every httpx.AsyncClient the service builds and installed
on url_extraction_service._TRANSPORT; a recording SSRF validator; a recorder on
price_service.curl_fetch_html_same_site that must stay EMPTY (ORCH-U1-B: the link path
never calls it); a call-through recorder on product_resolver.resolve_lexicon (read off the
module at call time); a fake extraction LLM client; a stubbed generate_comparison;
the metering ledger. Synthetic hosts shop-a.example / shop-b.example only; no
network, no database, no credential literal.
"""
from __future__ import annotations

import app.main  # noqa: F401  -- FIRST: the dotenv hazard (common brief)

import asyncio
import copy
import gzip
import json
import logging
import os
import re
import uuid

import httpx
import pytest
from fastapi.testclient import TestClient

from app.api import url_routes
from app.api.auth_routes import get_optional_user
from app.main import app
from app.services import api_budget_service, extraction_service, price_service
from app.services import product_resolver, text_sanitize
from app.services import structured_comparison_service as scs
from app.services import url_extraction_service as ues

FLAG = "ENABLE_URL_LINK_RESULT"
V2 = "ENABLE_URL_MODE_V2"
GUARD = "ENABLE_URL_WINNER_GUARD"
GATE = "ENABLE_RESULT_GATE"
RESOLVER = "ENABLE_PRODUCT_RESOLVER"
EGRESS = "ENABLE_OPENAI_EGRESS_STOP"
METER = "ENABLE_PAID_ROUTE_METERING"
TRUTH = "ENABLE_SEARCH_LOG_TRUTH"
ROLE_VERDICT = "ENABLE_ANTHROPIC_VERDICT"
PRE_V3 = "ENABLE_OPENAI_PRE_V3"
CLEARED_ENV = (
    FLAG, V2, GUARD, GATE, RESOLVER, EGRESS, METER, TRUTH, PRE_V3,
    "ENABLE_ANTHROPIC_TEXT", "ENABLE_ANTHROPIC_VISION", ROLE_VERDICT,
    "ENABLE_ANTHROPIC_CRITIC", "ENABLE_ANTHROPIC_MODERATION", "ENABLE_SONNET_ESCALATION",
    "ENABLE_SEARCH_LOG_SYNTHETIC_MARKER", "SEARCH_LOG_SYNTHETIC_TOKEN",
    "ENABLE_COMPARE_AUTH_REQUIRED", "ENABLE_STRICT_OPTIONAL_AUTH",
    "ENABLE_OFFLOOP_DNS_RESOLVE", "ENABLE_PRICE_PARSE_OFFLOAD", "ENABLE_JSONLD_SHAPE_LADDER",
    "ENABLE_LIVE_ROBOTS_REGISTRY", "ENABLE_FRAGRANCE_ONLY_GATE",
    "ENABLE_RESULT_STATUS_METADATA", "ENABLE_COMPARE_RUN_LEDGER",
    "ENABLE_LLM_PREFLIGHT_BREAKER", "ENABLE_EXTENDED_FALLBACK_RATES",
    "ENABLE_DEVICE_DAILY_QUOTA", "ENABLE_SYNC_DB_OFFLOAD", "ENABLE_ANON_USAGE_GATE",
)
OFF_VALUES = [None, "", "false", "0", "off", "garbage", " FALSE "]

# The pasted links carry a sentinel path segment and a sentinel query token (U-10).
SENT_PATH = "u1sentinelpath"
SENT_QUERY = "u1sentineltoken"
URL1 = f"https://shop-a.example/p/{SENT_PATH}/sauvage-edp?ref={SENT_QUERY}"
URL2 = f"https://shop-b.example/p/{SENT_PATH}/bleu-edp?ref={SENT_QUERY}"
HOST1 = "shop-a.example"
HOST2 = "shop-b.example"

UP_MSG = "We did not find a product on that page. Paste the product's own page link."
SU_MSG = ("That store does not let us read its pages. Paste a link from another store, "
          "or type the product name.")
BASE_HEADERS = {
    "user-agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "accept-language": "en-US,en;q=0.5",
    "accept-encoding": "gzip, deflate, br",
    "connection": "keep-alive",
    "upgrade-insecure-requests": "1",
}

PAGE_READ_RE = re.compile(
    r"^URL_PAGE_READ host=(?P<host>\S*) json_ld_blocks=(?P<json_ld_blocks>\d+)"
    r" product_node=(?P<product_node>yes|no) title=(?P<title>yes|no)"
    r" price=(?P<price>yes|no) currency=(?P<currency>[A-Z]{3}|other|none)"
    r" image=(?P<image>yes|no) challenge=(?P<challenge>yes|no)"
    r" retry=(?P<retry>none|ok|fail)"
    r" extraction_method=(?P<extraction_method>structured|ai|none)"
    r" key_resolved=(?P<key_resolved>yes|no|none)$"
)
PAGE_READ_FIELDS = ("host", "json_ld_blocks", "product_node", "title", "price", "currency",
                    "image", "challenge", "retry", "extraction_method", "key_resolved")

VERDICT_OK = {
    "winner_index": 1, "winner_declaration": "B",
    "winner_reason": "Bleu lasts longer on skin through the day. It scores 82/100 overall.",
    "key_tradeoff": "Sauvage opens brighter.",
    "specs_comparison": {"product_0_advantages": ["brighter opening"],
                         "product_1_advantages": ["longer wear"],
                         "similar": ["EDP"]},
    "product_0_pros": ["fresh opening", 7, None, "   "],
    "product_0_cons": ["shorter wear"],
    "product_1_pros": ["long wear"],
    "product_1_cons": ["heavier", {"x": 1}],
}
VERDICT_ERROR = {"winner_index": 0, "error": extraction_service.COMPARISON_GENERATION_ERROR}

_REAL_ASYNC_CLIENT = httpx.AsyncClient


# ---------------------------------------------------------------------------
# pages
# ---------------------------------------------------------------------------
def page(title, jsonld=None, og=None, body=""):
    head = "" if title is None else f"<title>{title}</title>"
    for key, value in (og or {}).items():
        head += f'<meta property="og:{key}" content="{value}">'
    for block in (jsonld or []):
        head += '<script type="application/ld+json">' + json.dumps(block) + "</script>"
    return f"<html><head>{head}</head><body>{body}</body></html>"


def node(name, *, brand=None, price=None, currency=None, image=None, rating=None,
         count=None, **extra):
    out = {"@context": "https://schema.org", "@type": "Product", "name": name}
    if brand is not None:
        out["brand"] = {"@type": "Brand", "name": brand}
    if image is not None:
        out["image"] = image
    if price is not None:
        offer = {"@type": "Offer", "price": price}
        if currency is not None:
            offer["priceCurrency"] = currency
        out["offers"] = offer
    if rating is not None or count is not None:
        out["aggregateRating"] = {"@type": "AggregateRating", "ratingValue": rating,
                                  "reviewCount": count}
    out.update(extra)
    return out


PAGE_A = page("Sauvage EDP | Shop A", [node(
    "Sauvage Eau de Parfum 100ml", brand="Dior", price="30.000", currency="BHD",
    image="https://cdn.shop-a.example/a.jpg", rating="4.5", count="120")])
PAGE_B = page("Bleu EDP | Shop B", [node(
    "Bleu de Chanel Eau de Parfum 100ml", brand="Chanel", price="45.500", currency="BHD",
    image="https://cdn.shop-b.example/b.jpg", rating="4.8", count="300")])
CHALLENGE = page("Just a moment...", body="Checking your browser before accessing the site.")
def ok(body, headers=None):
    return (200, dict({"content-type": "text/html; charset=utf-8"}, **(headers or {})), body)


def status(code, body="<html><body>Forbidden</body></html>"):
    return (code, {"content-type": "text/html"}, body)


def redirect(location, code=302):
    return (code, {"location": location}, b"")


class Pages:
    """Serves pages by exact request url; records the url, the Accept-Encoding header,
    every request header and the timeout extension of each request."""

    def __init__(self, pages=None, default=None):
        self.pages = dict(pages or {})
        self.default = default
        self.requests: list = []

    def handler(self, request):
        url = str(request.url)
        self.requests.append({
            "url": url,
            "headers": {k.lower(): v for k, v in request.headers.items()},
            "timeout": dict(request.extensions.get("timeout") or {}),
        })
        spec = self.pages.get(url, self.default)
        if isinstance(spec, list):  # served in order, the last one repeats
            seen = sum(1 for r in self.requests if r["url"] == url)
            spec = spec[min(seen, len(spec)) - 1]
        if spec is None:
            return httpx.Response(404, text="<html>not found</html>")
        if isinstance(spec, type) and issubclass(spec, Exception):
            raise spec("u1 probe", request=request)
        code, headers, body = spec
        content = body if isinstance(body, bytes) else body.encode("utf-8")
        return httpx.Response(code, headers=headers or {}, content=content)


# ---------------------------------------------------------------------------
# recorders
# ---------------------------------------------------------------------------
def _done(value=None):
    async def _r():
        return value
    return _r()


class Ledger:
    def __init__(self):
        self.consumes: list = []
        self.refunds: list = []
        self.lifetime: list = []
        self.saves: list = []
        self.rows: list = []
        self.labels: list = []
        self.pending: list = []
        self.run_saves = False

    def consume(self, user_id, access_token="", *_a, **_kw):
        self.consumes.append(user_id)
        return _done({"allowed": True, "reason": None, "tier": "free", "consumed": True,
                      "consumed_keys": {"daily": "d", "monthly": "m"},
                      "remaining": {"daily": 2, "monthly": 9, "lifetime_free": 2}})

    def refund(self, user_id, *_a, **_kw):
        self.refunds.append(user_id)
        return _done()

    def record_lifetime(self, user_id, *_a, **_kw):
        self.lifetime.append(user_id)
        return _done()

    def save(self, *a, **kw):
        self.saves.append(copy.deepcopy(kw))
        return _done()

    def log_search(self, *a, **kw):
        self.rows.append(dict(kw))
        return _done()

    def ff(self, coro, label=None):
        self.labels.append(label)
        if self.run_saves and isinstance(label, str) and label.startswith("save_comparison"):
            self.pending.append(coro)
            return
        try:
            coro.close()
        except Exception:  # noqa: BLE001
            pass


class _FC:
    def __init__(self, store, content):
        self.store, self.content = store, content

    async def create(self, **kw):
        self.store.append(kw)
        msg = type("M", (), {"content": self.content})()
        choice = type("C", (), {"message": msg})()
        return type("R", (), {"choices": [choice], "usage": None})()


def _fake_client(store, content="{}"):
    ns = type("Client", (), {})()
    ns.chat = type("Chat", (), {"completions": _FC(store, content)})()
    ns.with_options = lambda **kw: ns
    return ns


class H:
    def __init__(self):
        self.pages = Pages()
        self.ledger = Ledger()
        self.user = None
        self.ssrf_calls: list = []
        self.llm_calls: list = []
        self.gen_calls: list = []
        self.retry_calls: list = []
        self.resolver_calls: list = []
        self.scorer_winners: list = []
        self.cfu_calls: list = []


@pytest.fixture(autouse=True)
def _u1_env(monkeypatch):
    for name in CLEARED_ENV:
        monkeypatch.delenv(name, raising=False)
    for key in list(os.environ):
        if key.startswith("OPENAI_MODEL_"):
            monkeypatch.delenv(key, raising=False)
    from app.middleware.rate_limiter import limiter
    prior = limiter.enabled
    limiter.enabled = False
    saved = dict(app.dependency_overrides)
    try:
        yield
    finally:
        limiter.enabled = prior
        app.dependency_overrides.clear()
        app.dependency_overrides.update(saved)


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


def set_env(monkeypatch, name, value):
    if value is None:
        monkeypatch.delenv(name, raising=False)
    else:
        monkeypatch.setenv(name, value)


def _serve(monkeypatch, h, pages=None, default=None):
    h.pages = Pages(pages, default)
    transport = httpx.MockTransport(h.pages.handler)

    def factory(*a, **kw):
        if kw.get("transport") is None:
            kw["transport"] = transport
        return _REAL_ASYNC_CLIENT(*a, **kw)

    monkeypatch.setattr(ues.httpx, "AsyncClient", factory)
    monkeypatch.setattr(ues, "_TRANSPORT", transport, raising=False)


def _ssrf(monkeypatch, h, deny=(), deny_second_of=None):
    seen: dict = {}

    def validate(url):
        h.ssrf_calls.append(url)
        seen[url] = seen.get(url, 0) + 1
        if deny_second_of is not None and url == deny_second_of and seen[url] >= 2:
            return False
        return not any(d in str(url) for d in deny)
    monkeypatch.setattr("app.utils.url_validator.validate_external_url", validate)


def _retry(monkeypatch, h, html=None):
    async def rec(url, domain=None, *a, **kw):
        h.retry_calls.append((url, domain))
        return html
    monkeypatch.setattr(price_service, "curl_fetch_html_same_site", rec)


def _resolver(monkeypatch, h):
    real = product_resolver.resolve_lexicon

    def rec(name, *a, **kw):
        h.resolver_calls.append(name)
        return real(name, *a, **kw)
    monkeypatch.setattr(product_resolver, "resolve_lexicon", rec)


def _verdict(monkeypatch, h, verdict=None, raises=None, delay=None):
    async def gen(*a, **kw):
        h.gen_calls.append(dict(kw))
        if delay:
            await asyncio.sleep(delay)
        if raises is not None:
            raise raises
        return copy.deepcopy(verdict if verdict is not None else VERDICT_OK), {
            "prompt_tokens": 0, "completion_tokens": 0}
    monkeypatch.setattr(extraction_service, "generate_comparison", gen)

    async def resolve(products, selected_category, parser_path=False):
        return "fragrances", False, None
    monkeypatch.setattr(scs, "_resolve_pair_category", resolve)


def _record_cfu(monkeypatch, h):
    """A call-through recorder on the route's compare_from_urls: the kwargs the route
    threads down and the SERVICE result (U-11: field / reason are asserted there)."""
    real = url_routes.compare_from_urls

    async def rec(*a, **kw):
        entry = {"args": a, "kwargs": dict(kw), "result": None}
        h.cfu_calls.append(entry)
        out = await real(*a, **kw)
        entry["result"] = copy.deepcopy(out) if isinstance(out, dict) else out
        return out
    monkeypatch.setattr(url_routes, "compare_from_urls", rec)


def full(monkeypatch, h, *, flag="true", v2=None, guard=None, gate=None, resolver=None,
         egress=None, pages=None, default=None, verdict=None, verdict_raises=None,
         verdict_delay=None, retry_html=None, deny=(), deny_second_of=None,
         llm_content="{}"):
    """The full configuration (ruling B1): metering + search-log truth ON, an authed
    user, the page server, the SSRF fake, the LLM fake, the verdict stub, the retry
    and resolver recorders, the ledger."""
    set_env(monkeypatch, FLAG, flag)
    for name, value in ((V2, v2), (GUARD, guard), (GATE, gate), (RESOLVER, resolver),
                        (EGRESS, egress)):
        set_env(monkeypatch, name, value)
    monkeypatch.setenv(METER, "true")
    monkeypatch.setenv(TRUTH, "true")
    h.user = {"id": str(uuid.uuid4()), "access_token": "t-" + uuid.uuid4().hex}
    user = h.user
    app.dependency_overrides[get_optional_user] = lambda: user
    if pages is None:
        pages = {URL1: ok(PAGE_A), URL2: ok(PAGE_B)}
    _serve(monkeypatch, h, pages, default)
    _ssrf(monkeypatch, h, deny=deny, deny_second_of=deny_second_of)
    monkeypatch.setattr(ues, "get_client", lambda *a, **k: _fake_client(h.llm_calls, llm_content))
    _verdict(monkeypatch, h, verdict, verdict_raises, verdict_delay)
    _retry(monkeypatch, h, retry_html)
    _resolver(monkeypatch, h)
    _record_cfu(monkeypatch, h)
    led = h.ledger
    monkeypatch.setattr(url_routes, "consume_comparison_credit", led.consume)
    monkeypatch.setattr(url_routes, "refund_comparison_credit", led.refund)
    monkeypatch.setattr(url_routes, "record_lifetime_comparison", led.record_lifetime)
    monkeypatch.setattr(url_routes, "save_comparison_and_track_cohort", led.save)
    monkeypatch.setattr(url_routes, "log_search", led.log_search)
    monkeypatch.setattr(url_routes, "fire_and_forget", led.ff)
    return h


def call(client, url1=URL1, url2=URL2, verb="POST"):
    headers = {"X-Request-ID": "u1-fixed-request-id"}
    if verb == "GET":
        return client.get("/api/v1/url/compare", params={"url1": url1, "url2": url2},
                          headers=headers)
    return client.post("/api/v1/url/compare", json={"url1": url1, "url2": url2},
                       headers=headers)


def _link_on():
    """The reader precondition of every ON row (asserted, never called blind)."""
    reader = getattr(ues, "url_link_result_enabled", None)
    assert callable(reader), "INC-U1: url_extraction_service.url_link_result_enabled missing"
    assert reader() is True, "INC-U1: the flag reads OFF under the row's ON value"


def _unit_ran(h):
    """U-12: the unit ran: the route threaded link_result=True into compare_from_urls."""
    assert h.cfu_calls, "INC-U1: compare_from_urls was never called"
    assert all(c["kwargs"].get("link_result") is True for c in h.cfu_calls),         [c["kwargs"] for c in h.cfu_calls]


def service_refusal(h):
    """U-11: the coded per-url refusal as the SERVICE returned it."""
    assert len(h.cfu_calls) == 1, h.cfu_calls
    out = h.cfu_calls[0]["result"]
    assert isinstance(out, dict), out
    return {k: out.get(k) for k in ("success", "code", "field", "reason", "error")}


def assert_wire_refusal(resp, code="STORE_UNREADABLE", message=None):
    """U-11: with ENABLE_URL_MODE_V2 OFF the wire carries code and error only
    (error_handler.py:247-249 lifts field / reason only with V2 ON)."""
    assert resp.status_code == 400, (resp.status_code, resp.text[:300])
    body = resp.json()
    assert body.get("success") is False, body
    assert body.get("code") == code, body
    assert body.get("error") == (SU_MSG if message is None else message), body
    assert "field" not in body and "reason" not in body, body


def products_of(resp):
    assert resp.status_code == 200, (resp.status_code, resp.text[:400])
    body = resp.json()
    assert body.get("success") is True, body
    products = body.get("products")
    assert isinstance(products, list) and len(products) == 2, products
    return body, products


def page_reads(caplog):
    return [r for r in caplog.records if r.getMessage().startswith("URL_PAGE_READ")]


# ===========================================================================
# R01 the reader
# ===========================================================================
@pytest.mark.parametrize("value,expected", [
    ("true", True), (" TRUE ", True), ("1", True), ("yes", True), ("On", True),
    (None, False), ("", False), ("false", False), ("0", False), ("off", False),
    ("garbage", False),
])
def test_r01_reader_house_idiom(monkeypatch, value, expected):
    """RED R01: url_link_result_enabled() is the house idiom, read per call."""
    reader = getattr(ues, "url_link_result_enabled", None)
    assert callable(reader), "INC-U1: url_extraction_service.url_link_result_enabled missing"
    set_env(monkeypatch, FLAG, value)
    assert reader() is expected, (value, reader())


# ===========================================================================
# R02..R05 the adapted body
# ===========================================================================
def test_r02_recommendation_is_the_verdict_reason_without_score_internals(monkeypatch, client):
    """RED R02: on a V1 body the recommendation is the verdict's winner_reason with
    the score internal ("82/100") stripped (the _v2_verdict_fill value)."""
    h = full(monkeypatch, H())
    body, _ = products_of(call(client))
    want = text_sanitize.strip_score_internals(VERDICT_OK["winner_reason"])
    assert want == "Bleu lasts longer on skin through the day.", want
    assert body.get("recommendation") == want, body.get("recommendation")
    assert len(h.gen_calls) == 1
    _link_on()


def test_r03_pros_and_cons_are_the_verdict_lists_str_only(monkeypatch, client):
    """RED R03: products[i].pros / cons are the str items of the verdict lists,
    score internals stripped, non-str and empty items dropped."""
    full(monkeypatch, H())
    _, products = products_of(call(client))
    assert products[0].get("pros") == ["fresh opening"], products[0].get("pros")
    assert products[0].get("cons") == ["shorter wear"], products[0].get("cons")
    assert products[1].get("pros") == ["long wear"], products[1].get("pros")
    assert products[1].get("cons") == ["heavier"], products[1].get("cons")
    _link_on()


def test_r04_rating_and_review_count_lifted_only_when_real(monkeypatch, client):
    """RED R04: rating 4.7 (a float) from "4.7", review_count 2000 (an int) from
    "2,000"; a 7.5 rating and an "n/a" count are not lifted."""
    pa = page("A", [node("Sauvage Eau de Parfum 100ml", brand="Dior", price="30.000",
                         currency="BHD", rating="4.7", count="2,000")])
    pb = page("B", [node("Bleu de Chanel Eau de Parfum 100ml", brand="Chanel",
                         price="45.500", currency="BHD", rating=7.5, count="n/a")])
    full(monkeypatch, H(), pages={URL1: ok(pa), URL2: ok(pb)})
    _, products = products_of(call(client))
    assert products[0].get("rating") == 4.7, products[0].get("rating")
    assert type(products[0].get("rating")) is float
    assert products[0].get("review_count") == 2000, products[0].get("review_count")
    assert type(products[0].get("review_count")) is int
    assert products[1].get("rating") is None, products[1].get("rating")
    assert products[1].get("review_count") is None, products[1].get("review_count")
    _link_on()


def test_r05_image_url_one_https_string_or_none(monkeypatch, client):
    """RED R05: a protocol-relative image list ships as its https string; an http
    image ships as None (iOS ATS)."""
    pa = page("A", [node("Sauvage Eau de Parfum 100ml", brand="Dior", price="30.000",
                         currency="BHD", image=["//cdn.shop-a.example/x.jpg"])])
    pb = page("B", [node("Bleu de Chanel Eau de Parfum 100ml", brand="Chanel",
                         price="45.500", currency="BHD",
                         image="http://cdn.shop-b.example/y.jpg")])
    full(monkeypatch, H(), pages={URL1: ok(pa), URL2: ok(pb)})
    _, products = products_of(call(client))
    assert products[0].get("image_url") == "https://cdn.shop-a.example/x.jpg", products[0]
    assert products[1].get("image_url") is None, products[1].get("image_url")
    _link_on()


# ===========================================================================
# R06..R10 the History row and the price rule
# ===========================================================================
@pytest.mark.parametrize("verb", ["POST", "GET"])
def test_r06_delivered_bhd_pair_carries_metadata_and_a_stripped_query(monkeypatch, client, verb):
    """RED R06: a delivered BHD pair carries metadata {query "<p0> vs <p1>" (names by
    dedup_brand_name), input_type "url"} into the save, and the saved query is the
    stripped _url_log_query form (no "?")."""
    h = full(monkeypatch, H())
    body, products = products_of(call(client, verb=verb))
    names = [text_sanitize.dedup_brand_name(p.get("brand"), p.get("name")) for p in products]
    want = {"query": f"{names[0]} vs {names[1]}", "input_type": "url"}
    assert body.get("metadata") == want, body.get("metadata")
    saves = h.ledger.saves
    assert len(saves) == 1, saves
    assert (saves[0].get("full_response") or {}).get("metadata") == want, saves[0]
    assert "?" not in (saves[0].get("query") or "?"), saves[0].get("query")
    assert saves[0].get("query") == url_routes._url_log_query(URL1, URL2), saves[0].get("query")
    assert saves[0].get("input_type") == "url"
    _link_on()


def test_r07_bhd_price_object_unchanged(monkeypatch, client):
    """RED R07: a BHD page price ships as the base price object (no source_method,
    no estimate, no original_* key); U-12: the unit ran (link_result threaded, a
    link_key present)."""
    h_off = full(monkeypatch, H(), flag=None)
    _, off_products = products_of(call(client))
    h = full(monkeypatch, H())
    _, products = products_of(call(client))
    _unit_ran(h)
    assert isinstance(products[0].get("link_key"), dict), products[0]
    assert products[0].get("price") == off_products[0].get("price"), products[0].get("price")
    for key in ("source_method", "estimate_bhd", "estimate_basis", "original_amount",
                "original_currency", "unavailable"):
        assert key not in (products[0].get("price") or {}), (key, products[0].get("price"))
    assert h_off.retry_calls == []
    _link_on()


def test_r08_usd_price_converted_and_labelled(monkeypatch, client):
    """RED R08: USD 100 ships as 37.6 BHD, source_method converted_usd, with
    original_amount 100 and original_currency USD."""
    pa = page("A", [node("Sauvage Eau de Parfum 100ml", brand="Dior", price="100",
                         currency="USD")])
    full(monkeypatch, H(), pages={URL1: ok(pa), URL2: ok(PAGE_B)})
    _, products = products_of(call(client))
    price = products[0].get("price") or {}
    assert price.get("amount") == 37.6, price
    assert price.get("currency") == "BHD", price
    assert price.get("source_method") == "converted_usd", price
    assert price.get("original_amount") == 100, price
    assert price.get("original_currency") == "USD", price
    _link_on()


def test_r09_sar_price_kept_with_an_estimate_and_no_history_query(monkeypatch, client):
    """RED R09: SAR 450 ships as 450 SAR with estimate_bhd 45.135 (the fallback
    rate) and estimate_basis fallback_rate; rule F: no metadata.query."""
    pa = page("A", [node("Sauvage Eau de Parfum 100ml", brand="Dior", price=450,
                         currency="SAR")])
    h = full(monkeypatch, H(), pages={URL1: ok(pa), URL2: ok(PAGE_B)})
    body, products = products_of(call(client))
    price = products[0].get("price") or {}
    assert price.get("amount") == 450, price
    assert price.get("currency") == "SAR", price
    assert price.get("estimate_bhd") == 45.135, price
    assert price.get("estimate_basis") == "fallback_rate", price
    assert "source_method" not in price, price
    assert "query" not in (body.get("metadata") or {}), body.get("metadata")
    for saved in h.ledger.saves:
        assert "query" not in ((saved.get("full_response") or {}).get("metadata") or {}), saved
    _link_on()


def test_r10_unknown_shop_without_currency_is_pending(monkeypatch, client):
    """RED R10 (U-4): an unknown shop that states no currency ships a pending price:
    amount None, unavailable True, reason currency_unknown, currency BHD."""
    pa = page("A", [node("Sauvage Eau de Parfum 100ml", brand="Dior", price="25")])
    full(monkeypatch, H(), pages={URL1: ok(pa), URL2: ok(PAGE_B)})
    _, products = products_of(call(client))
    price = products[0].get("price") or {}
    assert price.get("amount") is None, price
    assert price.get("unavailable") is True, price
    assert price.get("reason") == "currency_unknown", price
    assert price.get("currency") == "BHD", price
    _link_on()


# ===========================================================================
# R11..R18 the page reader
# ===========================================================================
def test_r11_v1_request_drops_br_and_uses_an_8s_timeout(monkeypatch, client):
    """RED R11: under the flag on V1 every page request asks Accept-Encoding
    "gzip, deflate" (no br) with an 8 s timeout."""
    h = full(monkeypatch, H())
    products_of(call(client))
    assert len(h.pages.requests) == 2, h.pages.requests
    for req in h.pages.requests:
        assert req["headers"].get("accept-encoding") == "gzip, deflate", req
        assert req["timeout"] and set(req["timeout"].values()) == {8.0}, req["timeout"]
    _link_on()


def _requests_to(h, url):
    return [r for r in h.pages.requests if r["url"] == url]


def _assert_no_detour(h):
    """ORCH-U1-B: the link path never calls curl_fetch_html_same_site (or any
    browser-imitating client): the recorder on the helper stays empty."""
    assert h.retry_calls == [], h.retry_calls


def test_r12_br_reply_is_undecodable_never_content(monkeypatch, client):
    """RED R12 (ORCH-U1-B): a 200 that still arrives under Content-Encoding br (no
    decoder) is never read as product content: STORE_UNREADABLE reason undecodable on
    the service result, zero retries (one request), zero LLM calls, one refund."""
    garbage = gzip.compress(PAGE_A.encode("utf-8"))
    h = full(monkeypatch, H(), pages={URL1: ok(garbage, {"content-encoding": "br"}),
                                      URL2: ok(PAGE_B)})
    resp = call(client)
    _unit_ran(h)
    assert_wire_refusal(resp)
    assert service_refusal(h) == {"success": False, "code": "STORE_UNREADABLE",
                                  "field": "url1", "reason": "undecodable",
                                  "error": SU_MSG}, h.cfu_calls
    assert len(_requests_to(h, URL1)) == 1, h.pages.requests
    assert h.llm_calls == [] and h.gen_calls == [], (h.llm_calls, h.gen_calls)
    assert h.ledger.refunds == [h.user["id"]], h.ledger.refunds
    _assert_no_detour(h)
    _link_on()


def test_r13_challenge_page_is_store_unreadable_without_retry_or_llm(monkeypatch, client):
    """RED R13 (U-11, ORCH-U1-B): a challenge title on a 200 is STORE_UNREADABLE reason
    challenge (field / reason on the service result; code / error on the 400 wire):
    zero retries (one request), no extraction LLM call, no verdict call; one refund."""
    h = full(monkeypatch, H(), pages={URL1: ok(CHALLENGE), URL2: ok(PAGE_B)})
    resp = call(client)
    _unit_ran(h)
    assert_wire_refusal(resp)
    assert service_refusal(h) == {"success": False, "code": "STORE_UNREADABLE",
                                  "field": "url1", "reason": "challenge",
                                  "error": SU_MSG}, h.cfu_calls
    assert len(_requests_to(h, URL1)) == 1, h.pages.requests
    assert h.llm_calls == [], h.llm_calls
    assert h.gen_calls == [], h.gen_calls
    assert h.ledger.refunds == [h.user["id"]], h.ledger.refunds
    _assert_no_detour(h)
    _link_on()


@pytest.mark.parametrize("code", [401, 403, 429])
def test_r14_refusal_status_is_store_unreadable_refused_without_retry(monkeypatch, client, code):
    """RED R14 (ORCH-U1-B): a 401 / 403 / 429 is the shop's refusal: STORE_UNREADABLE
    reason refused on the service result, zero retries (one request), zero LLM calls,
    no verdict call, one refund."""
    h = full(monkeypatch, H(), pages={URL1: status(code), URL2: ok(PAGE_B)})
    resp = call(client)
    _unit_ran(h)
    assert_wire_refusal(resp)
    assert service_refusal(h) == {"success": False, "code": "STORE_UNREADABLE",
                                  "field": "url1", "reason": "refused",
                                  "error": SU_MSG}, h.cfu_calls
    assert len(_requests_to(h, URL1)) == 1, h.pages.requests
    assert h.llm_calls == [] and h.gen_calls == [], (h.llm_calls, h.gen_calls)
    assert h.ledger.refunds == [h.user["id"]], h.ledger.refunds
    _assert_no_detour(h)
    _link_on()


def test_r15_timeout_gets_one_retry_through_the_same_fetch(monkeypatch, client):
    """RED R15 (ORCH-U1-B): a timeout gets exactly ONE retry through the same fetch with
    the same headers; the retried answer delivers."""
    h = full(monkeypatch, H(), pages={URL1: [httpx.ReadTimeout, ok(PAGE_A)],
                                      URL2: ok(PAGE_B)})
    _, products = products_of(call(client))
    _unit_ran(h)
    reqs = _requests_to(h, URL1)
    assert len(reqs) == 2, h.pages.requests
    assert reqs[0]["headers"] == reqs[1]["headers"], reqs
    assert reqs[1]["headers"].get("accept-encoding") == "gzip, deflate", reqs[1]
    assert products[0].get("name") == "Sauvage Eau de Parfum 100ml", products[0]
    assert h.ledger.refunds == [], h.ledger.refunds
    _assert_no_detour(h)
    _link_on()


def test_r15b_timeout_twice_is_a_coded_refusal(monkeypatch, client):
    """RED R15b (U-11, ORCH-U1-B): a timeout on the retry too: STORE_UNREADABLE reason
    timeout on the service result (two requests, never a third), one refund."""
    h = full(monkeypatch, H(), pages={URL1: httpx.ReadTimeout, URL2: ok(PAGE_B)})
    resp = call(client)
    _unit_ran(h)
    assert_wire_refusal(resp)
    assert service_refusal(h) == {"success": False, "code": "STORE_UNREADABLE",
                                  "field": "url1", "reason": "timeout",
                                  "error": SU_MSG}, h.cfu_calls
    assert len(_requests_to(h, URL1)) == 2, h.pages.requests
    assert h.ledger.refunds == [h.user["id"]], h.ledger.refunds
    assert h.ledger.saves == [], h.ledger.saves
    _assert_no_detour(h)
    _link_on()


@pytest.mark.parametrize("code", [404, 410])
def test_r16_404_and_410_are_a_coded_not_found_without_retry(monkeypatch, client, code):
    """RED R16 (U-3, U-11, U-12, ORCH-U1-B): a 404 or a 410 is never retried: the coded
    not-found refusal UNRESOLVED_PRODUCT reason not_found on the service result (one
    request), code / error on the wire; the unit ran."""
    h = full(monkeypatch, H(), pages={URL1: status(code), URL2: ok(PAGE_B)})
    resp = call(client)
    _unit_ran(h)
    assert len(_requests_to(h, URL1)) == 1, h.pages.requests
    assert_wire_refusal(resp, code="UNRESOLVED_PRODUCT", message=UP_MSG)
    assert service_refusal(h) == {"success": False, "code": "UNRESOLVED_PRODUCT",
                                  "field": "url1", "reason": "not_found",
                                  "error": UP_MSG}, h.cfu_calls
    _assert_no_detour(h)
    _link_on()


@pytest.mark.parametrize("code", [500, 503])
def test_r28_5xx_gets_one_retry_through_the_same_fetch(monkeypatch, client, code):
    """RED R28 (ORCH-U1-B): a 5xx answer gets exactly ONE retry through the same fetch
    with the same headers; a 200 on the retry delivers."""
    h = full(monkeypatch, H(), pages={URL1: [status(code), ok(PAGE_A)], URL2: ok(PAGE_B)})
    _, products = products_of(call(client))
    _unit_ran(h)
    reqs = _requests_to(h, URL1)
    assert len(reqs) == 2, h.pages.requests
    assert reqs[0]["headers"] == reqs[1]["headers"], reqs
    assert products[0].get("name") == "Sauvage Eau de Parfum 100ml", products[0]
    _assert_no_detour(h)
    _link_on()


def test_r28b_5xx_twice_is_a_coded_refusal(monkeypatch, client):
    """RED R28b (U-11, ORCH-U1-B): a 5xx on the retry too: STORE_UNREADABLE reason
    http_5xx on the service result (two requests), one refund."""
    h = full(monkeypatch, H(), pages={URL1: status(502), URL2: ok(PAGE_B)})
    resp = call(client)
    _unit_ran(h)
    assert_wire_refusal(resp)
    assert service_refusal(h) == {"success": False, "code": "STORE_UNREADABLE",
                                  "field": "url1", "reason": "http_5xx",
                                  "error": SU_MSG}, h.cfu_calls
    assert len(_requests_to(h, URL1)) == 2, h.pages.requests
    assert h.ledger.refunds == [h.user["id"]], h.ledger.refunds
    _assert_no_detour(h)
    _link_on()


def test_r29_connect_error_is_a_coded_refusal_without_retry(monkeypatch, client):
    """RED R29 (U-11, ORCH-U1-B: only a timeout or a 5xx is retried): a transport error
    that is not a timeout is STORE_UNREADABLE reason fetch_error on the service result,
    one request, one refund."""
    h = full(monkeypatch, H(), pages={URL1: httpx.ConnectError, URL2: ok(PAGE_B)})
    resp = call(client)
    _unit_ran(h)
    assert_wire_refusal(resp)
    assert service_refusal(h) == {"success": False, "code": "STORE_UNREADABLE",
                                  "field": "url1", "reason": "fetch_error",
                                  "error": SU_MSG}, h.cfu_calls
    assert len(_requests_to(h, URL1)) == 1, h.pages.requests
    assert h.ledger.refunds == [h.user["id"]], h.ledger.refunds
    _assert_no_detour(h)
    _link_on()


def test_r17_og_price_meta_is_read_without_an_ai_call(monkeypatch, client):
    """RED R17: og:price:amount 39.5 + og:price:currency BHD with no node price ship
    as 39.5 BHD and no extraction LLM call is made."""
    pa = page("Sauvage Eau de Parfum 100ml",
              og={"title": "Sauvage Eau de Parfum 100ml", "price:amount": "39.5",
                  "price:currency": "BHD"})
    h = full(monkeypatch, H(), pages={URL1: ok(pa), URL2: ok(PAGE_B)})
    _, products = products_of(call(client))
    price = products[0].get("price") or {}
    assert price.get("amount") == 39.5, price
    assert price.get("currency") == "BHD", price
    assert h.llm_calls == [], h.llm_calls
    _link_on()


def test_r18_graph_and_type_list_reach_structured_extraction_on_v1(monkeypatch, client):
    """RED R18: {"@graph": [{"@type": ["Product"], ...}]} on V1 is read by the shape
    ladder: the node's name and price ship, no extraction LLM call."""
    graph = {"@context": "https://schema.org", "@graph": [
        {"@type": "WebSite", "name": "Shop A"},
        {"@type": ["Product"], "name": "Graph Sauvage Eau de Parfum 100ml",
         "brand": {"@type": "Brand", "name": "Dior"},
         "offers": {"@type": "Offer", "price": "30", "priceCurrency": "BHD"}}]}
    pa = page("Shop A - a page title", [graph])
    h = full(monkeypatch, H(), pages={URL1: ok(pa), URL2: ok(PAGE_B)})
    _, products = products_of(call(client))
    assert products[0].get("name") == "Graph Sauvage Eau de Parfum 100ml", products[0]
    assert (products[0].get("price") or {}).get("amount") == "30", products[0].get("price")
    assert h.llm_calls == [], h.llm_calls
    _link_on()


# ===========================================================================
# R19..R20 the link key
# ===========================================================================
@pytest.mark.parametrize("resolver_flag", [None, "false", "true"])
def test_r19_link_key_from_the_lexicon_and_variant_fill(monkeypatch, client, resolver_flag):
    """RED R19: "Sauvage Eau de Parfum 100ml" by Dior gets link_key Dior / Sauvage /
    EDP / 100 / resolved (source lexicon); an empty variant becomes "EDP 100ml"; the
    name never changes; ENABLE_PRODUCT_RESOLVER unset, "false" or "true" alike."""
    h = full(monkeypatch, H(), resolver=resolver_flag)
    _, products = products_of(call(client))
    assert products[0].get("link_key") == {
        "brand": "Dior", "line": "Sauvage", "concentration": "EDP", "size_ml": 100,
        "gtin": None, "resolved": True, "source": "lexicon"}, products[0].get("link_key")
    assert products[0].get("variant") == "EDP 100ml", products[0].get("variant")
    assert products[0].get("name") == "Sauvage Eau de Parfum 100ml", products[0].get("name")
    assert "Dior Sauvage Eau de Parfum 100ml" in h.resolver_calls, h.resolver_calls
    _link_on()


def test_r20_untyped_concentration_is_not_written(monkeypatch, client):
    """RED R20: "Dior Sauvage" resolves (Dior / Sauvage) but its page states no
    concentration: link_key.concentration is None (never the lexicon's base EDT)."""
    pa = page("A", [node("Dior Sauvage", brand="Dior", price="30.000", currency="BHD")])
    full(monkeypatch, H(), pages={URL1: ok(pa), URL2: ok(PAGE_B)})
    _, products = products_of(call(client))
    key = products[0].get("link_key")
    assert isinstance(key, dict), key
    assert key.get("resolved") is True and key.get("brand") == "Dior", key
    assert key.get("concentration") is None, key
    _link_on()


# ===========================================================================
# R21..R23 the verdict failure arms
# ===========================================================================
def test_r21_verdict_error_dict_without_the_stop_is_a_degraded_200(monkeypatch, client):
    """RED R21 (U-2): an error dict with the egress stop OFF is a degraded 200: success
    True, comparison.error truthy, recommendation "", pros / cons [], winner 0, no
    metadata, the credit kept (no refund)."""
    h = full(monkeypatch, H(), verdict=VERDICT_ERROR)
    body, products = products_of(call(client))
    assert (body.get("comparison") or {}).get("error"), body.get("comparison")
    assert body.get("recommendation") == "", body.get("recommendation")
    assert "metadata" not in body, body.get("metadata")
    assert body.get("winner_index") == 0, body.get("winner_index")
    for p in products:
        assert p.get("pros") == [] and p.get("cons") == [], p
    assert h.ledger.refunds == [], h.ledger.refunds
    assert h.ledger.consumes == [h.user["id"]], h.ledger.consumes
    _link_on()


def test_r22_verdict_error_dict_under_the_egress_stop_keeps_the_503(monkeypatch, client):
    """RED R22: an error dict while ENABLE_OPENAI_EGRESS_STOP is ON and the verdict role
    is OFF stays the 503 LLM_UNAVAILABLE with one refund; U-12: the unit ran."""
    h = full(monkeypatch, H(), verdict=VERDICT_ERROR, egress="true")
    resp = call(client)
    _unit_ran(h)
    assert resp.status_code == 503, (resp.status_code, resp.text[:300])
    assert resp.json().get("code") == "LLM_UNAVAILABLE", resp.json()
    assert h.ledger.refunds == [h.user["id"]], h.ledger.refunds
    _link_on()


def test_r23_raised_llm_unavailable_keeps_the_503(monkeypatch, client):
    """RED R23: a raised LLMUnavailableError with a role ON stays the 503 LLM_UNAVAILABLE; U-12: the unit ran."""
    monkeypatch.setenv(ROLE_VERDICT, "true")
    monkeypatch.setenv(PRE_V3, "true")
    h = full(monkeypatch, H(),
             verdict_raises=api_budget_service.LLMUnavailableError("u1 synthetic"))
    resp = call(client)
    _unit_ran(h)
    assert resp.status_code == 503, (resp.status_code, resp.text[:300])
    assert resp.json().get("code") == "LLM_UNAVAILABLE", resp.json()
    assert h.ledger.refunds == [h.user["id"]], h.ledger.refunds
    _link_on()


# ===========================================================================
# R24..R26
# ===========================================================================
def test_r24_one_page_read_line_per_page_and_no_link_text(monkeypatch, client, caplog):
    """RED R24: one INFO URL_PAGE_READ record per page with the eleven fields (host
    only); the sentinel path segment and query token appear in no record."""
    caplog.set_level(logging.INFO)
    monkeypatch.setattr(logging.getLogger("httpx"), "level", logging.WARNING)
    monkeypatch.setattr(logging.getLogger("httpcore"), "level", logging.WARNING)
    full(monkeypatch, H())
    products_of(call(client))
    reads = page_reads(caplog)
    assert len(reads) == 2, [r.getMessage() for r in reads]
    parsed = {}
    for rec in reads:
        assert rec.levelno == logging.INFO, rec.levelname
        m = PAGE_READ_RE.match(rec.getMessage())
        assert m is not None, rec.getMessage()
        assert tuple(m.groupdict()) == PAGE_READ_FIELDS
        parsed[m.group("host")] = m.groupdict()
    assert set(parsed) == {HOST1, HOST2}, parsed
    a = parsed[HOST1]
    assert (a["json_ld_blocks"], a["product_node"], a["title"], a["price"], a["currency"],
            a["image"], a["challenge"], a["retry"], a["extraction_method"],
            a["key_resolved"]) == ("1", "yes", "yes", "yes", "BHD", "yes", "no", "none",
                                   "structured", "yes"), a
    for rec in caplog.records:
        msg = rec.getMessage()
        assert SENT_PATH not in msg and SENT_QUERY not in msg, (rec.name, msg)
    _link_on()


def test_r25_v1_link_compare_runs_under_the_deadline(monkeypatch, client):
    """RED R25: V1 + the flag runs under the 25 s deadline (the module constant patched
    to 0.05 s, a slow verdict): 503 TIMEOUT, one refund."""
    monkeypatch.setattr(url_routes, "_URL_COMPARE_DEADLINE_SECONDS", 0.05)
    h = full(monkeypatch, H(), verdict_delay=1.0)
    resp = call(client)
    assert resp.status_code == 503, (resp.status_code, resp.text[:300])
    assert resp.json().get("code") == "TIMEOUT", resp.json()
    assert h.ledger.refunds == [h.user["id"]], h.ledger.refunds
    _link_on()


def test_r26_degraded_with_the_guard_ships_the_scorer_winner(monkeypatch, client):
    """RED R26: a degraded 200 with ENABLE_URL_WINNER_GUARD ON ships the scorer's
    winner as winner_index."""
    from app.services import scoring_service as ss
    real = ss.ScoringService.compute_scores
    h = H()

    def rec(self, *a, **kw):
        out = real(self, *a, **kw)
        h.scorer_winners.append(out.get("winner_index"))
        return out
    monkeypatch.setattr(ss.ScoringService, "compute_scores", rec)
    pa = page("A", [node("Sauvage Eau de Parfum 100ml", brand="Dior", price="60.000",
                         currency="BHD", rating="3.1", count="5")])
    pb = page("B", [node("Bleu de Chanel Eau de Parfum 100ml", brand="Chanel",
                         price="20.000", currency="BHD", rating="4.9", count="900")])
    full(monkeypatch, h, verdict=VERDICT_ERROR, guard="true",
         pages={URL1: ok(pa), URL2: ok(pb)})
    body, _ = products_of(call(client))
    assert h.scorer_winners == [1], h.scorer_winners
    assert body.get("winner_index") == 1, body.get("winner_index")
    assert (body.get("comparison") or {}).get("error"), body.get("comparison")
    _link_on()


# ===========================================================================
# R27 (U-10, ORCH-U1-A): no log record of a link compare carries more of a pasted
# link than its host, in any flag state
# ===========================================================================
U10_SCENARIOS = ("success", "http_403", "redirect_cap", "redirect_blocked",
                 "initial_blocked_at_fetch")
# The base fetch_page lines that print the whole link (url_extraction_service.py at
# 5cd93c6a): :557 "[SSRF] Blocked initial URL: {url}", :567 "[SSRF] Blocked redirect
# to {nxt}", :573 "[SSRF] Too many redirects for {url}". Those scenarios fail at base
# in BOTH flag states; the OFF success / http_403 nodes are green at base and live in
# tests/test_inc_u1_gate_rows.py (P10).
U10_BASE_LEAK = ("redirect_cap", "redirect_blocked", "initial_blocked_at_fetch")
BLOCKED_TARGET = f"https://blocked.shop-a.example/p/{SENT_PATH}/x?ref={SENT_QUERY}"


class _FakeInsert:
    def __init__(self, store):
        self.store = store

    def table(self, name):
        self.name = name
        return self

    def insert(self, record):
        self.store.append(record)
        return self

    def execute(self):
        return type("Res", (), {"data": [{"id": str(uuid.uuid4())}]})()


def u10_run(monkeypatch, client, caplog, state, scenario):
    """One link compare under ``state`` ("on" / "off") and ``scenario`` with every
    record captured at INFO (production: the root at INFO, httpx and httpcore at
    WARNING, logging_config.py:47-48), the retry recorder in place and the save run
    for real through database_service.save_comparison over a fake client. Returns
    (response, harness, inserted rows)."""
    from app.services import database_service as dbs
    caplog.set_level(logging.INFO)
    monkeypatch.setattr(logging.getLogger("httpx"), "level", logging.WARNING)
    monkeypatch.setattr(logging.getLogger("httpcore"), "level", logging.WARNING)
    pages = {URL1: ok(PAGE_A), URL2: ok(PAGE_B)}
    deny, deny_second_of = (), None
    if scenario == "http_403":
        pages[URL1] = status(403)
    elif scenario == "redirect_cap":
        pages[URL1] = redirect(URL1)
    elif scenario == "redirect_blocked":
        pages[URL1] = redirect(BLOCKED_TARGET)
        deny = ("blocked.shop-a.example",)
    elif scenario == "initial_blocked_at_fetch":
        deny_second_of = URL1
    h = full(monkeypatch, H(), flag="true" if state == "on" else None, pages=pages,
             deny=deny, deny_second_of=deny_second_of, retry_html=None)
    inserted: list = []
    fake = _FakeInsert(inserted)
    monkeypatch.setattr(dbs, "get_supabase_client", lambda *a, **k: fake)

    async def real_save(**kw):
        h.ledger.saves.append(copy.deepcopy(kw))
        return await dbs.save_comparison(
            full_response=kw.get("full_response"), query=kw.get("query"),
            input_type=kw.get("input_type"), user_id=kw.get("user_id"))
    monkeypatch.setattr(url_routes, "save_comparison_and_track_cohort", real_save)
    h.ledger.run_saves = True
    resp = call(client)
    for coro in h.ledger.pending:
        asyncio.run(coro)
    return resp, h, inserted


def u10_assert_no_link_text(caplog):
    assert caplog.records, "U-10: no record captured"
    for rec in caplog.records:
        msg = rec.getMessage()
        assert SENT_PATH not in msg, ("U-10 path", rec.name, rec.levelname, msg)
        assert SENT_QUERY not in msg, ("U-10 query", rec.name, rec.levelname, msg)


@pytest.mark.parametrize("state,scenario", [("on", s) for s in U10_SCENARIOS]
                         + [("off", s) for s in U10_BASE_LEAK])
def test_r27_u10_no_log_record_carries_the_link_path_or_query(monkeypatch, client, caplog,
                                                              state, scenario):
    """RED R27 (U-10): across the success, 403 (+ the retry), redirect-cap, blocked
    redirect and blocked-at-fetch paths, with the save run, no captured record carries
    the sentinel path segment or query token of a pasted link; flag ON and OFF."""
    resp, h, inserted = u10_run(monkeypatch, client, caplog, state, scenario)
    assert resp.status_code in (200, 400), (resp.status_code, resp.text[:300])
    if scenario == "success":
        assert resp.status_code == 200 and len(h.ledger.saves) == 1, h.ledger.saves
    u10_assert_no_link_text(caplog)
    if state == "on":
        _link_on()
